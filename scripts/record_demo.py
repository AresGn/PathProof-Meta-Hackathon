"""Generate the static, fictional fallback run from a successful real run."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.cli_run import run_cli_session, verified_report_from_journal
from src.clients.meta_client import get_client
from src.clients.muse_spark import MUSE_SPARK_MODEL

# Fixed fictional inputs documented in data/samples/README.md.
IMAGE_PATH = Path("data/samples/releve_serie_d.jpg")
AUDIO_PATH = Path("data/samples/note_vocale_coherente.mp3")
OUTPUT_PATH = ROOT / "web" / "recorded-run.json"


def is_fixed_sample_path(value: object, sample: Path) -> bool:
    if not isinstance(value, str):
        return False
    candidate = Path(value.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve() == (ROOT / sample).resolve()


def create_recorded_run(journal: list[dict]) -> dict:
    """Return display events only for the fixed fictional samples and verified report."""
    if not isinstance(journal, list) or not all(isinstance(event, dict) for event in journal):
        raise ValueError("journal must be a list of events from fixed fictional sample files")
    has_sample_image = any(
        event.get("tool") == "read_grade_sheet"
        and isinstance(event.get("args"), dict)
        and is_fixed_sample_path(event["args"].get("image_path"), IMAGE_PATH)
        for event in journal
    )
    has_sample_audio = any(
        event.get("tool") == "transcribe_voice"
        and isinstance(event.get("args"), dict)
        and is_fixed_sample_path(event["args"].get("audio_path"), AUDIO_PATH)
        for event in journal
    )
    if not has_sample_image or not has_sample_audio:
        raise ValueError("journal must use both fixed fictional sample files")

    report = verified_report_from_journal(journal)
    if not report:
        raise ValueError("journal must end with a verified report")

    events = [
        {
            "type": "step",
            "step": event.get("step"),
            "tool": event.get("tool"),
            "args": event.get("args"),
            "result": event.get("result"),
            "decision": event.get("decision"),
        }
        for event in journal
        if event.get("tool")
    ]
    events.append({
        "type": "done",
        "run_id": "recorded",
        "status": "ok",
        "report": report,
    })
    return {"events": events}


def answer_fictional_question(question: str) -> str:
    """Answer only the known series-confirmation question for the fixed sample."""
    if "série" not in question.casefold() and "serie" not in question.casefold():
        return ""
    return "Oui, série D."


def run_fictional_sample() -> list[dict]:
    """Run the fixed fictional photo and voice sample through the live agent."""
    if Path.cwd().resolve() != ROOT:
        raise ValueError("run this script from the repository root")
    journal: list[dict] = []
    result = run_cli_session(
        get_client(),
        MUSE_SPARK_MODEL,
        IMAGE_PATH,
        AUDIO_PATH,
        answer_fictional_question,
        tool_schemas=TOOL_SCHEMAS,
        journal=journal,
    )
    report = verified_report_from_journal(journal)
    if (result.outcome == loop.STOPPED_STEP_LIMIT
            or (isinstance(result.outcome, dict)
                and result.outcome.get("status") == "needs_input")
            or not report or result.report_text != report):
        raise ValueError("the fictional run did not finish with a successful verified report")
    return journal


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description="Regenerate web/recorded-run.json from a real fictional run.")


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    try:
        journal = run_fictional_sample()
        recording = create_recorded_run(journal)
        OUTPUT_PATH.write_text(
            json.dumps(recording, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Could not generate the recorded run: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
