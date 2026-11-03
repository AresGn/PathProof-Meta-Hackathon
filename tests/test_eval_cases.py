import json
from pathlib import Path
from types import SimpleNamespace

from src.agent import loop
from src.agent.prompts import SYSTEM_PROMPT
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
        assert isinstance(assertions["forbidden_strings"], list)
        assert all(isinstance(text, str) for text in assertions["forbidden_strings"])
        assert isinstance(assertions["expected_offer_ids"], list)
        assert all(offer_id.startswith("PUB-")
                   for offer_id in assertions["expected_offer_ids"])
        assert assertions["expected_question"] is None or isinstance(
            assertions["expected_question"], str
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


def test_case_oracle_is_not_in_the_agent_system_prompt():
    lowered_prompt = SYSTEM_PROMPT.casefold()
    assert "expected_behavior" not in lowered_prompt
    assert "forbidden_strings" not in lowered_prompt
    assert "expected_offer_ids" not in lowered_prompt

    for case in load_cases():
        client = ScriptedFakeClient([
            SimpleNamespace(content="Recorded fictional run.", tool_calls=None)
        ])
        loop.run(client, "test-model", None, json.dumps(case["input"], ensure_ascii=False))
        model_request = json.dumps(client.calls[0]["messages"], ensure_ascii=False).casefold()
        assert "assertions" not in model_request
        assert "expected_behavior" not in model_request
        assert "forbidden_strings" not in model_request
        assert "expected_offer_ids" not in model_request
        assert "expected_question" not in model_request
        for forbidden_string in case["assertions"]["forbidden_strings"]:
            assert forbidden_string.casefold() not in lowered_prompt
            assert forbidden_string.casefold() not in model_request
        for offer_id in case["assertions"]["expected_offer_ids"]:
            assert offer_id.casefold() not in model_request
