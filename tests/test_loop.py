import json
from types import SimpleNamespace

import pytest

from src.agent import loop
from tests.fake_client import ScriptedFakeClient

QUESTION = "Quelle est ta note en SVT ?"
ANSWER = "Ma note en SVT est 15 sur 20."


def tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def assistant_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def asking_client(*extra_messages):
    ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": QUESTION})])
    return ScriptedFakeClient([ask, *extra_messages])


def tool_observations(call_snapshot):
    return [message for message in call_snapshot["messages"]
            if isinstance(message, dict) and message.get("role") == "tool"]


def test_loop_returns_needs_input_when_model_asks_student():
    client = asking_client()
    result = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    assert result["status"] == "needs_input"
    assert result["question"] == QUESTION
    assert len(client.calls) == 1


def test_without_answer_no_further_model_or_tool_call_is_made(monkeypatch):
    executed = []
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: executed.append(kwargs))
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": QUESTION}),
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"}),
    ])
    client = ScriptedFakeClient([ask])
    result = loop.run(client, "fake-model", [], "Je veux être médecin.")
    assert result["status"] == "needs_input"
    assert len(client.calls) == 1
    assert executed == []


def test_resume_answers_every_pending_tool_call(monkeypatch):
    # Regression: the real API refuses a resumed history where a tool call
    # from the same assistant message (here lookup_filieres, asked alongside
    # ask_student) never got a tool response. ScriptedFakeClient raises in
    # that case, so reaching the final text proves every call was answered.
    executed = []
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", lambda **kwargs: executed.append(kwargs))
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": QUESTION}),
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"}),
    ])
    client = ScriptedFakeClient([ask, assistant_message(content="Merci, je continue.")])
    suspended = loop.run(client, "fake-model", [], "Je veux être médecin.")
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    assert executed == []  # answered with an error, never executed
    observations = tool_observations(client.calls[1])
    by_id = {message["tool_call_id"]: message["content"] for message in observations}
    assert ANSWER in by_id["call-ask"]
    assert "not executed" in by_id["call-lookup"]


def test_only_the_first_question_is_surfaced_when_model_asks_two():
    ask = assistant_message(tool_calls=[
        tool_call("call-ask-1", "ask_student", {"question": QUESTION}),
        tool_call("call-ask-2", "ask_student", {"question": "Quelle est ta série ?"}),
    ])
    client = ScriptedFakeClient([ask, assistant_message(content="Merci, je continue.")])
    suspended = loop.run(client, "fake-model", [], "Bonjour.")
    assert suspended["question"] == QUESTION
    assert len(client.calls) == 1
    # The second question was never executed: on resume it gets the
    # "not executed" error, so the strict fake client accepts the history.
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    by_id = {m["tool_call_id"]: m["content"] for m in tool_observations(client.calls[1])}
    assert ANSWER in by_id["call-ask-1"]
    assert "not executed" in by_id["call-ask-2"]


def test_resume_feeds_the_answer_as_a_tool_observation():
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."
    assert len(client.calls) == 2
    observations = tool_observations(client.calls[1])
    assert observations
    assert observations[-1]["tool_call_id"] == "call-ask"
    assert ANSWER in observations[-1]["content"]


def test_resume_without_an_answer_makes_no_model_call():
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    result = loop.resume(client, "fake-model", [], suspended, "   ")
    assert result["status"] == "needs_input"
    assert result["question"] == QUESTION
    assert len(client.calls) == 1


def test_resume_with_a_malformed_state_fails_loudly():
    client = asking_client()
    with pytest.raises(KeyError):
        loop.resume(client, "fake-model", [], {"status": "needs_input"}, ANSWER)
    assert client.calls == []


def test_repeated_questions_stop_at_the_twelfth_step():
    scripted = [assistant_message(tool_calls=[
        tool_call(f"call-ask-{step}", "ask_student", {"question": QUESTION})])
        for step in range(loop.MAX_STEPS)]
    client = ScriptedFakeClient(scripted)
    result = loop.run(client, "fake-model", [], "Mon relevé est flou.")
    while isinstance(result, dict) and result.get("status") == "needs_input":
        result = loop.resume(client, "fake-model", [], result, ANSWER)
    assert result == "Stopped: step limit reached."
    assert len(client.calls) == loop.MAX_STEPS


def test_empty_question_from_the_model_is_an_observation_not_a_suspension():
    empty_ask = assistant_message(tool_calls=[tool_call("call-ask", "ask_student", {"question": "  "})])
    client = ScriptedFakeClient([empty_ask, assistant_message(content="Je reformule.")])
    result = loop.run(client, "fake-model", [], "Bonjour.")
    assert result == "Je reformule."
    assert len(client.calls) == 2
    observations = tool_observations(client.calls[1])
    assert observations and "non-empty" in observations[-1]["content"]


