"""Machine-checked assertions of an evaluation case, and the verifier replay (E6.2).

Pure code on a raw result record (`evals/run.py` writes it): no model, no
network, no manual judgement. Semantics are documented in data/samples/README.md.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from src.agent.loop import DECISION_SUSPEND
from src.tools.verify_report import verify_report

ASK_STUDENT_TOOL = "ask_student"
VERIFY_REPORT_TOOL = "verify_report"


@dataclass(frozen=True)
class AssertionResult:
    name: str
    is_passed: bool
    detail: str = ""


def normalize_text(text: str) -> str:
    """Case, accents and no-break spaces ignored (NFKD maps them to a plain space)."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _contains(haystack: str, needle: str) -> bool:
    return normalize_text(needle) in normalize_text(haystack)


def is_successful_call(event: dict) -> bool:
    """A journaled call that really happened: no tool error, and ask_student suspended the loop."""
    result = event.get("result")
    if isinstance(result, dict) and set(result) == {"error"}:
        return False
    return event["tool"] != ASK_STUDENT_TOOL or event.get("decision") == DECISION_SUSPEND


def called_tools(record: dict) -> set[str]:
    return {event["tool"] for event in record["journal"]
            if event.get("tool") and is_successful_call(event)}


def evaluate_case(case: dict, record: dict) -> list[AssertionResult]:
    """Every assertion of the case, checked against what the run really did."""
    assertions = case["assertions"]
    report = record.get("report_text") or ""
    questions = record.get("questions") or []
    results = _tool_results(assertions["required_tools"], record)
    results += _forbidden_results(assertions["forbidden_strings"], report, questions)
    results += _required_results(assertions["required_strings"], report)
    results += _offer_results(assertions["expected_offer_ids"], report)
    results += _question_results(assertions["expected_question"], questions)
    return results


def _tool_results(required_tools: list[str], record: dict) -> list[AssertionResult]:
    called = called_tools(record)
    return [AssertionResult(f"required_tool: {tool}", tool in called,
                            "" if tool in called else "never called")
            for tool in required_tools]


def _forbidden_results(forbidden: list[str], report: str,
                       questions: list[str]) -> list[AssertionResult]:
    # The report and the questions are the two things the student reads.
    seen = "\n".join([report, *questions])
    return [AssertionResult(f"forbidden_string: {text}", not _contains(seen, text),
                            "found in report or questions" if _contains(seen, text) else "")
            for text in forbidden]


def _required_results(required: list[str], report: str) -> list[AssertionResult]:
    return [AssertionResult(f"required_string: {text}", _contains(report, text),
                            "" if _contains(report, text) else "absent from the verified report")
            for text in required]


def _offer_results(offer_ids: list[str], report: str) -> list[AssertionResult]:
    return [AssertionResult(f"expected_offer_id: {offer_id}", _contains(report, offer_id),
                            "" if _contains(report, offer_id) else "absent from the verified report")
            for offer_id in offer_ids]


def _question_results(alternatives: list[str] | None,
                      questions: list[str]) -> list[AssertionResult]:
    if alternatives is None:
        return []  # no question required; the series confirmation of a voice case is allowed
    is_asked = any(_contains(question, text)
                   for question in questions for text in alternatives)
    return [AssertionResult("expected_question", is_asked,
                            "" if is_asked else f"none of {alternatives} in the questions asked")]


def is_conform(results: list[AssertionResult]) -> bool:
    return all(result.is_passed for result in results)


def replay_verification(record: dict) -> dict:
    """Run verify_report again on the last recorded call: no agent, no API.

    The raw journal keeps the draft report and the proof context the agent
    sent, so the verifier can be re-run on them and compared with the problems
    it returned during the run.
    """
    event = next((event for event in reversed(record["journal"])
                  if event.get("tool") == VERIFY_REPORT_TOOL
                  and isinstance(event.get("args"), dict)
                  and "report" in event["args"] and "context" in event["args"]), None)
    if event is None:
        raise ValueError("no verify_report call with a draft and a context in this result")
    replayed = verify_report(event["args"]["report"], event["args"]["context"])
    return {"recorded": event["result"], "replayed": replayed,
            "is_same": event["result"] == replayed}
