"""Muse Wonder turns and per-turn model choice (E5.7).

No network, no API key: the Responses client is faked. The loop keeps its chat
history; a Wonder turn must translate it, answer in chat shape, and the journal
must name the model that really answered.
"""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
from openai.types.chat import ChatCompletionMessage, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion_message_tool_call import Function

from src.agent import loop
from src.api import server
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.clients import muse_wonder
from src.clients.muse_wonder import (
    MUSE_CONTRIBUTOR_MODEL, MUSE_WONDER_EFFORT, MUSE_WONDER_MODEL, WonderTurnError,
    request_wonder_turn)
from tests.fake_client import ScriptedFakeClient
from tests.test_loop import assistant_message, stub_verify_report, tool_call


def _text_item(text):
    return SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text=text)])


def _call_item(call_id, name, arguments):
    return SimpleNamespace(type="function_call", call_id=call_id, name=name,
                           arguments=json.dumps(arguments))


class FakeResponses:
    def __init__(self, outputs, fail=False):
        self.calls = []
        self._outputs = list(outputs)
        self._fail = fail

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._fail:
            raise ConnectionError("upstream unavailable")
        return SimpleNamespace(status="completed", output=self._outputs.pop(0))


class WonderAndChatClient(ScriptedFakeClient):
    """Chat turns scripted like ScriptedFakeClient; Responses turns scripted separately."""

    def __init__(self, chat_messages, wonder_outputs, wonder_fails=False):
        super().__init__(chat_messages)
        self.responses = FakeResponses(wonder_outputs, fail=wonder_fails)


def test_wonder_turn_requests_high_effort_and_flat_tools():
    client = SimpleNamespace(responses=FakeResponses([[_call_item("c1", "verify_report", {"report": {}})]]))
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "go"}]
    request_wonder_turn(client, messages, TOOL_SCHEMAS)
    sent = client.responses.calls[0]
    assert sent["model"] == "muse-wonder-1.0"
    assert sent["reasoning"] == {"effort": MUSE_WONDER_EFFORT} == {"effort": "high"}
    assert {tool["name"] for tool in sent["tools"]} == {
        schema["function"]["name"] for schema in TOOL_SCHEMAS}
    assert all(tool["type"] == "function" and "function" not in tool for tool in sent["tools"])


def test_chat_history_becomes_responses_items_with_matching_call_ids():
    assistant = ChatCompletionMessage(role="assistant", content="Looking up.", tool_calls=[
        ChatCompletionMessageToolCall(id="call-1", type="function",
                                      function=Function(name="lookup_filieres", arguments="{}"))])
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "go"},
                assistant,
                {"role": "tool", "tool_call_id": "call-1", "content": "{\"accessible\": []}"}]
    items = muse_wonder._history_to_input(messages)
    assert items == [
        {"role": "system", "content": "sys"}, {"role": "user", "content": "go"},
        {"role": "assistant", "content": "Looking up."},
        {"type": "function_call", "call_id": "call-1", "name": "lookup_filieres", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call-1", "output": "{\"accessible\": []}"},
    ]


def test_wonder_answer_comes_back_as_a_chat_message_the_loop_can_use():
    client = SimpleNamespace(responses=FakeResponses(
        [[_text_item("Verifying."), _call_item("c9", "verify_report", {"report": {"claims": []}})]]))
    message = request_wonder_turn(client, [{"role": "user", "content": "go"}], TOOL_SCHEMAS)
    assert isinstance(message, ChatCompletionMessage)
    assert message.content == "Verifying."
    call = message.tool_calls[0]
    assert (call.id, call.function.name) == ("c9", "verify_report")
    assert json.loads(call.function.arguments) == {"report": {"claims": []}}
    # Still serializable, so a later chat turn can take the same history.
    assert message.model_dump(exclude_none=True)["tool_calls"][0]["id"] == "c9"


def test_empty_wonder_answer_is_an_error_not_a_silent_turn():
    client = SimpleNamespace(responses=FakeResponses([[]]))
    try:
        request_wonder_turn(client, [{"role": "user", "content": "go"}], TOOL_SCHEMAS)
    except WonderTurnError as error:
        assert "empty answer" in str(error)
    else:
        raise AssertionError("an empty answer must raise")


def test_turn_model_switches_to_wonder_after_the_guide_search():
    assert loop._turn_model("base", MUSE_WONDER_MODEL, []) == "base"
    assert loop._turn_model("base", MUSE_WONDER_MODEL, [{"tool": "read_grade_sheet"}]) == "base"
    assert loop._turn_model("base", MUSE_WONDER_MODEL, [{"tool": "lookup_filieres"}]) == MUSE_WONDER_MODEL
    assert loop._turn_model("base", None, [{"tool": "lookup_filieres"}]) == "base"


def test_journal_names_who_decided_each_step(monkeypatch):
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: {"accessible": [], "excluded": []})
    stub_verify_report(monkeypatch, [[]])
    client = WonderAndChatClient(
        [assistant_message(tool_calls=[tool_call("l", "lookup_filieres", {"serie": "D"})])],
        [[_call_item("v", "verify_report", {"report": {"claims": []}, "context": {}})],
         [_text_item("Done.")]])
    journal = []
    result = loop.run(client, MUSE_CONTRIBUTOR_MODEL, [], "Hello.", journal=journal,
                      drafting_model=MUSE_WONDER_MODEL)
    assert result == "Done."
    assert [(event["tool"], event["model"]) for event in journal] == [
        ("lookup_filieres", MUSE_CONTRIBUTOR_MODEL), ("verify_report", MUSE_WONDER_MODEL)]
    assert client.calls[0]["model"] == MUSE_CONTRIBUTOR_MODEL
    # The second turn went through Responses with the whole history, not through chat.
    history = client.responses.calls[0]["input"]
    assert any(item.get("type") == "function_call_output" for item in history)
    assert len(client.calls) == 1