def always_tool_client(name, arguments):
    return ScriptedFakeClient([assistant_message(tool_calls=[
        tool_call(f"call-{step}", name, arguments)]) for step in range(20)])


def test_loop_stops_exactly_at_the_twelfth_step_when_model_always_calls_a_tool(monkeypatch):
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres",
                        lambda **kwargs: {"accessible": [], "excluded": []})
    journal = []
    client = always_tool_client("lookup_filieres", {"serie": "D"})
    result = loop.run(client, "fake-model", [], "Je veux etre medecin.", journal=journal)
    assert result == "Stopped: step limit reached."
    assert len(client.calls) == 12
    assert len(journal) == 12


def test_tool_exception_becomes_an_error_observation_and_the_loop_continues(monkeypatch):
    def failing_tool(**kwargs):
        raise RuntimeError("boom from the tool")

    monkeypatch.setitem(loop.TOOLS, "lookup_filieres", failing_tool)
    failing = assistant_message(tool_calls=[
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"})])
    client = ScriptedFakeClient([failing, assistant_message(content="Je continue.")])
    result = loop.run(client, "fake-model", [], "Je veux etre medecin.")
    assert result == "Je continue."
    observations = tool_observations(client.calls[1])
    assert observations and "boom from the tool" in observations[-1]["content"]


def test_unknown_tool_becomes_an_error_observation_and_the_loop_continues():
    unknown = assistant_message(tool_calls=[
        tool_call("call-unknown", "outil_inconnu", {"serie": "D"})])
    client = ScriptedFakeClient([unknown, assistant_message(content="Je continue.")])
    result = loop.run(client, "fake-model", [], "Bonjour.")
    assert result == "Je continue."
    observations = tool_observations(client.calls[1])
    assert observations and "unknown tool" in observations[-1]["content"]


FALSE_REPORT = {"schema_version": 1, "claims": [
    {"claim_id": "affirmation-fausse", "text": "Affirmation fausse.",
     "proofs": [{"type": "grade", "matiere": "SVT", "note": 19}]}]}
VERIFY_PROBLEMS = [{"claim_id": "affirmation-fausse", "type": "grade",
                    "reason": "grade proof does not match the grade sheet"}]
VERIFY_ARGS = {"report": FALSE_REPORT,
               "context": {"serie": "D", "grades": [], "transcript": ""}}


def verify_client(count):
    messages = [assistant_message(tool_calls=[
        tool_call(f"call-verify-{index}", "verify_report", VERIFY_ARGS)])
        for index in range(count)]
    return ScriptedFakeClient([*messages, assistant_message(content="Rapport final.")])


def stub_verify_report(monkeypatch, outcomes):
    remaining = list(outcomes)
    monkeypatch.setitem(loop.TOOLS, "verify_report",
                        lambda **kwargs: remaining.pop(0))


def test_three_consecutive_verify_refusals_stop_as_unverified_at_the_third(monkeypatch):
    stub_verify_report(monkeypatch, [VERIFY_PROBLEMS] * 6)
    journal = []
    client = verify_client(6)
    result = loop.run(client, "fake-model", [], "Voici mon brouillon.", journal=journal)
    assert result["status"] == "unverified"
    assert len(client.calls) == 3
    assert result["steps_used"] == 3
    assert result["problems"] == VERIFY_PROBLEMS
    assert result["refused_claims"] == FALSE_REPORT["claims"]
    assert result["report"] == FALSE_REPORT
    assert journal[-1]["decision"] == "stop_unverified"


def test_verify_refusal_counter_resets_after_a_successful_verify(monkeypatch):
    outcomes = [VERIFY_PROBLEMS, VERIFY_PROBLEMS, [],
                VERIFY_PROBLEMS, VERIFY_PROBLEMS]
    stub_verify_report(monkeypatch, outcomes)
    client = verify_client(len(outcomes))
    result = loop.run(client, "fake-model", [], "Voici mon brouillon.")
    assert result == "Rapport final."
    assert len(client.calls) == 6


def test_verify_refusals_keep_counting_across_a_suspension(monkeypatch):
    stub_verify_report(monkeypatch, [VERIFY_PROBLEMS] * 3)
    ask = assistant_message(tool_calls=[
        tool_call("call-ask", "ask_student", {"question": QUESTION})])
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[
            tool_call("call-verify-0", "verify_report", VERIFY_ARGS)]),
        assistant_message(tool_calls=[
            tool_call("call-verify-1", "verify_report", VERIFY_ARGS)]),
        ask,
        assistant_message(tool_calls=[
            tool_call("call-verify-2", "verify_report", VERIFY_ARGS)]),
        assistant_message(content="Rapport final."),
    ])
    suspended = loop.run(client, "fake-model", [], "Voici mon brouillon.")
    assert isinstance(suspended, dict) and suspended["status"] == "needs_input"
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result["status"] == "unverified"
    assert result["steps_used"] == 4


