"""Generate the static, fictional fallback run from a successful real run."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.cli_run import run_cli_session, verified_report_from_journal
from src.clients.meta_client import get_client
from src.clients.muse_wonder import MUSE_CONTRIBUTOR_MODEL, MUSE_WONDER_MODEL
from src.domain.report_text import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, report_text

# Fixed fictional inputs documented in data/samples/README.md.
IMAGE_PATH = Path("data/samples/releve_serie_d.jpg")
AUDIO_PATH = Path("data/samples/note_vocale_coherente.mp3")
OUTPUT_PATH = ROOT / "web" / "recorded-run.json"  # French reference recording
OUTPUT_PATH_BY_LANGUAGE = {
    "fr": OUTPUT_PATH,
    "en": ROOT / "web" / "recorded-run.en.json",  # docs/decisions.md E5.6
}
FICTIONAL_QUESTION = (
    "Pouvez-vous confirmer que vous êtes bien en série D, comme indiqué sur votre relevé ?"
)
# English: the model words the question itself, so accept only a question that
# asks about the serie D of the fixed sample, never an arbitrary one.
ENGLISH_QUESTION_PATTERN = re.compile(r"\bseries?\s+D\b", re.IGNORECASE)
FICTIONAL_ANSWER = {"fr": "Oui, série D.", "en": "Yes, serie D."}
# Replacements of the verified wording of src/domain/report_text.py, read from there.
RECORDED_WORDING = {
    "fr": {
        "title": "PathProof — rapport enregistré",
        "limits": ("## Limites du rapport enregistré\n"
                   "Les affirmations et leurs preuves sont reprises du journal de démonstration."),
        "claim_word": "vérifi",
    },
    "en": {
        "title": "PathProof — recorded report",
        "limits": ("## Limits of the recorded report\n"
                   "The claims and their proofs are taken from the demonstration log."),
        "claim_word": "verif",
    },
}


def is_fixed_sample_path(value: object, sample: Path) -> bool:
    if not isinstance(value, str):
        return False
    candidate = Path(value.replace("\\", "/"))
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    return candidate.resolve() == (ROOT / sample).resolve()


def create_recorded_run(journal: list[dict], language: str = DEFAULT_LANGUAGE) -> dict:
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

    validate_fictional_question_sequence(journal, language)

    report = verified_report_from_journal(journal)
    if not report:
        raise ValueError("journal must end with a verified report")
    report = make_recorded_report(report, language)

    events = [
        {
            "type": "step",
            "step": event.get("step"),
            "tool": event.get("tool"),
            "args": event.get("args"),
            "result": report if event.get("tool") == "build_report" else event.get("result"),
            "decision": event.get("decision"),
            "model": event.get("model"),
        }
        for event in journal
        if event.get("tool") and event.get("tool") != "ask_student"
    ]
    events.append({
        "type": "done",
        "run_id": "recorded",
        "status": "ok",
        "report": report,
    })
    return {"events": events}


def normalize_question(question: object) -> str | None:
    if not isinstance(question, str):
        return None
    return " ".join(question.split()).casefold()


def is_expected_question(question: object, language: str) -> bool:
    if language == "en":
        return isinstance(question, str) and bool(ENGLISH_QUESTION_PATTERN.search(question))
    return normalize_question(question) == normalize_question(FICTIONAL_QUESTION)


def validate_fictional_question_sequence(journal: list[dict],
                                         language: str = DEFAULT_LANGUAGE) -> None:
    question_steps = [
        (index, event) for index, event in enumerate(journal)
        if event.get("tool") == "ask_student"
    ]
    if len(question_steps) != 1:
        raise ValueError("journal must contain the expected fictional question")
    question_index, question_event = question_steps[0]
    if (not isinstance(question_event.get("args"), dict)
            or not is_expected_question(question_event["args"].get("question"), language)
            or not isinstance(question_event.get("result"), dict)
            or question_event["result"].get("status") != "needs_input"
            or not is_expected_question(question_event["result"].get("question"), language)
            or question_event.get("decision") != "suspend"):
        raise ValueError("journal must contain the expected fictional question")
    final_steps = [
        index for index, event in enumerate(journal)
        if event.get("tool") in {"verify_report", "build_report"}
    ]
    if not final_steps or question_index >= min(final_steps):
        raise ValueError("the fictional question must precede report verification")


def make_recorded_report(report: str, language: str = DEFAULT_LANGUAGE) -> str:
    wording = RECORDED_WORDING[language]
    text_of = report_text(language)
    verified_title = text_of["title"].split("\n", 1)[0]
    verified_limits = f'{text_of["h_unverified"]}\n{text_of["all_verified"]}'
    report = report.replace(verified_title, wording["title"])
    report = report.replace(verified_limits, wording["limits"])
    if wording["claim_word"] in report.casefold():
        raise ValueError("recorded report must not claim verification")
    return report


def answer_fictional_question(question: str, language: str = DEFAULT_LANGUAGE) -> str:
    """Answer only the known series-confirmation question for the fixed sample."""
    if not is_expected_question(question, language):
        return ""
    return FICTIONAL_ANSWER[language]


def run_fictional_sample(language: str = DEFAULT_LANGUAGE) -> list[dict]:
    """Run the fixed fictional photo and voice sample through the live agent."""
    if Path.cwd().resolve() != ROOT:
        raise ValueError("run this script from the repository root")
    journal: list[dict] = []
    result = run_cli_session(
        get_client(),
        MUSE_CONTRIBUTOR_MODEL,
        IMAGE_PATH,
        AUDIO_PATH,
        lambda question: answer_fictional_question(question, language),
        tool_schemas=TOOL_SCHEMAS,
        journal=journal,
        language=language,
        drafting_model=MUSE_WONDER_MODEL,
    )
    validate_fictional_question_sequence(journal, language)
    report = verified_report_from_journal(journal)
    if (result.outcome == loop.STOPPED_STEP_LIMIT
            or (isinstance(result.outcome, dict)
                and result.outcome.get("status") == "needs_input")
            or not report or result.report_text != report):
        raise ValueError("the fictional run did not finish with a successful verified report")
    return journal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Regenerate a recorded run (web/recorded-run*.json) from a real fictional run.")
    parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, default=DEFAULT_LANGUAGE,
                        help="report language of the recording (default: fr)")
    return parser


def main(argv: list[str] | None = None) -> int:
    language = build_parser().parse_args(argv).language
    output_path = OUTPUT_PATH_BY_LANGUAGE[language]
    try:
        journal = run_fictional_sample(language)
        recording = create_recorded_run(journal, language)
        # Write then rename: an interrupted run must not leave a truncated
        # fixture, which the page would report as invalid when the fallback is needed.
        temporary_path = output_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(recording, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Could not generate the recorded run: {error}", file=sys.stderr)
        return 1
    print(f"Wrote {output_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
