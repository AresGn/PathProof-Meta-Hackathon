"""CLI entry point: grade-sheet photo + voice note → verified report (E4.4, issue #29)."""
import argparse
import sys
from pathlib import Path

from src.cli_run import (
    CliInputError,
    MUSE_SPARK_MODEL,
    CliRunResult,
    answers_from_file,
    default_journal_path,
    print_outcome,
    resolve_path,
    run_cli_session,
    summary_path_for_journal,
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


def configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def _stdin_ask(question: str) -> str:
    print(question, file=sys.stderr)
    sys.stderr.write("> ")
    sys.stderr.flush()
    return sys.stdin.readline().rstrip("\n")


def main(argv: list[str] | None = None) -> int:
    configure_stdio_utf8()
    args = build_parser().parse_args(argv)
    try:
        image_path = resolve_path(args.image, "Grade sheet")
        audio_path = resolve_path(args.audio, "Voice note") if args.audio else None
        ask_fn = (_stdin_ask if not args.answers_file else
                  answers_from_file(resolve_path(args.answers_file, "Answers file")))
    except CliInputError as error:
        print(error, file=sys.stderr)
        return 2
    journal_path = (Path(args.journal_out) if args.journal_out else
                    default_journal_path(image_path, audio_path, args.run_label))
    if not journal_path.is_absolute():
        journal_path = Path.cwd() / journal_path
    journal: list = []
    result: CliRunResult | None = None
    exit_code = 1
    try:
        client = get_client()
        result = run_cli_session(client, MUSE_SPARK_MODEL, image_path, audio_path, ask_fn,
                                 journal=journal)
        exit_code = print_outcome(result)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        exit_code = 2
    finally:
        if journal:
            write_journal(journal_path, journal)
            summary_path = summary_path_for_journal(journal_path)
            if result is not None:
                write_run_summary(journal_path, result)
            print(f"Journal written to {journal_path}", file=sys.stderr)
            print(f"Summary written to {summary_path}", file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
