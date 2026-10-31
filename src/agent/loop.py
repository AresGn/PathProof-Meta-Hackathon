"""Agent loop: model picks a tool, we execute it, feed the observation back, repeat.

This module only orchestrates: it holds no business logic (no average, no
filtering, no proof check of its own). The tool JSON schemas live in
`src/agent/tool_schemas.py`, declared in that single place; every real
tool of `src/tools/` is registered in `TOOLS` by its function name.

`ask_student` is the one tool that does not feed an observation back right
away: it suspends the loop, which returns {"status": "needs_input",
"question", "messages", "tool_call_id", "pending_tool_call_ids",
"steps_used", "journal", "consecutive_verify_refusals"} and makes no
further model or tool call. `resume` then answers every pending tool call
of that message (the student's answer for `ask_student`, a "not executed"
error for the others, which the real API requires before any new model
call), appends them as tool observations and continues the loop. Steps are
counted across suspensions: `steps_used` travels in the suspended state,
so the 12-step limit (FR-1) covers the whole run, resumes included.

The journal is a JSON list of events {"step", "tool", "args", "result",
"decision"}, one per tool call, reusable by the CLI and the web (E5.1):
pass a list as `journal` to collect it, it travels in the suspended and
unverified states. `decision` is what the loop does next: "continue"
(feed the observation back), "suspend" (ask_student), "stop_unverified"
(3rd consecutive verify_report refusal) or "stop_step_limit" (ask_student
at the 12th step, which cannot suspend and stops instead).

Model arguments are filtered to the keys declared in `TOOL_SCHEMAS`
(single source of truth): an extra key such as `client` never reaches the
function, and filtering happens in `_execute_tool` only (the ask path
filters once via the same `_filter_arguments` helper). An empty schema
list means the shared schemas: `tool_schemas=[]` filters like `None`.
A malformed JSON payload never calls the tool: the observation
is `invalid arguments: ...` so the model can fix its JSON, and the
journal keeps the truncated raw payload under `_raw_arguments` for
debugging. A `verify_report` exception (tool error) is an observation
like any other: it neither resets nor increments the
consecutive-refusal counter.

After `MAX_VERIFY_REFUSALS` consecutive refusals of `verify_report` (a
non-empty problems list; a proven draft resets the counter), the loop
stops with {"status": "unverified", "refused_claims", "problems",
"report", "journal", "steps_used"} instead of burning the remaining
steps: `refused_claims` are the claims of the last draft that the verifier
refused, transmitted to `build_report` (#27) so it lists them under
"Ce que je n'ai pas pu vérifier", never as facts. Matching claims to
problems by `claim_id` is routing, not verification: the loop never
recomputes or rechecks a proof itself.
"""
import json

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.tools.ask_student import ask_student
from src.tools.build_report import build_report
from src.tools.compute_ranking_average import compute_ranking_average
from src.tools.extract_profile import extract_profile
from src.tools.lookup_filieres import lookup_filieres
from src.tools.read_grade_sheet import read_grade_sheet
from src.tools.transcribe_voice import transcribe_voice
from src.tools.verify_report import verify_report

ASK_STUDENT_TOOL = "ask_student"
VERIFY_REPORT_TOOL = "verify_report"
BUILD_REPORT_TOOL = "build_report"
NOT_EXECUTED_ERROR = "not executed: answer the pending question first"
INVALID_ARGUMENTS_ERROR = "invalid arguments"
STOPPED_STEP_LIMIT = "Stopped: step limit reached."
DECISION_CONTINUE = "continue"
DECISION_SUSPEND = "suspend"
DECISION_STOP_UNVERIFIED = "stop_unverified"
DECISION_STOP_STEP_LIMIT = "stop_step_limit"
TOOLS = {
    "transcribe_voice": transcribe_voice,
    "extract_profile": extract_profile,
    "read_grade_sheet": read_grade_sheet,
    "compute_ranking_average": compute_ranking_average,
    "lookup_filieres": lookup_filieres,
    ASK_STUDENT_TOOL: ask_student,
    VERIFY_REPORT_TOOL: verify_report,
    BUILD_REPORT_TOOL: build_report,
}
MAX_STEPS = 12  # docs/prd.md FR-1
MAX_VERIFY_REFUSALS = 3  # docs/decisions.md 2026-10-28: stop at the 3rd consecutive refusal
MAX_RAW_ARGUMENTS = 500  # docs/decisions.md 2026-10-31: raw payload kept truncated in the journal


