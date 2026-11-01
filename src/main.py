"""CLI entry point: grade-sheet photo + voice note → verified report (E4.4, issue #29)."""
import argparse
import sys
from pathlib import Path

from src.cli_run import (
    CliInputError,
    MUSE_SPARK_MODEL,
    answers_from_file,
    default_journal_path,
    print_outcome,
    resolve_path,
    run_cli_session,
    write_journal,
    write_run_summary,
)
from src.clients.meta_client import get_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the PathProof agent loop on a grade sheet and optional voice note.")
    parser.add_argument("--image", required=True, help="Path to the grade-sheet photo")
    parser.add_argument("--audio", help="Path to the voice note audio file")
    parser.add_argument(
        "--journal-out",
        help="Where to write the raw tool journal (JSON array). "
             "Default: evals/results/<image>_<audio>.json",
    )
    parser.add_argument(
        "--run-label",
        help="Stem for the default journal file under evals/results/ (e.g. e4.4_clear_sheet_d_medecin)",
    )
    parser.add_argument(
        "--answers-file",
        help="Text file with one student answer per line for ask_student (non-interactive replay)",
    )
    return parser


def _stdin_ask(question: str) -> str:
    print(question, file=sys.stderr)
    sys.stderr.write("> ")
    sys.stderr.flush()
    return sys.stdin.readline().rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        image_path = resolve_path(args.image, "Grade sheet")
        audio_path = resolve_path(args.audio, "Voice note") if args.audio else None
    except CliInputError as error:
        print(error, file=sys.stderr)
        return 2
    journal_path = (Path(args.journal_out) if args.journal_out else
                    default_journal_path(image_path, audio_path, args.run_label))
    if not journal_path.is_absolute():
        journal_path = Path.cwd() / journal_path
    client = get_client()
    if args.answers_file:
        ask_fn = answers_from_file(resolve_path(args.answers_file, "Answers file"))
    else:
        ask_fn = _stdin_ask
    result = run_cli_session(client, MUSE_SPARK_MODEL, image_path, audio_path, ask_fn)
    write_journal(journal_path, result.journal)
    write_run_summary(journal_path, result)
    print(f"Journal written to {journal_path}", file=sys.stderr)
    return print_outcome(result)


if __name__ == "__main__":
    raise SystemExit(main())
