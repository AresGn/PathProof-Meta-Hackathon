// Demo orchestration: wires the form, examples, answer flow and language
// switch to the API stream and the views. No rendering or HTTP code here:
// see steps.js, proofs.js, report.js, api.js, i18n.js and format.js.
import { applyTranslations, getLanguage, setLanguage, t } from "./i18n.js";
import {
  describeClientError, ensureApiBase, fetchRecordedRun, fetchSampleFile,
  recordedFailureReason, shouldUseRecordedRun,
  preloadRecordedRun,
  setServerStateListener, streamAnswer, streamRun,
} from "./api.js";
import { renderSteps } from "./steps.js";
import { createAgentMap } from "./agent-map.js";
import { initReveal } from "./motion.js";
import { createProofViewer, verifiedClaims, verifiedContext } from "./proofs.js";
import { renderProblems, renderReport } from "./report.js";

const form = document.getElementById("demo-form");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const submitBtn = document.getElementById("submit-btn");
const busyBar = document.getElementById("busy-bar");
const serverStatusEl = document.getElementById("server-status");
const recordedBanner = document.getElementById("recorded-banner");
const answerBlock = document.getElementById("answer-block");
const questionEl = document.getElementById("question");
const answerInput = document.getElementById("answer-input");
const answerBtn = document.getElementById("answer-btn");
const proofDialog = document.getElementById("proof-dialog");
const agentPanel = document.getElementById("agent-panel");
const agentMap = createAgentMap(document.getElementById("agent-map"));
const exampleBtns = [...document.querySelectorAll("[data-example]")];
const langBtns = [...document.querySelectorAll("[data-set-lang]")];

const reportView = {
  report: document.getElementById("report"),
  claims: document.getElementById("claims"),
  proofs: document.getElementById("proofs"),
  banner: document.getElementById("verified-banner"),
};

// One-click fictional examples (data/samples/README.md): nothing to prepare.
const EXAMPLES = {
  coherent: { image: "releve_serie_d.jpg", audio: "note_vocale_coherente.mp3" },
  blurry: { image: "releve_serie_d_flou.jpg", audio: null },
  contradictory: { image: "releve_serie_d.jpg", audio: "note_vocale_contradictoire.mp3" },
};

let currentRunId = null;
let seenSteps = [];
let submittedText = "";
let runBusy = false;
let serverState = "checking";
let lastReport = null;
let lastReportVerified = false;
let lastProblems = null;
let recordedRunState = null;

const proofViewer = createProofViewer({
  dialog: proofDialog,
  title: document.getElementById("proof-title"),
  body: document.getElementById("proof-body"),
  getSteps: () => seenSteps,
  getVerifiedContext: () => verifiedContext(seenSteps),
});

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "muted";
}

function renderServerStatus() {
  const keys = {
    ready: "serverReady", "ready-local": "serverReadyLocal",
    down: "serverDown", checking: "serverChecking",
  };
  serverStatusEl.textContent = t(keys[serverState] || "serverChecking");
  serverStatusEl.className = serverState === "down" ? "bad" : "";
}

function drawAgent() {
  agentMap.update(seenSteps, { busy: runBusy, waiting: !answerBlock.hidden });
}

function drawSteps(force = false) {
  renderSteps(stepsEl, seenSteps, runBusy, force);
  drawAgent();
}

function showReport(report, isVerified = false) {
  lastReport = report;
  lastReportVerified = isVerified;
  renderReport(
    reportView,
    report,
    isVerified ? verifiedClaims(seenSteps) : [],
    proofViewer.openProof,
    isVerified
  );
}

function showProblems(problems) {
  lastProblems = problems;
  renderProblems(reportView, problems);
}

