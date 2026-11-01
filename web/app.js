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

function parseSse(text) {
  const events = [];
  for (const block of String(text).split("\n\n")) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    for (const line of trimmed.split("\n")) {
      if (line.startsWith("data:")) {
        try {
          events.push(JSON.parse(line.slice(5).trim()));
        } catch {
          // Ignore a malformed frame; the error event carries real failures.
        }
      }
    }
  }
  return events;
}

function renderSteps() {
  if (!seenSteps.length) {
    stepsEl.innerHTML = '<p class="muted">En attente des étapes…</p>';
    return;
  }
  const items = seenSteps
    .map(
      (s) =>
        `<li><strong>${escapeHtml(s.tool || "étape")} (pas ${escapeHtml(s.step)})</strong> — ${escapeHtml(s.decision || "")}</li>`
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

function handleEvents(events) {
  for (const event of events) {
    if (event.type === "step") {
      seenSteps.push(event);
      renderSteps();
    } else if (event.type === "needs_input") {
      currentRunId = event.run_id;
      questionEl.textContent = event.question || "";
      answerBlock.hidden = false;
      setStatus("L’agent pose une question.");
    } else if (event.type === "done") {
      currentRunId = null;
      answerBlock.hidden = true;
      if (event.status === "ok") {
        setStatus("Exécution terminée.");
        renderReport(event.report);
      } else if (event.status === "unverified") {
        setStatus("Rapport non vérifié : voir les problèmes.", true);
        renderReport(null);
      } else {
        setStatus(`Exécution terminée (${event.status}).`);
        renderReport(event.report || null);
      }
    } else if (event.type === "error") {
      setStatus(`Erreur : ${event.error || "exécution impossible"}`, true);
    }
  }
}

async function postRun(body) {
  const response = await fetch("/run", { method: "POST", body });
  const text = await response.text();
  if (!response.ok) {
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch {
      // Keep the raw body when it is not JSON (413/415 pages).
    }
    throw new Error(detail);
  }
  handleEvents(parseSse(text));
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  answerBlock.hidden = true;
  currentRunId = null;
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
  try {
    const response = await fetch("/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_id: currentRunId, answer: answer.trim() }),
    });
    const text = await response.text();
    if (!response.ok) throw new Error(text);
    answerInput.value = "";
    handleEvents(parseSse(text));
  } catch (err) {
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    answerBtn.disabled = false;
  }
});
