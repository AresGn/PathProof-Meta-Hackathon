"""Muse Wonder 1.0 agent turn (Responses API); the only place that knows its parameters.

The loop keeps its history in chat format. A Wonder turn converts that history
to Responses items, calls the model with a high reasoning effort, and returns
the answer as a chat assistant message, so the loop and the other models never
see the difference.
"""
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function

MUSE_WONDER_MODEL = "muse-wonder-1.0"
MUSE_WONDER_EFFORT = "high"  # Meta Responses API reasoning effort, requested for the drafting turns
MUSE_CONTRIBUTOR_MODEL = "muse-spark-1.3-contributor"  # chat model with tool calling, probed on 2026-11-03


class WonderTurnError(RuntimeError):
    """Wonder answered without a usable message or tool call."""


def _tool_calls_of(message: object) -> list:
    return list(getattr(message, "tool_calls", None) or [])


def _history_to_input(messages: list) -> list[dict]:
    """Chat history (dicts and assistant messages) as Responses input items."""
    items: list[dict] = []
    for message in messages:
        if isinstance(message, dict):
            if message.get("role") == "tool":
                items.append({"type": "function_call_output",
                              "call_id": message["tool_call_id"],
                              "output": message["content"]})
            else:
                items.append({"role": message["role"], "content": message["content"]})
            continue
        content = getattr(message, "content", None)
        if isinstance(content, str) and content.strip():
            items.append({"role": "assistant", "content": content})
        for call in _tool_calls_of(message):
            items.append({"type": "function_call", "call_id": call.id,
                          "name": call.function.name,
                          "arguments": call.function.arguments})
    return items


def _schemas_to_tools(tool_schemas: list[dict]) -> list[dict]:
    """Chat function schemas as flat Responses tools."""
    tools = []
    for schema in tool_schemas:
        function = schema["function"]
        tools.append({"type": "function", "name": function["name"],
                      "description": function.get("description", ""),
                      "parameters": function.get("parameters", {"type": "object"})})
    return tools


def _output_to_message(response: object) -> ChatCompletionMessage:
    """Turn a Responses output into the chat assistant message the loop expects."""
    if getattr(response, "status", None) == "incomplete":
        # Same trap as finish_reason=length: partial text must never pass for a final answer.
        details = getattr(response, "incomplete_details", None)
        raise WonderTurnError(f"incomplete answer, reason={getattr(details, 'reason', None)}")
    texts: list[str] = []
    calls: list[ChatCompletionMessageToolCall] = []
    for item in getattr(response, "output", None) or []:
        if item.type == "message":
            texts.extend(part.text for part in item.content if part.type == "output_text")
        elif item.type == "function_call":
            calls.append(ChatCompletionMessageToolCall(
                id=item.call_id, type="function",
                function=Function(name=item.name, arguments=item.arguments)))
    content = "\n".join(text for text in texts if text.strip()) or None
    if content is None and not calls:
        raise WonderTurnError(f"empty answer, status={getattr(response, 'status', None)}")
    return ChatCompletionMessage(role="assistant", content=content,
                                 tool_calls=calls or None)


def request_wonder_turn(client, messages: list, tool_schemas: list[dict]) -> ChatCompletionMessage:
    """One agent turn answered by Muse Wonder at high reasoning effort."""
    response = client.responses.create(
        model=MUSE_WONDER_MODEL,
        reasoning={"effort": MUSE_WONDER_EFFORT},
        input=_history_to_input(messages),
        tools=_schemas_to_tools(tool_schemas))
    return _output_to_message(response)

