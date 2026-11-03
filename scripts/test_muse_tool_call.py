"""Test Muse Spark 1.3 tool choice (lookup_filieres). Writes docs/muse-spark-tool-call-results.md."""
from __future__ import annotations

import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
RUNS = 5
MODEL = "muse-spark-1.3"
OUT_PATH = ROOT / "docs" / "muse-spark-tool-call-results.md"

load_dotenv(ROOT / ".env")

if not os.environ.get("MUSE_API_KEY"):
    raise SystemExit("MUSE_API_KEY is not set (see .env)")

client = OpenAI(
    api_key=os.environ["MUSE_API_KEY"],
    base_url="https://api.meta.ai/v1",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "lookup_filieres",
            "description": "Liste les filières vérifiées pour une moyenne au BAC.",
            "parameters": {
                "type": "object",
                "properties": {"moyenne": {"type": "number"}},
                "required": ["moyenne"],
            },
        },
    }
]

question = "J'ai eu 13,5 au BAC C. Quelles filières me conviennent ?"

rows: list[dict] = []
console_buf = io.StringIO()

def log(line: str) -> None:
    print(line)
    console_buf.write(line + "\n")

for i in range(1, RUNS + 1):
    log(f"=== Run {i} ===")
    row: dict = {"run": i, "ok": False}
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
            tools=tools,
        )
        msg = resp.choices[0].message
        row["finish_reason"] = resp.choices[0].finish_reason
        row["content"] = msg.content
        row["tool_calls_raw"] = str(msg.tool_calls)
        log(f"finish_reason: {row['finish_reason']}")
        log(f"tool_calls: {msg.tool_calls}")
        log(f"content: {msg.content}")
        if msg.tool_calls:
            tc = msg.tool_calls[0]
            row["tool_name"] = tc.function.name
            row["tool_args"] = tc.function.arguments
            row["ok"] = (
                tc.function.name == "lookup_filieres"
                and "13.5" in tc.function.arguments
            )
        else:
            row["tool_name"] = None
            row["tool_args"] = None
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
        log(f"ERROR: {row['error']}")
    rows.append(row)
    log("")

passed = sum(1 for r in rows if r.get("ok"))
ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

lines = [
    "# Muse Spark 1.3 test — `lookup_filieres` tool call",
    "",
    "This report checks that the model **chooses the tool** it is offered (not the quality of its text answer).",
    "",
    f"- **Run date:** {ts}",
    f"- **Model:** `{MODEL}`",
    f"- **Endpoint:** `https://api.meta.ai/v1`",
    f"- **Runs:** {RUNS}",
    f"- **Passes:** {passed}/{RUNS}",
    "",
    "## Success criteria",
    "",
    "- `finish_reason` = `tool_calls`",
    "- `tool_calls[0].function.name` = `lookup_filieres`",
    "- JSON arguments containing `moyenne` = **13.5** (French decimal comma in the question)",
    "",
    "## Results",
    "",
    "| Run | OK | finish_reason | Tool | Arguments | content |",
    "| ---: | :---: | --- | --- | --- | --- |",
]

for r in rows:
    if "error" in r:
        lines.append(
            f"| {r['run']} | ❌ | — | — | — | Error: `{r['error']}` |"
        )
        continue
    ok = "✅" if r.get("ok") else "❌"
    content = (r.get("content") or "").replace("|", "\\|")
    if len(content) > 80:
        content = content[:77] + "…"
    lines.append(
        f"| {r['run']} | {ok} | `{r.get('finish_reason')}` | "
        f"`{r.get('tool_name')}` | `{r.get('tool_args')}` | {content} |"
    )

lines.extend(
    [
        "",
        "## Raw console output (5 runs)",
        "",
        "```text",
        console_buf.getvalue().rstrip(),
        "```",
        "",
        "## Rerun the test",
        "",
        "```bash",
        "python scripts/test_muse_tool_call.py",
        "```",
        "",
        "Prerequisite: `MUSE_API_KEY` in `.env` (see `.env.example`).",
        "",
    ]
)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT_PATH}")
sys.exit(0 if passed == RUNS else 1)
