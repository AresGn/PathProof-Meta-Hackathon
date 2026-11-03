"""Test the full tool round trip with Muse Spark 1.3: choice, tool result returned, final answer.

Writes docs/muse-spark-roundtrip-results.md (never docs/muse-spark-tool-call-results.md).
Usage: python scripts/test_muse_roundtrip.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))  # run as a script: make `src` importable

from src.clients.meta_client import get_client  # noqa: E402
OUT_PATH = ROOT / "docs" / "muse-spark-roundtrip-results.md"
MODEL = "muse-spark-1.3"
MAX_TOKENS = 4000  # reasoning tokens count against the limit (AGENTS.md, section Modèle et API)
MAX_STEPS = 5  # spike only: bounds the loop; the agent loop limit is docs/prd.md FR-1
ROUNDTRIP_RUNS = 5  # docs/backlog.md E0.7

# Fictional values, deliberately odd so the model cannot guess them.
CUTOFF_VALUE = 13.87
BURSARY_VALUE = 417
TOOL_RESULTS = {
    "get_filiere_cutoff": {"filiere": "Médecine", "seuil_moyenne_classement": CUTOFF_VALUE},
    "get_bursary_amount": {"serie": "D", "montant_mensuel_fcfa": BURSARY_VALUE},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_filiere_cutoff",
            "description": "Renvoie le seuil de moyenne de classement d'une filière.",
            "parameters": {
                "type": "object",
                "properties": {"filiere": {"type": "string"}},
                "required": ["filiere"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_bursary_amount",
            "description": "Renvoie le montant mensuel de la bourse pour une série du BAC.",
            "parameters": {
                "type": "object",
                "properties": {"serie": {"type": "string"}},
                "required": ["serie"],
            },
        },
    },
]

ROUNDTRIP_QUESTION = "Quel est le seuil de moyenne de classement pour la filière Médecine ?"
BURSARY_QUESTION = "Quel est le montant mensuel de la bourse pour la série D ?"
NO_TOOL_QUESTION = "Combien font 7 fois 8 ?"
CHAINED_QUESTION = (
    "Donne-moi le seuil de moyenne de classement de Médecine ET le montant mensuel "
    "de la bourse pour la série D."
)


def run_conversation(client: OpenAI, question: str) -> dict:
    """Run the tool loop until the model answers without tool call; return a raw trace."""
    messages: list[dict] = [{"role": "user", "content": question}]
    trace: dict = {"question": question, "steps": [], "tools_called": [], "usage": []}
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOLS, max_tokens=MAX_TOKENS
        )
        choice = response.choices[0]
        message = choice.message
        trace["usage"].append(response.usage.model_dump() if response.usage else {})
        trace["steps"].append(
            {
                "finish_reason": choice.finish_reason,
                "content": message.content,
                "tool_calls": [
                    {"name": tc.function.name, "arguments": tc.function.arguments}
                    for tc in (message.tool_calls or [])
                ],
            }
        )
        if not message.tool_calls:
            trace["final_answer"] = message.content or ""
            return trace
        messages.append(message.model_dump(exclude_none=True))
        for tool_call in message.tool_calls:
            trace["tools_called"].append(tool_call.function.name)
            result = TOOL_RESULTS.get(tool_call.function.name, {"erreur": "outil inconnu"})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    trace["final_answer"] = ""
    trace["error"] = f"no final answer after {MAX_STEPS} steps"
    return trace


def contains_value(text: str, value: float | int) -> bool:
    """Accept both '13.87' and '13,87'; spaces in thousands are ignored."""
    compact = text.replace(" ", "").replace(" ", "").replace(" ", "")
    return str(value) in compact or str(value).replace(".", ",") in compact


def total_tokens(trace: dict) -> tuple[int, int]:
    prompt = sum(u.get("prompt_tokens", 0) for u in trace["usage"])
    completion = sum(u.get("completion_tokens", 0) for u in trace["usage"])
    return prompt, completion


def safe_run(client: OpenAI, question: str) -> dict:
    try:
        return run_conversation(client, question)
    except Exception as exc:  # recorded in the report, not hidden
        return {"question": question, "steps": [], "tools_called": [], "usage": [],
                "final_answer": "", "error": f"{type(exc).__name__}: {exc}"}


def evaluate(client: OpenAI) -> dict:
    roundtrip = [safe_run(client, ROUNDTRIP_QUESTION) for _ in range(ROUNDTRIP_RUNS)]
    for trace in roundtrip:
        trace["ok"] = (
            trace["tools_called"] == ["get_filiere_cutoff"]
            and contains_value(trace["final_answer"], CUTOFF_VALUE)
        )
    bursary = safe_run(client, BURSARY_QUESTION)
    bursary["ok"] = (
        bursary["tools_called"] == ["get_bursary_amount"]
        and contains_value(bursary["final_answer"], BURSARY_VALUE)
    )
    no_tool = safe_run(client, NO_TOOL_QUESTION)
    no_tool["ok"] = not no_tool["tools_called"] and "56" in no_tool["final_answer"]
    chained = safe_run(client, CHAINED_QUESTION)
    chained["ok"] = (
        set(chained["tools_called"]) == {"get_filiere_cutoff", "get_bursary_amount"}
        and contains_value(chained["final_answer"], CUTOFF_VALUE)
        and contains_value(chained["final_answer"], BURSARY_VALUE)
    )
    return {"roundtrip": roundtrip, "bursary": bursary, "no_tool": no_tool, "chained": chained}


def describe_chain(trace: dict) -> str:
    """Whether the tools were called in two separate model turns (true chaining) or in parallel."""
    turns_with_tools = [s for s in trace["steps"] if s["tool_calls"]]
    if len(turns_with_tools) >= 2:
        return "observed one after the other (separate turns)"
    if turns_with_tools and len(turns_with_tools[0]["tool_calls"]) >= 2:
        return "requested in parallel in a single turn (no chaining)"
    return "not observed"


def render_trace(title: str, trace: dict) -> list[str]:
    prompt, completion = total_tokens(trace)
    lines = [
        f"### {title}",
        "",
        f"- Question: {trace['question']}",
        f"- Tools called: {trace['tools_called'] or 'none'}",
        f"- Tokens: {prompt} input, {completion} output",
        f"- Result: {'✅' if trace.get('ok') else '❌'}"
        + (f" — error: `{trace['error']}`" if trace.get("error") else ""),
        "",
        "```json",
        json.dumps(trace["steps"], ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    return lines


def render_report(results: dict) -> str:
    roundtrip = results["roundtrip"]
    passed = sum(1 for t in roundtrip if t["ok"])
    all_traces = roundtrip + [results["bursary"], results["no_tool"], results["chained"]]
    prompt = sum(total_tokens(t)[0] for t in all_traces)
    completion = sum(total_tokens(t)[1] for t in all_traces)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# Muse Spark 1.3 test — round trip with two tools",
        "",
        "Checks that the model picks the right tool, receives its result in a `tool` message, "
        "then uses it in its final answer. Complements `docs/muse-spark-tool-call-results.md` "
        "(first call only). The returned values are fictional and impossible to guess.",
        "",
        f"- **Run date:** {stamp}",
        f"- **Model:** `{MODEL}` — `max_tokens` = {MAX_TOKENS}",
        f"- **Tools exposed:** `get_filiere_cutoff` (returns {CUTOFF_VALUE}), "
        f"`get_bursary_amount` (returns {BURSARY_VALUE})",
        "",
        "## Summary",
        "",
        "| Criterion | Result |",
        "| --- | --- |",
        f"| Round trip, right tool + value in the final answer | **{passed}/{len(roundtrip)}** |",
        f"| Choice of the other tool (grant), 1 run | {'✅' if results['bursary']['ok'] else '❌'} |",
        f"| Question without a tool: no call, 1 run | {'✅' if results['no_tool']['ok'] else '❌'} |",
        f"| Chained calls (question needing two tools) | {describe_chain(results['chained'])} ; "
        f"answer containing both values: {'✅' if results['chained']['ok'] else '❌'} |",
        "",
        "## Cost",
        "",
        f"Total tokens used: {prompt} input, {completion} output "
        f"({len(all_traces)} conversations). This script does not record the credit "
        "rate, so the cost in credits is not given here.",
        "",
        "## Limits of this test",
        "",
        f"- Two tools only, one question per tool; {ROUNDTRIP_RUNS} attempts for the round trip, "
        "only 1 for each other case: this is not a statistical measurement.",
        "- Fixed tool values; the test covers neither tool errors nor invalid arguments.",
        "- PathProof's real tools (`lookup_filieres`...) are not tested here.",
        "",
        "## Raw outputs",
        "",
    ]
    for index, trace in enumerate(roundtrip, start=1):
        lines += render_trace(f"Round trip, run {index}", trace)
    lines += render_trace("Other tool (grant)", results["bursary"])
    lines += render_trace("Question without a tool", results["no_tool"])
    lines += render_trace("Chained calls", results["chained"])
    lines += ["## Rerun", "", "```bash", "python scripts/test_muse_roundtrip.py", "```", ""]
    return "\n".join(lines)


def main() -> int:
    results = evaluate(get_client())
    OUT_PATH.write_text(render_report(results), encoding="utf-8")
    passed = sum(1 for t in results["roundtrip"] if t["ok"])
    print(f"Round trip: {passed}/{ROUNDTRIP_RUNS}; report: {OUT_PATH}")
    return 0 if passed == ROUNDTRIP_RUNS else 1


if __name__ == "__main__":
    sys.exit(main())