def _resolve_schemas(tool_schemas: list[dict] | None) -> list[dict]:
    """Return the schemas to filter against; an empty list means the shared ones."""
    return TOOL_SCHEMAS if not tool_schemas else tool_schemas


def _schema_properties(tool_schemas: list[dict] | None = None) -> dict[str, set[str]]:
    """Map each tool name to the argument keys its schema declares."""
    schemas = _resolve_schemas(tool_schemas)
    mapping: dict[str, set[str]] = {}
    for schema in schemas or []:
        function = schema.get("function", {}) if isinstance(schema, dict) else {}
        name = function.get("name")
        parameters = function.get("parameters", {})
        properties = parameters.get("properties", {})
        if isinstance(name, str) and isinstance(properties, dict):
            mapping[name] = set(properties)
    return mapping


def _filter_arguments(name: str, args: dict,
                      tool_schemas: list[dict] | None = None) -> dict:
    """Keep only the keys declared in the tool schema (schemas stay the source)."""
    allowed = _schema_properties(tool_schemas).get(name)
    if allowed is None:
        return dict(args)
    return {key: value for key, value in args.items() if key in allowed}


def run(client, model: str, tool_schemas: list[dict] | None, user_input: str,
        journal: list | None = None) -> str | dict:
    """Run the loop from a student input.

    Returns the model's final text, the `needs_input` dict of `ask_student`
    when the loop suspends (see `resume`), the `unverified` dict after 3
    consecutive `verify_report` refusals, or the step-limit sentence.
    `tool_schemas` defaults to `TOOL_SCHEMAS` (single declaration place);
    an empty list is treated like `None`.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input}]
    return _continue_loop(client, model, tool_schemas, messages, steps_used=0,
                          journal=journal if journal is not None else [],
                          verify_refusals=0)


def resume(client, model: str, tool_schemas: list[dict] | None, suspended: dict,
           student_answer: str | None) -> str | dict:
    """Resume a loop suspended by `ask_student` with the student's answer.

    Every pending tool call of the suspended message gets a tool response:
    the answer for `ask_student` (the model sees it like any other tool
    result), `NOT_EXECUTED_ERROR` for the others, which were never executed.
    A blank answer resumes nothing: the suspended state is returned as is and
    neither the model nor any tool is called (ask, never guess). A malformed
    state fails loudly (missing key), never a silent `tool_call_id: None`.
    """
    messages = suspended["messages"]
    if not isinstance(student_answer, str) or not student_answer.strip():
        return {"status": "needs_input", "question": suspended["question"],
                "messages": messages, "tool_call_id": suspended["tool_call_id"],
                "pending_tool_call_ids": suspended["pending_tool_call_ids"],
                "steps_used": suspended["steps_used"],
                "journal": suspended.get("journal") or [],
                "consecutive_verify_refusals": suspended.get(
                    "consecutive_verify_refusals", 0)}
    answer = json.dumps({"answer": student_answer.strip()}, ensure_ascii=False)
    not_executed = json.dumps({"error": NOT_EXECUTED_ERROR}, ensure_ascii=False)
    for call_id in suspended["pending_tool_call_ids"]:
        content = answer if call_id == suspended["tool_call_id"] else not_executed
        messages.append({"role": "tool", "tool_call_id": call_id, "content": content})
    return _continue_loop(client, model, tool_schemas, messages,
                          steps_used=suspended["steps_used"],
                          journal=suspended.get("journal") or [],
                          verify_refusals=suspended.get(
                              "consecutive_verify_refusals", 0))


def _continue_loop(client, model: str, tool_schemas: list[dict] | None,
                   messages: list, steps_used: int, journal: list,
                   verify_refusals: int) -> str | dict:
    tool_schemas = _resolve_schemas(tool_schemas)
    while steps_used < MAX_STEPS:
        msg = client.chat.completions.create(
            model=model, messages=messages, tools=tool_schemas).choices[0].message
        steps_used += 1
        messages.append(msg)
        if not msg.tool_calls:
            return msg.content or ""
        outcome, verify_refusals = _execute_calls(
            msg.tool_calls, messages, steps_used, journal, verify_refusals,
            tool_schemas)
        if outcome is not None:
            return outcome
    return STOPPED_STEP_LIMIT


def _execute_calls(tool_calls: list, messages: list, steps_used: int, journal: list,
                   verify_refusals: int,
                   tool_schemas: list[dict] | None = None) -> tuple[str | dict | None, int]:
    """Execute one assistant message's calls; return (terminal outcome, refusals)."""
    for index, call in enumerate(tool_calls):
        if call.function.name == ASK_STUDENT_TOOL:
            outcome = _ask_student_outcome(
                call, tool_calls[index:], messages, steps_used, journal,
                verify_refusals, tool_schemas)
            if outcome is not None:
                return outcome, verify_refusals
            continue
        args, parse_error, journal_args = _parse_arguments(call)
        if parse_error is not None:
            messages.append(_tool_observation(call, None, parse_error))
            _record(journal, steps_used, call.function.name, journal_args, None,
                    parse_error, DECISION_CONTINUE)
            continue
        if call.function.name == BUILD_REPORT_TOOL:
            args = _pin_verified_draft(args, journal)
        result, error, filtered = _execute_tool(call.function.name, args, tool_schemas)
        messages.append(_tool_observation(call, result, error))
        if call.function.name == VERIFY_REPORT_TOOL and error is None:
            verify_refusals, outcome = _verify_outcome(
                filtered, result, steps_used, journal, verify_refusals)
            if outcome is not None:
                return outcome, verify_refusals
            continue
        _record(journal, steps_used, call.function.name, filtered, result, error,
                DECISION_CONTINUE)
    return None, verify_refusals


