const form = document.getElementById("demo-form");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const reportEl = document.getElementById("report");
const submitBtn = document.getElementById("submit-btn");
const answerBlock = document.getElementById("answer-block");
const questionEl = document.getElementById("question");
const answerInput = document.getElementById("answer-input");
const answerBtn = document.getElementById("answer-btn");

let currentRunId = null;
let seenSteps = [];

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "error" : "muted";
}

function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

function formatDetail(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? null, null, 2);
  return text.length > 2000 ? `${text.slice(0, 2000)}…` : text;
}

function renderSteps() {
  if (!seenSteps.length) {
    stepsEl.innerHTML = '<p class="muted">En attente des étapes…</p>';
    return;
  }
  const items = seenSteps
    .map(
      (s) =>
        `<li><strong>${escapeHtml(s.tool || "étape")} (pas ${escapeHtml(s.step)})</strong> — ${escapeHtml(s.decision || "")}` +
        `<details><summary>Entrée / sortie</summary>` +
        `<pre>Entrée : ${escapeHtml(formatDetail(s.args))}</pre>` +
        `<pre>Sortie : ${escapeHtml(formatDetail(s.result))}</pre></details></li>`
    )
    .join("");
  stepsEl.innerHTML = `<ol>${items}</ol>`;
}

function renderReport(report) {
  if (!report) {
    reportEl.innerHTML = '<p class="muted">Le rapport apparaîtra ici.</p>';
    return;
  }
  reportEl.innerHTML = `<pre>${escapeHtml(report)}</pre>`;
}

function closeSession() {
  currentRunId = null;
  answerBlock.hidden = true;
  answerInput.value = "";
}

function handleEvent(event) {
  if (event.type === "step") {
    seenSteps.push(event);
    renderSteps();
  } else if (event.type === "rollback") {
    // Steps of a failed attempt are re-emitted on retry: drop them here.
    const count = Math.min(event.steps || 0, seenSteps.length);
    if (count) seenSteps.splice(seenSteps.length - count, count);
    renderSteps();
  } else if (event.type === "needs_input") {
    currentRunId = event.run_id;
    questionEl.textContent = event.question || "";
    answerInput.value = "";
    answerBlock.hidden = false;
    setStatus("L’agent pose une question.");
  } else if (event.type === "done") {
    closeSession();
    if (event.status === "ok") {
      setStatus("Exécution terminée.");
      renderReport(event.report);
    } else if (event.status === "unverified") {
      setStatus("Rapport non vérifié : voir « Ce que je n’ai pas pu vérifier ».", true);
      renderReport(null);
    } else {
      setStatus(`Exécution terminée (${event.status}).`);
      renderReport(event.report || null);
    }
  } else if (event.type === "error") {
    if (currentRunId && event.run_id === currentRunId) {
      // The server kept the session and the typed answer: offer a retry.
      setStatus(`Erreur : ${event.error || "exécution impossible"} — vous pouvez réessayer.`, true);
    } else {
      setStatus(`Erreur : ${event.error || "exécution impossible"}`, true);
    }
  }
}

async function streamEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminalSeen = false;
  let parseErrors = 0;
  const dispatch = (line) => {
    if (!line.startsWith("data:")) return;
    try {
      const event = JSON.parse(line.slice(5).trim());
      if (event.type === "done" || event.type === "needs_input" || event.type === "error") {
        terminalSeen = true;
      }
      onEvent(event);
    } catch {
      parseErrors += 1;
    }
  };
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let cut;
    while ((cut = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      for (const line of block.split("\n")) dispatch(line);
    }
  }
  const tail = buffer.trim();
  if (tail) dispatch(tail);
  return { terminalSeen, parseErrors };
}

async function readErrorDetail(response) {
  const text = await response.text();
  try {
    return JSON.parse(text).detail || text;
  } catch {
    return text;
  }
}

async function postRun(body) {
  const response = await fetch("/run", { method: "POST", body });
  if (!response.ok) throw new Error(await readErrorDetail(response));
  const result = await streamEvents(response, handleEvent);
  if (!result.terminalSeen) {
    throw new Error("Connexion interrompue : aucun événement final reçu. Relancez l’exécution.");
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  closeSession();
  seenSteps = [];
  renderSteps();
  renderReport(null);
  setStatus("Envoi au serveur…");

  const photo = document.getElementById("photo").files[0];
  const voice = document.getElementById("voice").files[0];
  const fallback = document.getElementById("fallback-text").value;
  const body = new FormData();
  if (photo) body.append("image", photo);
  if (voice) body.append("audio", voice);
  if (fallback && fallback.trim()) body.append("text", fallback.trim());

  try {
    await postRun(body);
  } catch (err) {
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});

answerBtn.addEventListener("click", async () => {
  const answer = answerInput.value;
  if (!currentRunId || !answer.trim()) return;
  answerBtn.disabled = true;
  const stepsBeforeAnswer = seenSteps.length;
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: currentRunId, answer: answer.trim() }),
    });
    if (!response.ok) {
      const detail = await readErrorDetail(response);
      if (response.status === 404) closeSession();
      throw new Error(detail);
    }
    // The typed answer is cleared only on a terminal event (needs_input
    // clears it for the next question, done via closeSession): on error it
    // stays in place so the student can retry as the message promises.
    const result = await streamEvents(response, handleEvent);
    if (!result.terminalSeen) {
      seenSteps = seenSteps.slice(0, stepsBeforeAnswer);
      renderSteps();
      setStatus("Connexion interrompue : la réponse n’a pas abouti. Vous pouvez réessayer.", true);
    }
  } catch (err) {
    seenSteps = seenSteps.slice(0, stepsBeforeAnswer);
    renderSteps();
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    answerBtn.disabled = false;
  }
});
