"""Markdown table of one evaluation date, built from the raw results (E6.2).

Everything shown is read from `evals/results/<date>/<id>.json` and recomputed
by `evals.checks`: the table can be rebuilt later without calling the API.
"""
from __future__ import annotations

import json
from pathlib import Path

from evals.checks import AssertionResult, evaluate_case, is_conform

TOKENS_PER_MILLION = 1_000_000
NO_COST = "n/a (no per-model usage)"
# USD per million (input, output) tokens, standard billing: https://dev.meta.ai/docs/pricing-rate-limits,
# consulted 3 Nov 2026. Cached input is billed lower; every input token is priced in full here.
PRICE_PER_MILLION_TOKENS = {
    "muse-spark-1.3-contributor": (0.10, 0.20),
    "muse-wonder-1.0": (4.00, 20.00),
}


def load_records(results_dir: Path, cases: list[dict]) -> list[tuple[dict, dict]]:
    """(case, record) pairs, in the order of cases.jsonl, for the cases run that date."""
    pairs = []
    for case in cases:
        path = results_dir / f"{case['id']}.json"
        if path.is_file():
            pairs.append((case, json.loads(path.read_text(encoding="utf-8"))))
    return pairs


def estimate_cost(usage: dict) -> float | None:
    """USD of the agent-loop calls, from the tokens counted per model.

    None when the record has no per-model counts (older results) or a model has no
    known rate: a cost is never guessed. The tools' own calls (vision, profile,
    transcription) go through clients the loop does not see, so they are not in it.
    """
    by_model = usage.get("by_model")
    if not by_model or any(model not in PRICE_PER_MILLION_TOKENS for model in by_model):
        return None
    return sum((counts["prompt_tokens"] * PRICE_PER_MILLION_TOKENS[model][0]
                + counts["completion_tokens"] * PRICE_PER_MILLION_TOKENS[model][1])
               / TOKENS_PER_MILLION for model, counts in by_model.items())


def _format_cost(cost: float | None) -> str:
    return NO_COST if cost is None else f"${cost:.2f}"


def _mark(is_passed: bool) -> str:
    return "pass" if is_passed else "FAIL"


def _row(case: dict, record: dict, results: list[AssertionResult],
         cost: float | None) -> str:
    passed = sum(result.is_passed for result in results)
    usage = record["usage"]
    tool_calls = sum(1 for event in record["journal"] if event.get("tool"))
    cells = [case["id"], _mark(is_conform(results)), f"{passed}/{len(results)}",
             str(tool_calls), str(len(record["questions"])),
             f"{record['duration_seconds']:.0f} s", f"{usage['total_tokens']:,}",
             _format_cost(cost)]
    return "| " + " | ".join(cells) + " |"


def _detail_lines(case: dict, record: dict, results: list[AssertionResult]) -> list[str]:
    lines = [f"### {case['id']} — {record['outcome_status']}"]
    if record.get("error"):
        lines.append(f"Run error: {record['error']}")
    for result in results:
        suffix = f" ({result.detail})" if result.detail else ""
        lines.append(f"- {_mark(result.is_passed)} `{result.name}`{suffix}")
    for index, question in enumerate(record["questions"], start=1):
        lines.append(f"- Q{index}: {question}")
    return lines


def render_summary(date: str, pairs: list[tuple[dict, dict]]) -> str:
    """The summary.md text for the given (case, record) pairs."""
    evaluated = [(case, record, evaluate_case(case, record)) for case, record in pairs]
    costs = [estimate_cost(record["usage"])
             for _, record, _ in evaluated]
    lines = [f"# Evaluation summary — {date}", "",
             f"{sum(is_conform(results) for _, _, results in evaluated)} of "
             f"{len(evaluated)} cases conform (every assertion passes).", "",
             "| Case | Result | Assertions | Tool calls | Questions | Duration | Loop tokens | Loop cost |",
             "|---|---|---|---|---|---|---|---|"]
    lines += [_row(case, record, results, cost)
              for (case, record, results), cost in zip(evaluated, costs)]
    lines += ["", _totals_line(evaluated, costs), "", *_notes(pairs), "## Detail per assertion", ""]
    for case, record, results in evaluated:
        lines += _detail_lines(case, record, results) + [""]
    return "\n".join(lines)


def _totals_line(evaluated: list, costs: list[float | None]) -> str:
    tokens = sum(record["usage"]["total_tokens"] for _, record, _ in evaluated)
    seconds = sum(record["duration_seconds"] for _, record, _ in evaluated)
    cost = None if any(value is None for value in costs) else sum(costs)
    return (f"**Total: {tokens:,} loop tokens, {seconds:.0f} s, cost {_format_cost(cost)}.**")


def _notes(pairs: list[tuple[dict, dict]]) -> list[str]:
    models = sorted({f"{key}: {value}" for _, record in pairs
                     for key, value in record["models"].items()})
    streaming = sum(record["usage"]["streaming_calls"] for _, record in pairs)
    return ["Models: " + "; ".join(models) + ".",
            "Loop tokens are the non-streaming chat and Responses calls of the agent loop "
            f"({streaming} streaming call(s) not counted); the tools' own calls (vision, "
            "profile extraction, transcription) are not counted. Loop cost is those tokens at "
            "the official rates of dev.meta.ai/docs/pricing-rate-limits (3 Nov 2026), cached "
            "input priced in full, so the real bill is slightly different; Billing is the "
            "reference. Duration excludes the time spent waiting for the student's answer.", ""]
