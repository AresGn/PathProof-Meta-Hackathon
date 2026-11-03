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
from datetime import date as calendar_date
from pathlib import Path

from evals.checks import replay_verification
from evals.summary import load_records, render_summary
from src.agent import loop
from src.cli_run import (
    CliRunResult,
    answers_from_lines,
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


def outcome_status(outcome: object) -> str:
    if isinstance(outcome, dict):
        return str(outcome.get("status"))
    if outcome == loop.STOPPED_STEP_LIMIT:
        return "step_limit"
    return "finished"


def build_record(case: dict, date: str, result: CliRunResult | None, journal: list,
                 error: str | None) -> dict:
    """Raw result of one case: enough to recompute every assertion and replay the verifier."""
    usage = result.usage if result else None
    return {
        "case_id": case["id"],
        "date": date,
        "language": DEFAULT_LANGUAGE,
        "models": {"deciding": MUSE_CONTRIBUTOR_MODEL, "drafting": MUSE_WONDER_MODEL},
        "files": case["input"]["files"],
        "student_answers": case.get("student_answers", []),
        "outcome_status": outcome_status(result.outcome) if result else "error",
        "report_text": result.report_text if result else None,
        "questions": result.questions if result else [],
        "duration_seconds": result.duration_seconds if result else 0.0,
        "usage": {"prompt_tokens": usage.prompt_tokens if usage else 0,
                  "completion_tokens": usage.completion_tokens if usage else 0,
                  "total_tokens": usage.total_tokens if usage else 0,
                  "streaming_calls": usage.streaming_calls if usage else 0},
        "error": error,
        "journal": journal,
    }


def run_case(client, case: dict, date: str) -> dict:
    """Run one case with the real loop; a crash is recorded, never raised."""
    journal: list = []
    result: CliRunResult | None = None
    error: str | None = None
    try:
        result = run_cli_session(
            client, MUSE_CONTRIBUTOR_MODEL, ask_student=answers_from_lines(
                case.get("student_answers", [])),
            journal=journal, language=DEFAULT_LANGUAGE, drafting_model=MUSE_WONDER_MODEL,
            **case_inputs(case))
    except Exception as exception:
        error = f"{type(exception).__name__}: {exception}"
    return build_record(case, date, result, journal, error)


def write_record(results_dir: Path, record: dict) -> Path:
    path = results_dir / f"{record['case_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def write_summary(date: str, cases: list[dict], price_input: float | None,
                  price_output: float | None, results_root: Path = RESULTS_DIR) -> Path:
    pairs = load_records(results_root / date, cases)
    summary_path = results_root / SUMMARY_NAME
    summary_path.write_text(render_summary(date, pairs, price_input, price_output) + "\n",
                            encoding="utf-8")
    return summary_path


def run_live(client, cases: list[dict], date: str, results_root: Path = RESULTS_DIR) -> None:
    for case in cases:
        print(f"[{case['id']}] running...", file=sys.stderr)
        record = run_case(client, case, date)
        path = write_record(results_root / date, record)
        print(f"[{case['id']}] {record['outcome_status']} -> {path}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the PathProof evaluation cases by hand.")
    parser.add_argument("--live", action="store_true",
                        help="call the real API (costs credits); without it nothing is sent")
    parser.add_argument("--case", action="append", help="run only this case id (repeatable)")
    parser.add_argument("--date", default=None, help="results folder name (default: today)")
    parser.add_argument("--summarize", metavar="DATE",
                        help="rebuild summary.md from evals/results/<DATE>/, no API call")
    parser.add_argument("--replay", metavar="RESULT_JSON",
                        help="re-run verify_report on a recorded result, no agent, no API")
    parser.add_argument("--price-input", type=float,
                        help="USD per million input tokens, for the cost column")
    parser.add_argument("--price-output", type=float,
                        help="USD per million output tokens, for the cost column")
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
            print(write_summary(args.summarize, load_cases(), args.price_input,
                                args.price_output))
            return 0
        if not args.live:
            _print_plan(cases)
            return 0
        date = args.date or calendar_date.today().isoformat()
        run_live(get_client(), cases, date)
        print(write_summary(date, load_cases(), args.price_input, args.price_output))
        return 0
    except Exception as error:  # one clean exit for a missing key, file or case id
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
