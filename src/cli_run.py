"""End-to-end CLI session: paths in, agent loop, journal and report out (E4.4).

Orchestration only: business logic stays in tools and loop. Real API calls
need MUSE_API_KEY; unit tests inject a fake client and a scripted ask callback.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from src.agent import loop
from src.agent.tool_schemas import TOOL_SCHEMAS
from src.clients.muse_spark import MUSE_SPARK_MODEL

BUILD_REPORT_TOOL = "build_report"
VERIFY_REPORT_TOOL = "verify_report"


class CliInputError(ValueError):
    """Missing file or invalid CLI arguments."""


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    streaming_calls: int = 0

    def add(self, usage: object) -> None:
        if usage is None:
            return
        self.prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
        self.completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        self.total_tokens += int(getattr(usage, "total_tokens", 0) or 0)


@dataclass
class CliRunResult:
    image_path: Path
    audio_path: Path | None
    journal: list
    outcome: str | dict
    report_text: str | None
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_seconds: float = 0.0
    questions: list[str] = field(default_factory=list)

    @property
    def distinct_tool_count(self) -> int:
        return len({event["tool"] for event in self.journal if event.get("tool")})

    @property
    def max_model_step(self) -> int:
        steps: list[int] = []
        for event in self.journal:
            step = event.get("step")
            if isinstance(step, bool) or step is None:
                continue
            if isinstance(step, (int, float)):
                steps.append(int(step))
        if steps:
            return max(steps)
        if isinstance(self.outcome, dict) and isinstance(self.outcome.get("steps_used"), int):
            return self.outcome["steps_used"]
        return 0


class UsageTrackingClient:
    """Delegate to the real client; count tokens on non-streaming completions only."""

    def __init__(self, inner, usage: TokenUsage):
        self._inner = inner
        self._usage = usage
        self._chat = _UsageTrackingChat(inner.chat, usage)

    def __getattr__(self, name: str):
        if name == "chat":
            return self._chat
        return getattr(self._inner, name)


class _UsageTrackingChat:
    def __init__(self, chat, usage: TokenUsage):
        self._chat = chat
        self._completions = _UsageTrackingCompletions(chat.completions, usage)

    def __getattr__(self, name: str):
        if name == "completions":
            return self._completions
        return getattr(self._chat, name)


class _UsageTrackingCompletions:
    def __init__(self, completions, usage: TokenUsage):
        self._completions = completions
        self._usage = usage
        original_create = completions.create

        def tracked_create(**kwargs):
            if kwargs.get("stream"):
                usage.streaming_calls += 1
                return original_create(**kwargs)
            response = original_create(**kwargs)
            usage.add(getattr(response, "usage", None))
            return response

        self.create = tracked_create

    def __getattr__(self, name: str):
        return getattr(self._completions, name)


def resolve_path(path: str | Path, label: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise CliInputError(f"{label} not found: {resolved}")
    return resolved


def path_for_agent(path: Path) -> str:
    """Prefer a repo-relative POSIX path so journals replay on any OS."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def build_user_message(image_path: Path, audio_path: Path | None) -> str:
    image_arg = path_for_agent(image_path)
    lines = [
        "The student submitted a grade-sheet photo and a voice note (fictional sample).",
        f"Grade sheet image path (pass verbatim to read_grade_sheet): {image_arg}",
    ]
    if audio_path is not None:
        lines.append(
            "Voice note audio path (pass verbatim to transcribe_voice): "
            f"{path_for_agent(audio_path)}")
    lines.append(
        "Run the full tool loop and produce a verified orientation report via "
        "verify_report then build_report.")
    return "\n".join(lines)


def _tool_events(journal: list) -> list:
    return [event for event in journal if event.get("tool")]


def report_from_journal(journal: list) -> str | None:
    for event in reversed(journal):
        if event.get("tool") != BUILD_REPORT_TOOL:
            continue
        if event.get("decision") != loop.DECISION_CONTINUE:
            continue
        result = event.get("result")
        if isinstance(result, str) and result.strip():
            return result
    return None


def verified_report_from_journal(journal: list) -> str | None:
    """Return build_report text only if it is the last tool call and follows empty verify_report."""
    events = _tool_events(journal)
    if not events or events[-1].get("tool") != BUILD_REPORT_TOOL:
        return None
    build = events[-1]
    if build.get("decision") != loop.DECISION_CONTINUE:
        return None
    build_text = build.get("result")
    if not isinstance(build_text, str) or not build_text.strip():
        return None
    for event in reversed(events[:-1]):
        if event.get("tool") != VERIFY_REPORT_TOOL:
            continue
        if event.get("decision") != loop.DECISION_CONTINUE:
            return None
        if event.get("result") != []:
            return None
        return build_text
    return None


def verify_problems_from_journal(journal: list) -> list | None:
    for event in reversed(journal):
        if event.get("tool") != VERIFY_REPORT_TOOL:
            continue
        result = event.get("result")
        if isinstance(result, list):
            return result
    return None


def default_journal_path(image_path: Path, audio_path: Path | None, label: str | None) -> Path:
    if label:
        stem = label
    elif audio_path is not None:
        stem = f"{image_path.stem}_{audio_path.stem}"
    else:
        stem = image_path.stem
    return Path("evals") / "results" / f"{stem}.json"


def summary_path_for_journal(journal_path: Path) -> Path:
    """Summary path is derived from the full journal file name, not stem only."""
    return journal_path.with_name(f"{journal_path.name}.summary.txt")


