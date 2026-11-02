// Demo orchestration: wires the form, examples, answer flow and language
// switch to the API stream and the views. No rendering or HTTP code here:
// see steps.js, proofs.js, report.js, api.js, i18n.js and format.js.
import { applyTranslations, setLanguage, t } from "./i18n.js";
import {
  describeClientError, ensureApiBase, fetchSampleFile,
  setServerStateListener, streamAnswer, streamRun,
} from "./api.js";
import { renderSteps } from "./steps.js";
import { createProofViewer, verifiedClaims } from "./proofs.js";
import { renderProblems, renderReport } from "./report.js";

const form = document.getElementById("demo-form");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const submitBtn = document.getElementById("submit-btn");
const busyBar = document.getElementById("busy-bar");
const serverStatusEl = document.getElementById("server-status");
const answerBlock = document.getElementById("answer-block");
const questionEl = document.getElementById("question");
const answerInput = document.getElementById("answer-input");
const answerBtn = document.getElementById("answer-btn");
const proofDialog = document.getElementById("proof-dialog");
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
let lastProblems = null;

const proofViewer = createProofViewer({
  dialog: proofDialog,
  title: document.getElementById("proof-title"),
  body: document.getElementById("proof-body"),
  getSteps: () => seenSteps,
  getSubmittedText: () => submittedText,
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

function drawSteps() {
  renderSteps(stepsEl, seenSteps, runBusy);
}

function showReport(report) {
  lastReport = report;
  renderReport(reportView, report, verifiedClaims(seenSteps), proofViewer.openProof);
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
}

function closeSession() {
  currentRunId = null;
  answerBlock.hidden = true;
  answerInput.value = "";
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
    setStatus(t("askedStatus"));
    answerBlock.scrollIntoView({ behavior: "smooth", block: "center" });
    answerInput.focus({ preventScroll: true });
  } else if (event.type === "done") {
    closeSession();
    reportView.report.scrollIntoView({ behavior: "smooth", block: "start" });
    if (event.status === "ok") {
      setStatus(t("statusDone"));
      showReport(event.report);
    } else if (event.status === "unverified") {
      setStatus(t("statusUnverified"), true);
      showProblems(event.problems);
    } else {
      setStatus(t("statusDoneOther", { status: event.status }));
      showReport(event.report || null);
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
  seenSteps = [];
  lastReport = null;
  lastProblems = null;
  drawSteps();
  showReport(null);
}

async function startRun(body) {
  setRunBusy(true);
  resetRunView();
  setStatus(t("statusSending"));
  try {
    await streamRun(body, handleEvent);
  } catch (err) {
    setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
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
    setStatus(t("statusSending"));
    await streamRun(body, handleEvent);
  } catch (err) {
    setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
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
  drawSteps();
  if (lastProblems) showProblems(lastProblems);
  else if (lastReport) showReport(lastReport);
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
  await startRun(body);
});

answerBtn.addEventListener("click", async () => {
  const answer = answerInput.value;
  if (!currentRunId || !answer.trim()) return;
  answerBtn.disabled = true;
  const stepsBeforeAnswer = seenSteps.length;
  try {
    const result = await streamAnswer(currentRunId, answer.trim(), handleEvent);
    if (!result.terminalSeen) {
      seenSteps = seenSteps.slice(0, stepsBeforeAnswer);
      drawSteps();
      setStatus(t("answerInterrupted"), true);
    }
  } catch (err) {
    seenSteps = seenSteps.slice(0, stepsBeforeAnswer);
    drawSteps();
    if (err && err.status === 404) closeSession();
    setStatus(`${t("errorPrefix")}${describeClientError(err)}`, true);
  } finally {
    answerBtn.disabled = false;
  }
});
