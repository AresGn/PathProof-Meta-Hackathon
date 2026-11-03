"""JSON schemas of the agent tools, declared in this single place (E4.1).

Every tool the model may call is described here, in the function-calling
shape the API expects, and nowhere else: the loop (`src/agent/loop.py`)
executes the functions of `TOOLS` by name, the CLI and the web pass
`TOOL_SCHEMAS` to the model. A schema added here without its function (or
the reverse) is caught by `tests/test_tool_schemas.py`. The vocabulary
keeps the French words of the data (`serie`, `matiere`, `filiere`).
"""

_GRADE_ENTRY = {
    "type": "object",
    "properties": {
        "matiere": {"type": "string"},
        "note": {"type": ["number", "null"]},
        "lisible": {"type": "boolean"},
    },
    "required": ["matiere", "note"],
}

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "transcribe_voice",
            "description": "Transcribe the student's voice note (audio file) to text.",
            "parameters": {
                "type": "object",
                "properties": {"audio_path": {"type": "string"}},
                "required": ["audio_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "extract_profile",
            "description": "Extract serie, declared average, interests, target job and "
                           "constraints from a transcript, each with its exact quote.",
            "parameters": {
                "type": "object",
                "properties": {"transcript": {"type": "string"}},
                "required": ["transcript"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_grade_sheet",
            "description": "Read a grade-sheet photo into grades; an unreadable grade is null.",
            "parameters": {
                "type": "object",
                "properties": {"image_path": {"type": "string"}},
                "required": ["image_path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_ranking_average",
            "description": "Compute the ranking average of one offer with the guide "
                           "formula (deterministic code; never compute it yourself).",
            "parameters": {
                "type": "object",
                "properties": {
                    "serie": {"type": "string"},
                    "offer_subjects": {"type": "array", "items": {"type": "string"}},
                    "grades": {"type": "array", "items": _GRADE_ENTRY},
                },
                "required": ["serie", "offer_subjects", "grades"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_filieres",
            "description": "List the guide offers accessible to a serie (strict access), "
                           "ranked, plus the excluded rows with their reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "serie": {"type": "string"},
                    "metier_vise": {"type": "string"},
                    "interets": {"type": "array", "items": {"type": "string"}},
                    "grades": {"type": "array", "items": _GRADE_ENTRY},
                },
                "required": ["serie"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_student",
            "description": "Ask the student one question and pause; use it whenever a "
                           "value is unreadable, missing or contradictory.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_report",
            "description": "Check every proof of a draft report against its source "
                           "(deterministic code); an empty list means fully proven.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report": {"type": "object"},
                    "context": {"type": "object"},
                },
                "required": ["report", "context"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_report",
            "description": "Format the verified report for the student.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report": {"type": "object"},
                    "context": {"type": "object"},
                    "refused_claims": {"type": "array", "items": {"type": "object"}},
                },
                "required": ["report", "context"],
                "additionalProperties": False,
            },
        },
    },
]