def test_journal_is_a_json_list_of_step_tool_args_result_decision_events(monkeypatch):
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres",
                        lambda **kwargs: {"accessible": [], "excluded": []})
    journal = []
    lookup = assistant_message(tool_calls=[
        tool_call("call-lookup", "lookup_filieres", {"serie": "D"})])
    client = ScriptedFakeClient([lookup, assistant_message(content="Termine.")])
    result = loop.run(client, "fake-model", [], "Je veux etre medecin.", journal=journal)
    assert result == "Termine."
    assert json.loads(json.dumps(journal, ensure_ascii=False)) == journal
    assert journal == [{"step": 1, "tool": "lookup_filieres", "args": {"serie": "D"},
                        "result": {"accessible": [], "excluded": []},
                        "decision": "continue"}]


def test_journal_travels_with_the_suspended_state_and_resume():
    journal = []
    client = asking_client(assistant_message(content="Merci, je continue."))
    suspended = loop.run(client, "fake-model", [], "Mon releve est flou.", journal=journal)
    assert suspended["journal"] is journal
    assert journal[-1]["tool"] == "ask_student"
    assert journal[-1]["decision"] == "suspend"
    result = loop.resume(client, "fake-model", [], suspended, ANSWER)
    assert result == "Merci, je continue."


def test_extra_schema_keys_are_filtered_before_the_tool_runs(monkeypatch):
    seen = {}
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres",
                        lambda **kwargs: seen.update(kwargs) or {"accessible": [], "excluded": []})
    journal = []
    lookup = assistant_message(tool_calls=[
        tool_call("call-lookup", "lookup_filieres", {"serie": "D", "client": "injected"})])
    client = ScriptedFakeClient([lookup, assistant_message(content="Termine.")])
    result = loop.run(client, "fake-model", None, "Je veux etre medecin.", journal=journal)
    assert result == "Termine."
    assert seen == {"serie": "D"}
    assert journal[0]["args"] == {"serie": "D"}


def raw_tool_call(call_id, name, raw_arguments):
    return SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=raw_arguments))


def test_malformed_json_arguments_become_an_invalid_arguments_observation():
    journal = []
    bad = assistant_message(tool_calls=[raw_tool_call("call-bad", "lookup_filieres", "{bad json")])
    client = ScriptedFakeClient([bad, assistant_message(content="Reformule.")])
    result = loop.run(client, "fake-model", [], "Bonjour.", journal=journal)
    assert result == "Reformule."
    assert len(client.calls) == 2
    observations = tool_observations(client.calls[1])
    assert observations and "invalid arguments" in observations[-1]["content"]
    assert journal[0]["decision"] == "continue"
    assert "invalid arguments" in journal[0]["result"]["error"]
    assert journal[0]["args"] == {"_raw_arguments": "{bad json"}


def test_non_object_json_arguments_become_an_invalid_arguments_observation():
    journal = []
    bad = assistant_message(tool_calls=[raw_tool_call("call-bad", "lookup_filieres", "[1, 2]")])
    client = ScriptedFakeClient([bad, assistant_message(content="Reformule.")])
    result = loop.run(client, "fake-model", [], "Bonjour.", journal=journal)
    assert result == "Reformule."
    observations = tool_observations(client.calls[1])
    assert observations and "invalid arguments" in observations[-1]["content"]
    assert journal[0]["args"] == {"_raw_arguments": "[1, 2]"}


def test_empty_schema_list_still_filters_like_the_shared_schemas(monkeypatch):
    seen = {}
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres",
                        lambda **kwargs: seen.update(kwargs) or {"accessible": [], "excluded": []})
    journal = []
    lookup = assistant_message(tool_calls=[
        tool_call("call-lookup", "lookup_filieres", {"serie": "D", "client": "injected"})])
    client = ScriptedFakeClient([lookup, assistant_message(content="Termine.")])
    result = loop.run(client, "fake-model", [], "Je veux etre medecin.", journal=journal)
    assert result == "Termine."
    assert seen == {"serie": "D"}
    assert journal[0]["args"] == {"serie": "D"}


def test_execute_tool_filters_once_and_returns_filtered_args():
    result, error, filtered = loop._execute_tool(
        "lookup_filieres", {"serie": "D", "client": "injected"}, None)
    assert error is None
    assert filtered == {"serie": "D"}
    assert result == {"accessible": [], "excluded": []} or isinstance(result, dict)


def test_refused_claims_ignores_problems_without_claim_id():
    report = {"claims": [{"claim_id": "kept", "text": "Gardee."},
                         {"text": "Sans identifiant."}]}
    problems = [{"type": "structure", "reason": "forme"}]
    assert loop._refused_claims(report, problems) == []