def _pin_verified_draft(args: dict, journal: list) -> dict:
    """Make build_report receive the draft verify_report just accepted.

    The model retypes the whole JSON for build_report and can drift from
    the verified draft (a proof copied into the wrong field). When the most
    recent verify_report call returned no problem, its `report` and `context`
    replace the model's: routing only, build_report still re-verifies.
    """
    last = next((event for event in reversed(journal)
                 if event["tool"] == VERIFY_REPORT_TOOL), None)
    if last is None or last["result"] != []:
        return args
    pinned = {key: last["args"][key] for key in ("report", "context")
              if key in last["args"]}
    return {**args, **pinned}


def _verify_outcome(args: dict, result: object, steps_used: int, journal: list,
                    verify_refusals: int) -> tuple[int, dict | None]:
    """Count one verify_report result; stop as unverified at the 3rd refusal.

    Only a returned problem list counts: an exception never reaches here
    (it is an error observation in `_execute_calls`) and leaves the
    consecutive-refusal counter unchanged, like a non-list result.
    """
    if not isinstance(result, list):
        _record(journal, steps_used, VERIFY_REPORT_TOOL, args, result, None,
                DECISION_CONTINUE)
        return verify_refusals, None
    if not result:
        _record(journal, steps_used, VERIFY_REPORT_TOOL, args, result, None,
                DECISION_CONTINUE)
        return 0, None
    verify_refusals += 1
    if verify_refusals < MAX_VERIFY_REFUSALS:
        _record(journal, steps_used, VERIFY_REPORT_TOOL, args, result, None,
                DECISION_CONTINUE)
        return verify_refusals, None
    _record(journal, steps_used, VERIFY_REPORT_TOOL, args, result, None,
            DECISION_STOP_UNVERIFIED)
    report = args.get("report")
    return verify_refusals, {
        "status": "unverified",
        "refused_claims": _refused_claims(report, result),
        "problems": result,
        "report": report,
        "journal": journal,
        "steps_used": steps_used,
    }


def _refused_claims(report: object, problems: list) -> list:
    """Claims of the draft whose claim_id the verifier refused (for build_report)."""
    if not isinstance(report, dict) or not isinstance(report.get("claims"), list):
        return []
    refused_ids = {problem.get("claim_id") for problem in problems
                   if isinstance(problem, dict)
                   and problem.get("claim_id") is not None}
    return [claim for claim in report["claims"]
            if isinstance(claim, dict) and claim.get("claim_id") in refused_ids]


