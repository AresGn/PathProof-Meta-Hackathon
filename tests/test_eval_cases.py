import json
from pathlib import Path
from types import SimpleNamespace

from src.agent import loop
from src.agent.prompts import SYSTEM_PROMPT
from src.cli_run import build_user_message
from tests.fake_client import ScriptedFakeClient

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "cases.jsonl"
SAMPLES_PATH = ROOT / "data" / "samples"
CASE_IDS = {
    "clear_sheet_d_medecin",
    "clear_sheet_c",
    "blurry_photo",
    "missing_grade",
    "out_of_range_grade",
    "noisy_voice",
    "voice_contradicts_sheet",
    "unverified_trap",
    "false_friend",
    "concours_entry",
}
VOICE_CASE_IDS = {
    "noisy_voice",
    "voice_contradicts_sheet",
    "unverified_trap",
    "false_friend",
    "concours_entry",
}


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines()]


def build_case_message(case: dict) -> str:
    """The user message the CLI builds from the case files (--image, --audio, --voice-text)."""
    by_kind = {(sample["role"], sample["type"]): ROOT / sample["path"]
               for sample in case["input"]["files"]}
    text_path = by_kind.get(("voice", "text"))
    return build_user_message(
        by_kind.get(("grade_sheet", "image")),
        by_kind.get(("voice", "audio")),
        text_path.read_text(encoding="utf-8") if text_path else None,
    )


def test_eval_cases_reference_existing_fictional_assets_and_machine_assertions():
    cases = load_cases()
    samples_readme = (SAMPLES_PATH / "README.md").read_text(encoding="utf-8")
    assert {case["id"] for case in cases} == CASE_IDS
    assert len({case["id"] for case in cases}) == len(cases)

    for case in cases:
        assert case.get("status") != "sample file TODO"
        assert "expected_behavior" not in case
        assert "TODO" not in json.dumps(case, ensure_ascii=False)
        files = case["input"]["files"]
        assert files
        for sample in files:
            path = Path(sample["path"])
            assert path.parts[:2] == ("data", "samples")
            assert ".." not in path.parts
            assert (ROOT / path).is_file(), f"{case['id']}: missing {path}"
            if sample["role"] == "grade_sheet":
                assert sample["type"] == "image"
            else:
                assert sample["role"] == "voice"
                assert sample["type"] in {"audio", "text"}

        for sample in files:
            name = Path(sample["path"]).name
            listing = [line for line in samples_readme.splitlines() if f"`{name}`" in line]
            assert listing, f"{case['id']}: {name} is not listed"
            assert any("fictif" in line.casefold() or "fictive" in line.casefold()
                       for line in listing)

        assertions = case["assertions"]
        assert assertions["required_tools"]
        assert all(isinstance(tool, str) for tool in assertions["required_tools"])
        for key in ("forbidden_strings", "required_strings"):
            assert isinstance(assertions[key], list)
            assert all(isinstance(text, str) and text for text in assertions[key])
        assert isinstance(assertions["expected_offer_ids"], list)
        assert all(offer_id.startswith("PUB-")
                   for offer_id in assertions["expected_offer_ids"])
        expected_question = assertions["expected_question"]
        assert expected_question is None or (
            isinstance(expected_question, list) and expected_question
            and all(isinstance(text, str) and text for text in expected_question)
        )

    by_id = {case["id"]: case for case in cases}
    for case_id in VOICE_CASE_IDS:
        voice_files = [
            sample for sample in by_id[case_id]["input"]["files"]
            if sample["role"] == "voice"
        ]
        assert voice_files
        assert all(sample["type"] in {"audio", "text"} for sample in voice_files)

    for sample_path in SAMPLES_PATH.iterdir():
        if sample_path.name == "README.md":
            continue
        listing = [line for line in samples_readme.splitlines()
                   if f"`{sample_path.name}`" in line]
        assert listing, f"{sample_path.name} is not listed"
        assert any("fictif" in line.casefold() or "fictive" in line.casefold()
                   for line in listing), f"{sample_path.name} is not marked fictional"


def test_agent_source_does_not_load_evaluation_assertions():
    for source_path in (ROOT / "src").rglob("*.py"):
        source = source_path.read_text(encoding="utf-8")
        assert "cases.jsonl" not in source
        assert "expected_behavior" not in source
        assert "forbidden_strings" not in source
        assert "expected_offer_ids" not in source
        assert "expected_question" not in source
        assert "required_strings" not in source


def test_case_oracle_is_not_in_the_agent_system_prompt():
    lowered_prompt = SYSTEM_PROMPT.casefold()
    assert "expected_behavior" not in lowered_prompt
    assert "forbidden_strings" not in lowered_prompt
    assert "expected_offer_ids" not in lowered_prompt

    for case in load_cases():
        client = ScriptedFakeClient([
            SimpleNamespace(content="Recorded fictional run.", tool_calls=None)
        ])
        loop.run(client, "test-model", None, build_case_message(case))
        model_request = json.dumps(client.calls[0]["messages"], ensure_ascii=False).casefold()
        assert "assertions" not in model_request
        assert "expected_behavior" not in model_request
        assert "forbidden_strings" not in model_request
        assert "expected_offer_ids" not in model_request
        assert "expected_question" not in model_request
        assert "required_strings" not in model_request
        for text in (case["assertions"]["forbidden_strings"]
                     + case["assertions"]["required_strings"]):
            assert text.casefold() not in lowered_prompt
            assert text.casefold() not in model_request
        for offer_id in case["assertions"]["expected_offer_ids"]:
            assert offer_id.casefold() not in model_request
