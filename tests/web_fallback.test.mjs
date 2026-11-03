import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

globalThis.window = {
  localStorage: { getItem: () => "en", setItem: () => {} },
};

const {
  recordedFailureReason,
  shouldUseRecordedRun,
  streamAnswer,
  validateRecordedRun,
} = await import("../web/js/api.js");
const recording = JSON.parse(
  await readFile(new URL("../web/recorded-run.json", import.meta.url), "utf8")
);

test("fallback is reserved for network and server failures", () => {
  assert.equal(shouldUseRecordedRun(new TypeError("fetch failed")), true);
  assert.equal(shouldUseRecordedRun({ name: "AbortError" }), true);
  assert.equal(shouldUseRecordedRun({ infrastructureFailure: true }), true);
  assert.equal(shouldUseRecordedRun({ status: 503 }), true);
  assert.equal(shouldUseRecordedRun({ status: 400 }), false);
  assert.equal(shouldUseRecordedRun({ status: 413 }), false);
  assert.equal(shouldUseRecordedRun({ status: 415 }), false);
  assert.equal(shouldUseRecordedRun({ status: 404 }), false);
});

test("recorded report must match the verified draft and final build step", () => {
  assert.equal(validateRecordedRun(recording), true);

  const reorderedKeys = structuredClone(recording);
  const reorderedBuild = reorderedKeys.events.find(
    (event) => event.type === "step" && event.tool === "build_report"
  );
  reorderedBuild.args.context = Object.fromEntries(
    Object.entries(reorderedBuild.args.context).reverse()
  );
  assert.equal(validateRecordedRun(reorderedKeys), true);

  const mismatchedReport = structuredClone(recording);
  const build = mismatchedReport.events.find(
    (event) => event.type === "step" && event.tool === "build_report"
  );
  build.args.report.claims[0].text = "Unverified altered claim.";
  assert.equal(validateRecordedRun(mismatchedReport), false);

  const mismatchedBuild = structuredClone(recording);
  const finalBuild = mismatchedBuild.events.find(
    (event) => event.type === "step" && event.tool === "build_report"
  );
  finalBuild.result = "Different report";
  assert.equal(validateRecordedRun(mismatchedBuild), false);

  const mismatchedContext = structuredClone(recording);
  const acceptedVerification = [...mismatchedContext.events]
    .reverse()
    .find((event) => event.type === "step" && event.tool === "verify_report"
      && event.result.length === 0);
  const verifiedBuild = mismatchedContext.events.find(
    (event) => event.type === "step" && event.tool === "build_report"
  );
  verifiedBuild.args.context.serie = "C";
  assert.notDeepEqual(verifiedBuild.args.context, acceptedVerification.args.context);
  assert.equal(validateRecordedRun(mismatchedContext), false);
});

test("recorded fallback reason is localized from error data", async () => {
  assert.match(recordedFailureReason(new TypeError("offline")), /server unreachable/i);
  assert.match(recordedFailureReason({ status: 503 }), /503/);
  assert.match(recordedFailureReason({ interrupted: true, messageKey: "answerInterrupted" }), /answer did not go through/i);
  const { setLanguage } = await import("../web/js/i18n.js");
  setLanguage("fr");
  assert.match(recordedFailureReason(new TypeError("offline")), /serveur injoignable/i);
  assert.match(recordedFailureReason({ status: 503 }), /503/);
  assert.match(recordedFailureReason({ interrupted: true, messageKey: "answerInterrupted" }), /réponse n’a pas abouti/i);
  setLanguage("en");
});

test("answer SSE errors and interruptions are classified centrally", async () => {
  const originalFetch = globalThis.fetch;
  const originalLocation = globalThis.window.location;
  let answerResponse;
  globalThis.window.location = {
    hostname: "127.0.0.1",
    origin: "http://127.0.0.1:8000",
  };
  globalThis.fetch = async (url) => {
    if (String(url).endsWith("/health")) {
      return new Response(JSON.stringify({ service: "pathproof-demo" }), { status: 200 });
    }
    return answerResponse;
  };

  try {
    answerResponse = new Response(
      'data: {"type":"error","run_id":"retry-id","error":"backend failed"}\n\n',
      { status: 200 }
    );
    const observed = [];
    await assert.rejects(
      streamAnswer("retry-id", "D", (event) => observed.push(event)),
      (error) => error.infrastructureFailure === true
    );
    assert.equal(observed[0].type, "error");

    answerResponse = new Response(
      'data: {"type":"step","tool":"ask_student"}\n\n',
      { status: 200 }
    );
    await assert.rejects(
      streamAnswer("retry-id", "D", () => {}),
      (error) => error.interrupted === true
        && shouldUseRecordedRun(error)
        && recordedFailureReason(error).includes("answer did not go through")
    );

    answerResponse = new Response(JSON.stringify({ detail: "invalid answer" }), { status: 400 });
    await assert.rejects(
      streamAnswer("retry-id", "", () => {}),
      (error) => error.status === 400 && !shouldUseRecordedRun(error)
    );
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.window.location = originalLocation;
  }
});
