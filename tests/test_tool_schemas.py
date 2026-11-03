import json

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS

# Set by the loop, never offered to the model (the interface language).
LOOP_ROUTED_ARGUMENTS = {"build_report": {"language"}}
EXPECTED_TOOLS = {"transcribe_voice", "extract_profile", "read_grade_sheet",
                  "compute_ranking_average", "lookup_filieres", "ask_student",
                  "verify_report", "build_report"}


def test_tool_schemas_are_declared_once_and_cover_every_loop_tool():
    names = [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    assert set(names) == EXPECTED_TOOLS
    assert len(names) == len(set(names))
    assert set(loop.TOOLS) == EXPECTED_TOOLS


def test_every_tool_schema_is_a_function_schema_with_object_parameters():
    for schema in TOOL_SCHEMAS:
        assert schema["type"] == "function"
        function = schema["function"]
        assert function["name"] in loop.TOOLS
        assert function["description"].strip()
        parameters = function["parameters"]
        assert parameters["type"] == "object"
        assert isinstance(parameters["properties"], dict)
        assert parameters["properties"]
        for required in parameters.get("required", []):
            assert required in parameters["properties"]
    assert json.loads(json.dumps(TOOL_SCHEMAS)) == TOOL_SCHEMAS


def test_tool_schemas_match_function_signatures():
    import inspect
    by_name = {schema["function"]["name"]: schema["function"]["parameters"]
               for schema in TOOL_SCHEMAS}
    assert set(by_name) == set(loop.TOOLS)
    for name, tool in loop.TOOLS.items():
        parameters = inspect.signature(tool).parameters
        expected = ({param for param in parameters if param != "client"}
                    - LOOP_ROUTED_ARGUMENTS.get(name, set()))
        declared = set(by_name[name]["properties"])
        assert declared == expected, name
        for required in by_name[name].get("required", []):
            assert required in declared, (name, required)


def test_loop_defaults_to_the_shared_tool_schemas(monkeypatch):
    seen = {}

    class RecordingClient:
        def __init__(self):
            self.chat = self
            self.completions = self

        def create(self, **kwargs):
            seen.update(kwargs)
            from types import SimpleNamespace
            message = SimpleNamespace(content="Done.", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    result = loop.run(RecordingClient(), "fake-model", None, "Bonjour.")
    assert result == "Done."
    assert seen["tools"] == TOOL_SCHEMAS