function setRunBusy(busy) {
  runBusy = busy;
  submitBtn.disabled = busy;
  busyBar.hidden = !busy;
  for (const btn of exampleBtns) btn.disabled = busy;
  if (!seenSteps.length) drawSteps();
  else drawAgent();
  // On a phone the agent panel sits below the form: bring the action into view.
  if (busy && window.matchMedia("(max-width: 959px)").matches) {
    agentPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function closeSession() {
  currentRunId = null;
  answerBlock.hidden = true;
  answerInput.value = "";
  drawAgent();
}

function handleEvent(event) {
  if (event.type === "step") {
    seenSteps.push(event);
    drawSteps();
  } else if (event.type === "rollback") {
    // Steps of a failed attempt are re-emitted on retry: drop them here.
    const count = Math.min(event.steps || 0, seenSteps.length);
    if (count) seenSteps.splice(seenSteps.length - count, count);
    drawSteps();
  } else if (event.type === "needs_input") {
    currentRunId = event.run_id;
    questionEl.textContent = event.question || "";
    answerInput.value = "";
    answerBlock.hidden = false;
    drawAgent();
    setStatus(t("askedStatus"));
    answerBlock.scrollIntoView({ behavior: "smooth", block: "center" });
    answerInput.focus({ preventScroll: true });
  } else if (event.type === "done") {
    closeSession();
    reportView.report.scrollIntoView({ behavior: "smooth", block: "start" });
    if (event.status === "ok") {
      setStatus(t("statusDone"));
      showReport(event.report, true);
    } else if (event.status === "unverified") {
      setStatus(t("statusUnverified"), true);
      showProblems(event.problems);
    } else {
      setStatus(t("statusDoneOther", { status: event.status }));
      showReport(event.report || null, false);
    }
  } else if (event.type === "error") {
    if (currentRunId && event.run_id === currentRunId) {
      // The server kept the session and the typed answer: offer a retry.
      setStatus(`${t("errorPrefix")}${event.error || "run failed"}${t("retrySuffix")}`, true);
    } else {
      setStatus(`${t("errorPrefix")}${event.error || "run failed"}`, true);
    }
  }
}

function resetRunView() {
  closeSession();
  recordedRunState = null;
  recordedBanner.hidden = true;
  seenSteps = [];
  lastReport = null;
  lastReportVerified = false;
  lastProblems = null;
  drawSteps();
  showReport(null);
}

function restoreAnswerState(state) {
  recordedRunState = null;
  recordedBanner.hidden = true;
  currentRunId = state.runId;
  seenSteps = state.steps;
  questionEl.textContent = state.question;
  answerInput.value = state.answer;
  answerBlock.hidden = false;
  lastProblems = state.problems;
  if (state.problems) showProblems(state.problems);
  else showReport(state.report, state.reportVerified);
  drawSteps(true);
}

function restoreRecordedRetryState() {
  if (!recordedRunState?.retryState) return;
  const state = recordedRunState.retryState;
  recordedRunState = null;
  restoreAnswerState(state);
  setStatus(t("askedStatus"));
}

async function showRecordedRun(error, { retryState = null } = {}) {
  let recording;
  try {
    recording = await fetchRecordedRun();
  } catch (recordedError) {
    if (retryState) {
      restoreAnswerState(retryState);
    } else {
      closeSession();
      seenSteps = [];
      lastProblems = null;
      drawSteps();
      showReport(null);
    }
    setStatus(
      `${t("errorPrefix")}${recordedFailureReason(error)} — ` +
        t("recordedRunUnavailable", { detail: recordedFailureReason(recordedError) }),
      true
    );
    return;
  }
  resetRunView();
  recordedRunState = { error, retryState };
  recordedBanner.hidden = false;
  for (const event of recording.events) {
    if (event.type === "step") {
      seenSteps.push(event);
      drawSteps();
    }
  }
  const done = recording.events[recording.events.length - 1];
  showReport(done.report, false);
  if (retryState) {
    currentRunId = retryState.runId;
    questionEl.textContent = retryState.question;
    answerInput.value = retryState.answer;
    answerBlock.hidden = false;
  }
  setStatus(t("recordedRunStatus", { reason: recordedFailureReason(error) }), true);
}

async function startRun(body) {
  setRunBusy(true);
  resetRunView();
  setStatus(t("statusSending"));
  try {
    await streamRun(body, handleEvent);
  } catch (err) {
    if (shouldUseRecordedRun(err)) await showRecordedRun(err);
    else setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
  } finally {
    setRunBusy(false);
  }
}

async function runExample(key) {
  const example = EXAMPLES[key];
  if (!example) return;
  submittedText = "";
  setRunBusy(true);
  resetRunView();
  setStatus(t("statusLoadingExample"));
  try {
    const body = new FormData();
    body.append("image", await fetchSampleFile(example.image));
    if (example.audio) body.append("audio", await fetchSampleFile(example.audio));
    body.append("language", getLanguage());
    setStatus(t("statusSending"));
    await streamRun(body, handleEvent);
  } catch (err) {
    if (shouldUseRecordedRun(err)) await showRecordedRun(err);
    else setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
  } finally {
    setRunBusy(false);
  }
}

function applyLanguage() {
  applyTranslations();
  for (const inputId of ["photo", "voice"]) {
    const input = document.getElementById(inputId);
    const nameEl = document.getElementById(`${inputId}-name`);
    if (!input.files[0]) nameEl.textContent = t("noFile");
  }
  renderServerStatus();
  drawSteps(true);
  if (lastProblems) showProblems(lastProblems);
  else if (lastReport) showReport(lastReport, lastReportVerified);
  if (recordedRunState) {
    recordedBanner.hidden = false;
    setStatus(t("recordedRunStatus", {
      reason: recordedFailureReason(recordedRunState.error),
    }), true);
  }
}

for (const btn of langBtns) {
  btn.addEventListener("click", () => {
    setLanguage(btn.dataset.setLang);
    applyLanguage();
  });
}

for (const btn of exampleBtns) {
  btn.addEventListener("click", () => runExample(btn.dataset.example));
}

for (const inputId of ["photo", "voice"]) {
  const input = document.getElementById(inputId);
  const nameEl = document.getElementById(`${inputId}-name`);
  input.addEventListener("change", () => {
    nameEl.textContent = input.files[0] ? input.files[0].name : t("noFile");
  });
}

document.getElementById("proof-close").addEventListener("click", () => proofDialog.close());

setServerStateListener((state) => {
  serverState = state;
  renderServerStatus();
});
applyTranslations();
renderServerStatus();
drawSteps();
showReport(null);
initReveal();
preloadRecordedRun();
ensureApiBase();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const photo = document.getElementById("photo").files[0];
  const voice = document.getElementById("voice").files[0];
  const fallback = document.getElementById("fallback-text").value;
  submittedText = fallback && fallback.trim() ? fallback.trim() : "";
  const body = new FormData();
  if (photo) body.append("image", photo);
  if (voice) body.append("audio", voice);
  if (submittedText) body.append("text", submittedText);
  body.append("language", getLanguage());
  await startRun(body);
});

answerBtn.addEventListener("click", async () => {
  const answer = answerInput.value;
  if (!currentRunId || !answer.trim()) return;
  restoreRecordedRetryState();
  const retryState = {
    runId: currentRunId,
    question: questionEl.textContent,
    answer,
    steps: [...seenSteps],
    report: lastReport,
    reportVerified: lastReportVerified,
    problems: lastProblems,
  };
  setRunBusy(true);
  answerBtn.disabled = true;
  try {
    await streamAnswer(currentRunId, answer.trim(), handleEvent);
  } catch (err) {
    if (err?.status === 404) {
      restoreAnswerState(retryState);
      closeSession();
      setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
    } else if (shouldUseRecordedRun(err)) {
      await showRecordedRun(err, { retryState });
    } else {
      const retrySuffix = currentRunId ? t("retrySuffix") : "";
      setStatus(`${t("errorPrefix")}${describeClientError(err)}${retrySuffix}`, true);
    }
  } finally {
    setRunBusy(false);
    answerBtn.disabled = false;
  }
});
