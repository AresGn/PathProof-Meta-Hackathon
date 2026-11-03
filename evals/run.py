"""Hand-launched evaluation runner (E6.2).

    python -m evals.run                         # dry run: lists the cases, sends nothing
    python -m evals.run --live [--case <id>]    # real agent loop, costs API credits
    python -m evals.run --summarize <date>      # rebuild summary.md from raw results
    python -m evals.run --replay <result.json>  # re-run verify_report, no agent, no API

Never imported by pytest or the CI run: the tests only exercise the pure
helpers with a fake client. Run from the repository root (sample paths are
relative to it).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date as calendar_date
from pathlib import Path
from typing import Callable

from evals.checks import normalize_text, replay_verification
from evals.summary import load_records, render_summary
from src.cli_run import (
    CliRunResult,
    TokenUsage,
    outcome_status,
    resolve_path,
    run_cli_session,
)
from src.clients.meta_client import get_client
from src.clients.muse_wonder import MUSE_CONTRIBUTOR_MODEL, MUSE_WONDER_MODEL
from src.domain.report_text import DEFAULT_LANGUAGE

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "cases.jsonl"
RESULTS_DIR = ROOT / "evals" / "results"
SUMMARY_NAME = "summary.md"


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def select_cases(cases: list[dict], case_ids: list[str] | None) -> list[dict]:
    if not case_ids:
        return cases
    known = {case["id"] for case in cases}
    unknown = [case_id for case_id in case_ids if case_id not in known]
    if unknown:
        raise ValueError(f"unknown case id(s): {', '.join(unknown)}")
    return [case for case in cases if case["id"] in case_ids]


def case_inputs(case: dict) -> dict:
    """Paths and fallback text of a case, in the shape `run_cli_session` takes."""
    by_kind = {(sample["role"], sample["type"]): resolve_path(ROOT / sample["path"], sample["role"])
               for sample in case["input"]["files"]}
    text_path = by_kind.get(("voice", "text"))
    return {"image_path": by_kind.get(("grade_sheet", "image")),
            "audio_path": by_kind.get(("voice", "audio")),
            "voice_text": text_path.read_text(encoding="utf-8") if text_path else None}


def answers_from_script(script: list[dict], exchanges: list[dict]) -> Callable[[str], str]:
    """Answer each question with the first unused scripted answer whose `when` words it contains.

    Matching by content, not by position: a different question order must not hand
    the student's confirmation of the series to a question about the average. A
    question nothing matches gets a blank answer, which stops the run (as the CLI does).
    """
    unused = list(script)

    def ask(question: str) -> str:
        match = next((entry for entry in unused
                      if any(normalize_text(word) in normalize_text(question)
                             for word in entry["when"])), None)
        if match is not None:
            unused.remove(match)
        answer = match["answer"] if match else ""
        exchanges.append({"question": question, "answer": answer})
        return answer

    return ask


def questions_from_journal(journal: list) -> list[str]:
    return [event["args"]["question"] for event in journal
            if event.get("tool") == "ask_student" and isinstance(event.get("args"), dict)
            and isinstance(event["args"].get("question"), str)]


def status_of(result: CliRunResult | None) -> str:
    if result is None:
        return "error"
    status = outcome_status(result.outcome)
    # A finished loop without a verified report is not a success.
    return "no_verified_report" if status == "finished" and not result.report_text else status


def build_record(case: dict, date: str, result: CliRunResult | None, journal: list,
                 error: str | None, usage: TokenUsage, duration: float,
                 exchanges: list[dict]) -> dict:
    """Raw result of one case: enough to recompute every assertion and replay the verifier.

    Tokens, duration and questions survive a crash: they come from the objects the
    runner owns, not from the (missing) result. The deciding models are read from
    the journal by the summary, never taken from constants.
    """
    return {
        "case_id": case["id"],
        "date": date,
        "language": DEFAULT_LANGUAGE,
        "files": case["input"]["files"],
        "student_answers": case.get("student_answers", []),
        "exchanges": exchanges,
        "outcome_status": status_of(result),
        "report_text": result.report_text if result else None,
        "questions": result.questions if result else questions_from_journal(journal),
        "duration_seconds": result.duration_seconds if result else duration,
        "usage": {"prompt_tokens": usage.prompt_tokens,
                  "completion_tokens": usage.completion_tokens,
                  "total_tokens": usage.total_tokens,
                  "streaming_calls": usage.streaming_calls,
                  "by_model": usage.by_model},
        "error": error,
        "journal": journal,
    }


def run_case(client, case: dict, date: str) -> dict:
    """Run one case with the real loop; a crash is recorded, never raised."""
    journal: list = []
    exchanges: list[dict] = []
    usage = TokenUsage()
    result: CliRunResult | None = None
    error: str | None = None
    started = time.monotonic()
    try:
        result = run_cli_session(
            client, MUSE_CONTRIBUTOR_MODEL,
            ask_student=answers_from_script(case.get("student_answers", []), exchanges),
            journal=journal, language=DEFAULT_LANGUAGE, drafting_model=MUSE_WONDER_MODEL,
            usage=usage, **case_inputs(case))
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
    return build_record(case, date, result, journal, error, usage,
                        time.monotonic() - started, exchanges)


def write_record(results_dir: Path, record: dict) -> Path:
    path = results_dir / f"{record['case_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_summary(date: str, cases: list[dict], results_root: Path | None = None) -> Path:
    results_root = results_root or RESULTS_DIR  # read at call time, so tests can redirect it
    pairs = load_records(results_root / date, cases)
    summary_path = results_root / SUMMARY_NAME
    summary_path.write_text(render_summary(date, pairs) + "\n",
                            encoding="utf-8")
    return summary_path


def run_live(client, cases: list[dict], date: str, results_root: Path | None = None) -> None:
    results_root = results_root or RESULTS_DIR
    for case in cases:
        print(f"[{case['id']}] running...", file=sys.stderr)
        record = run_case(client, case, date)
        path = write_record(results_root / date, record)
        print(f"[{case['id']}] {record['outcome_status']} -> {path}", file=sys.stderr)


def iso_date(value: str) -> str:
    """A calendar date used as a folder name: nothing that can climb out of evals/results/."""
    try:
        return calendar_date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PathProof evaluation cases by hand.")
    parser.add_argument("--live", action="store_true",
                        help="call the real API (costs credits); without it nothing is sent")
    parser.add_argument("--case", action="append", help="run only this case id (repeatable)")
    parser.add_argument("--date", type=iso_date, default=None, help="results folder name (default: today)")
    parser.add_argument("--summarize", metavar="DATE", type=iso_date,
                        help="rebuild summary.md from evals/results/<DATE>/, no API call")
    parser.add_argument("--replay", metavar="RESULT_JSON",
                        help="re-run verify_report on a recorded result, no agent, no API")
    return parser


def _print_replay(path: Path) -> int:
    outcome = replay_verification(json.loads(path.read_text(encoding="utf-8")))
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 0 if outcome["is_same"] else 1


def _print_plan(cases: list[dict]) -> None:
    print("Dry run: nothing is sent to the API. Add --live to run these cases:")
    for case in cases:
        files = ", ".join(sample["path"] for sample in case["input"]["files"])
        print(f"  {case['id']}: {files}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    try:
        if args.replay:
            return _print_replay(Path(args.replay))
        cases = select_cases(load_cases(), args.case)
        if args.summarize:
            print(write_summary(args.summarize, load_cases()))
            return 0
        if not args.live:
            _print_plan(cases)
            return 0
        date = args.date or calendar_date.today().isoformat()
        run_live(get_client(), cases, date)
        if len(cases) < len(load_cases()):
            # A summary of a few cases would replace the full table with a partial one.
            print(f"Partial run: summary.md left untouched. Rebuild it with --summarize {date}.",
                  file=sys.stderr)
            return 0
        print(write_summary(date, load_cases()))
        return 0
    except Exception as error:  # one clean exit for a missing key, file or case id
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