def test_ask_at_the_step_limit_is_journaled_as_a_stop_not_a_suspend():
    journal = []
    scripted = [assistant_message(tool_calls=[
        tool_call(f"call-ask-{step}", "ask_student", {"question": QUESTION})])
        for step in range(loop.MAX_STEPS)]
    client = ScriptedFakeClient(scripted)
    result = loop.run(client, "fake-model", [], "Mon relevé est flou.", journal=journal)
    while isinstance(result, dict) and result.get("status") == "needs_input":
        result = loop.resume(client, "fake-model", [], result, ANSWER)
    assert result == "Stopped: step limit reached."
    assert journal[-1]["tool"] == "ask_student"
    assert journal[-1]["decision"] == "stop_step_limit"


def test_verify_exception_leaves_the_refusal_counter_unchanged(monkeypatch):
    def raising_verify(**kwargs):
        raise RuntimeError("verifier crashed")
    monkeypatch.setitem(loop.TOOLS, "verify_report", raising_verify)
    journal = []
    failing = assistant_message(tool_calls=[
        tool_call("call-verify", "verify_report", VERIFY_ARGS)])
    client = ScriptedFakeClient([failing, assistant_message(content="Je continue.")])
    result = loop.run(client, "fake-model", [], "Voici mon brouillon.", journal=journal)
    assert result == "Je continue."
    observations = tool_observations(client.calls[1])
    assert observations and "verifier crashed" in observations[-1]["content"]
    assert journal[0]["decision"] == "continue"


def test_verify_exception_does_not_consume_a_refusal(monkeypatch):
    calls = {"count": 0}

    def flaky_verify(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("verifier crashed")
        return VERIFY_PROBLEMS
    monkeypatch.setitem(loop.TOOLS, "verify_report", flaky_verify)
    client = verify_client(5)
    result = loop.run(client, "fake-model", [], "Voici mon brouillon.")
    assert result["status"] == "unverified"
    assert len(client.calls) == 4


def test_multiple_calls_in_one_message_keep_counting_verify_in_the_middle(monkeypatch):
    seen = []
    monkeypatch.setitem(loop.TOOLS, "lookup_filieres",
                        lambda **kwargs: seen.append(kwargs) or {"accessible": [], "excluded": []})
    stub_verify_report(monkeypatch, [VERIFY_PROBLEMS])
    journal = []
    both = assistant_message(tool_calls=[
        tool_call("call-lookup-1", "lookup_filieres", {"serie": "D"}),
        tool_call("call-verify", "verify_report", VERIFY_ARGS),
        tool_call("call-lookup-2", "lookup_filieres", {"serie": "D"}),
    ])
    client = ScriptedFakeClient([both, assistant_message(content="Termine.")])
    result = loop.run(client, "fake-model", [], "Voici mon brouillon.", journal=journal)
    assert result == "Termine."
    assert seen == [{"serie": "D"}, {"serie": "D"}]
    assert [entry["tool"] for entry in journal] == ["lookup_filieres", "verify_report",
                                                   "lookup_filieres"]


def test_build_report_receives_the_draft_verify_report_accepted(monkeypatch):
    verified = {"schema_version": 1, "claims": [{"claim_id": "c1", "text": "ok", "proofs": []}]}
    drifted = {"schema_version": 1, "claims": [{"claim_id": "c1", "text": "ok", "proofs": [
        {"type": "filiere", "champ": "Mode_entrée", "valeur": "C, D"}]}]}
    context = {"grades": [], "serie": "D"}
    stub_verify_report(monkeypatch, [[]])
    received = {}
    monkeypatch.setitem(loop.TOOLS, "build_report",
                        lambda **kwargs: received.update(kwargs) or "Rapport.")
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("v", "verify_report", {"report": verified, "context": context})]),
        assistant_message(tool_calls=[tool_call("b", "build_report", {"report": drifted, "context": context})]),
        assistant_message(content="Rapport.")])
    journal = []
    loop.run(client, "fake-model", None, "Brouillon.", journal=journal)
    assert received["report"] == verified
    assert journal[-1]["args"]["report"] == verified


def test_build_report_keeps_the_model_draft_when_the_last_verify_was_refused(monkeypatch):
    draft = {"schema_version": 1, "claims": []}
    stub_verify_report(monkeypatch, [VERIFY_PROBLEMS])
    received = {}
    monkeypatch.setitem(loop.TOOLS, "build_report",
                        lambda **kwargs: received.update(kwargs) or "Refus.")
    client = ScriptedFakeClient([
        assistant_message(tool_calls=[tool_call("v", "verify_report", {"report": FALSE_REPORT, "context": {}})]),
        assistant_message(tool_calls=[tool_call("b", "build_report", {"report": draft, "context": {}})]),
        assistant_message(content="Fin.")])
    loop.run(client, "fake-model", None, "Brouillon.", journal=[])
    assert received["report"] == draft