def test_failed_wonder_turn_falls_back_and_the_journal_says_so(monkeypatch):
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: {"accessible": [], "excluded": []})
    stub_verify_report(monkeypatch, [[]])
    client = WonderAndChatClient(
        [assistant_message(tool_calls=[tool_call("l", "lookup_filieres", {"serie": "D"})]),
         assistant_message(tool_calls=[tool_call("v", "verify_report", {"report": {"claims": []}, "context": {}})]),
         assistant_message(content="Done.")],
        [], wonder_fails=True)
    journal = []
    result = loop.run(client, MUSE_CONTRIBUTOR_MODEL, [], "Hello.", journal=journal,
                      drafting_model=MUSE_WONDER_MODEL)
    assert result == "Done."
    # Wonder was tried, failed, and must never be credited with the step.
    assert len(client.responses.calls) == 2  # tried on both drafting turns
    assert journal[-1]["tool"] == "verify_report"
    assert journal[-1]["model"] == MUSE_CONTRIBUTOR_MODEL


def test_without_a_drafting_model_every_turn_uses_the_base_model(monkeypatch):
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: {"accessible": [], "excluded": []})
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("l", "lookup_filieres", {"serie": "D"})]),
        assistant_message(content="Done.")])
    journal = []
    loop.run(client, "base-model", [], "Hello.", journal=journal)
    assert {call["model"] for call in client.calls} == {"base-model"}
    assert journal[0]["model"] == "base-model"


def test_step_frames_carry_the_deciding_model_to_the_browser():
    frame = server.build_step_frame({"step": 5, "tool": "verify_report", "args": {}, "result": [],
                                     "decision": "continue", "model": MUSE_WONDER_MODEL})
    assert frame["model"] == "muse-wonder-1.0"


def test_server_runs_the_contributor_with_wonder_drafting(monkeypatch):
    app = TestClient(server.app)
    server.pending_run_store.clear_pending_runs()
    seen = {}

    def fake_run(client, model, schemas, user_input, journal=None, language="fr", drafting_model=None):
        seen.update(model=model, drafting_model=drafting_model)
        return "Done."

    monkeypatch.setattr(loop, "run", fake_run)
    monkeypatch.setattr(server, "get_client", lambda: SimpleNamespace())
    response = app.post("/run", files={"image": ("sheet.jpg", b"fake-image", "image/jpeg")},
                        data={"text": "x"})
    assert response.status_code == 200
    assert seen == {"model": "muse-spark-1.3-contributor", "drafting_model": "muse-wonder-1.0"}