def write_journal(path: Path, journal: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(journal, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def _path_for_log(path: Path | None) -> str:
    if path is None:
        return "(none)"
    return path_for_agent(path)


def write_run_summary(journal_path: Path, result: CliRunResult) -> None:
    summary_path = summary_path_for_journal(journal_path)
    lines = [
        f"CLI run E4.4 — {journal_path.name}",
        f"Image: {_path_for_log(result.image_path)}",
        f"Audio: {_path_for_log(result.audio_path)}",
        f"Duration: {result.duration_seconds:.1f}s",
        f"Tool call events in journal: {len(result.journal)}",
        f"Distinct tools: {result.distinct_tool_count}",
        f"Max model step reached: {result.max_model_step} (limit {loop.MAX_STEPS})",
        (f"Token usage (non-streaming Muse Spark completions): prompt="
         f"{result.usage.prompt_tokens}, completion={result.usage.completion_tokens}, "
         f"total={result.usage.total_tokens}"),
    ]
    if result.usage.streaming_calls:
        lines.append(f"Streaming completion calls (usage not counted): "
                     f"{result.usage.streaming_calls}")
    lines.append(f"Student questions asked: {len(result.questions)}")
    for index, question in enumerate(result.questions, start=1):
        lines.append(f"  Q{index}: {question}")
    if isinstance(result.outcome, dict):
        lines.append(f"Outcome status: {result.outcome.get('status')}")
    elif result.outcome == loop.STOPPED_STEP_LIMIT:
        lines.append("Outcome: step limit reached")
    else:
        lines.append("Outcome: finished")
    verify = verify_problems_from_journal(result.journal)
    if verify is not None:
        lines.append(f"Last verify_report problems: {len(verify)}")
    if result.report_text:
        lines.append("Report: verified (printed on stdout)")
    elif isinstance(result.outcome, dict) and result.outcome.get("status") == "unverified":
        lines.append("Report: not verified (unverified stop)")
    elif result.outcome == loop.STOPPED_STEP_LIMIT:
        lines.append("Report: not verified (step limit)")
    else:
        lines.append("Report: not verified")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def persist_run_artifacts(journal_path: Path, journal: list,
                          result: CliRunResult | None) -> None:
    """Write journal and optional summary; never raise (errors go to stderr)."""
    if not journal:
        return
    try:
        write_journal(journal_path, journal)
        print(f"Journal written to {journal_path}", file=sys.stderr)
    except OSError as error:
        print(f"Could not write journal: {error}", file=sys.stderr)
        return
    if result is None:
        return
    summary_path = summary_path_for_journal(journal_path)
    try:
        write_run_summary(journal_path, result)
        print(f"Summary written to {summary_path}", file=sys.stderr)
    except OSError as error:
        print(f"Could not write summary: {error}", file=sys.stderr)


def answers_from_lines(lines: list[str]) -> Callable[[str], str]:
    """Return answers in order; blank lines are skipped when reading a file."""
    queue = [line for line in lines if line.strip()]
    index = 0

    def ask(_question: str) -> str:
        nonlocal index
        if index >= len(queue):
            return ""
        answer = queue[index]
        index += 1
        return answer

    return ask


def answers_from_file(path: Path) -> Callable[[str], str]:
    return answers_from_lines(path.read_text(encoding="utf-8").splitlines())


def run_cli_session(
    client,
    model: str,
    image_path: Path,
    audio_path: Path | None,
    ask_student: Callable[[str], str],
    *,
    tool_schemas: list[dict] | None = None,
    journal: list | None = None,
) -> CliRunResult:
    """Run the agent loop until it finishes or ask_student gets no answer."""
    usage = TokenUsage()
    tracked = UsageTrackingClient(client, usage)
    journal = journal if journal is not None else []
    user_input = build_user_message(image_path, audio_path)
    schemas = TOOL_SCHEMAS if tool_schemas is None else tool_schemas
    started = time.monotonic()
    questions: list[str] = []
    outcome = loop.run(tracked, model, schemas, user_input, journal=journal)
    while isinstance(outcome, dict) and outcome.get("status") == "needs_input":
        question = outcome["question"]
        questions.append(question)
        answer = ask_student(question)
        if not isinstance(answer, str) or not answer.strip():
            break
        outcome = loop.resume(tracked, model, schemas, outcome, answer)
    report_text = verified_report_from_journal(journal)
    duration = time.monotonic() - started
    return CliRunResult(image_path=image_path, audio_path=audio_path, journal=journal,
                        outcome=outcome, report_text=report_text, usage=usage,
                        duration_seconds=duration, questions=questions)


def print_outcome(result: CliRunResult, *, stream=None) -> int:
    """Print the report or an error; return a process exit code."""
    stream = stream or sys.stdout
    if isinstance(result.outcome, dict) and result.outcome.get("status") == "unverified":
        print("Run stopped: report could not be fully verified (unverified).",
              file=sys.stderr)
        return 1
    if result.outcome == loop.STOPPED_STEP_LIMIT:
        print(loop.STOPPED_STEP_LIMIT, file=sys.stderr)
        return 1
    if isinstance(result.outcome, dict) and result.outcome.get("status") == "needs_input":
        print("Run stopped: student did not answer.", file=sys.stderr)
        return 1
    verified = result.report_text
    if verified:
        stream.write(verified)
        if not verified.endswith("\n"):
            stream.write("\n")
        return 0
    if isinstance(result.outcome, str) and result.outcome.strip():
        print("Run finished without a verified report.", file=sys.stderr)
        print(result.outcome.strip(), file=sys.stderr)
        return 1
    print("Run finished without a build_report output.", file=sys.stderr)
    return 1