def _ask_student_outcome(call, remaining_calls: list, messages: list, steps_used: int,
                         journal: list, verify_refusals: int,
                         tool_schemas: list[dict] | None = None) -> dict | str | None:
    """Suspend on a valid question; an invalid one is an error observation.

    `remaining_calls` is the suspended call plus every later call of the same
    message: none of them was executed, and `resume` answers each of them.
    At the step limit there is nothing to resume, so the loop stops instead
    (journaled as `stop_step_limit`, never as a misleading `suspend`).
    """
    args, parse_error, journal_args = _parse_arguments(call)
    if parse_error is not None:
        messages.append(_tool_observation(call, None, parse_error))
        _record(journal, steps_used, ASK_STUDENT_TOOL, journal_args, None, parse_error,
                DECISION_CONTINUE)
        return None
    filtered = _filter_arguments(ASK_STUDENT_TOOL, args, tool_schemas)
    try:
        result = ask_student(**filtered)
    except Exception as error:  # invalid question: observation, no suspension
        messages.append(_tool_observation(call, None, str(error)))
        _record(journal, steps_used, ASK_STUDENT_TOOL, filtered, None, str(error),
                DECISION_CONTINUE)
        return None
    if steps_used >= MAX_STEPS:
        _record(journal, steps_used, ASK_STUDENT_TOOL, filtered, result, None,
                DECISION_STOP_STEP_LIMIT)
        return STOPPED_STEP_LIMIT
    _record(journal, steps_used, ASK_STUDENT_TOOL, filtered, result, None,
            DECISION_SUSPEND)
    return {**result, "messages": messages, "tool_call_id": call.id,
            "pending_tool_call_ids": [pending.id for pending in remaining_calls],
            "steps_used": steps_used, "journal": journal,
            "consecutive_verify_refusals": verify_refusals}


def _parse_arguments(call) -> tuple[dict, str | None, dict]:
    """Parse the model's JSON arguments; return (args, error, journal_args).

    A malformed payload or a non-object stays visible as
    `invalid arguments: ...` so the model knows its JSON was broken
    instead of seeing a misleading "missing required argument".
    `journal_args` is what the journal records: the parsed dict on
    success, the truncated raw payload under `_raw_arguments` on error.
    """
    raw = call.function.arguments if isinstance(call.function.arguments, str) else ""
    try:
        parsed = json.loads(call.function.arguments)
    except (ValueError, TypeError) as error:
        return {}, f"{INVALID_ARGUMENTS_ERROR}: {error}", {
            "_raw_arguments": raw[:MAX_RAW_ARGUMENTS]}
    if not isinstance(parsed, dict):
        return {}, (f"{INVALID_ARGUMENTS_ERROR}: expected an object, "
                     f"got {type(parsed).__name__}"), {
            "_raw_arguments": raw[:MAX_RAW_ARGUMENTS]}
    return parsed, None, parsed


def _execute_tool(name: str, args: dict,
                  tool_schemas: list[dict] | None = None) -> tuple[object, str | None, dict]:
    """Run one registered tool; return (result, error, filtered_args).

    The single filtering place for tool calls: only the keys declared in
    the tool schema reach the function, so the model can never inject
    `client` or another off-schema argument. A tool exception (including
    `verify_report`) becomes an observation: it neither resets nor
    increments the consecutive-refusal counter.
    """
    tool = TOOLS.get(name)
    if tool is None:
        return None, f"unknown tool: {name}", dict(args)
    filtered = _filter_arguments(name, args, tool_schemas)
    try:
        return tool(**filtered), None, filtered
    except Exception as error:  # tool error becomes an observation, not a crash
        return None, str(error), filtered


def _tool_observation(call, result: object, error: str | None) -> dict:
    payload = {"error": error} if error is not None else result
    content = json.dumps(payload, default=str, ensure_ascii=False)
    return {"role": "tool", "tool_call_id": call.id, "content": content}


def _record(journal: list, step: int, tool: str, args: dict, result: object,
            error: str | None, decision: str) -> None:
    payload = {"error": error} if error is not None else result
    journal.append({"step": step, "tool": tool, "args": _json_value(args),
                    "result": _json_value(payload), "decision": decision})


def _json_value(value: object) -> object:
    """Copy a value into plain JSON data so the journal stays serializable."""
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except (TypeError, ValueError):
        return str(value)
