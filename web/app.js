const form = document.getElementById("demo-form");
const statusEl = document.getElementById("status");
const stepsEl = document.getElementById("steps");
const reportEl = document.getElementById("report");
const proofsEl = document.getElementById("proofs");
const claimsEl = document.getElementById("claims");
const submitBtn = document.getElementById("submit-btn");
const answerBlock = document.getElementById("answer-block");
const questionEl = document.getElementById("question");
const answerInput = document.getElementById("answer-input");
const answerBtn = document.getElementById("answer-btn");
const proofDialog = document.getElementById("proof-dialog");
const proofTitle = document.getElementById("proof-title");
const proofBody = document.getElementById("proof-body");
const proofClose = document.getElementById("proof-close");
const exampleBtns = [...document.querySelectorAll("[data-example]")];

// One-click fictional examples (data/samples/README.md): nothing to prepare.
const EXAMPLES = {
  coherent: { image: "releve_serie_d.jpg", audio: "note_vocale_coherente.mp3" },
  blurry: { image: "releve_serie_d_flou.jpg", audio: null },
  contradictory: { image: "releve_serie_d.jpg", audio: "note_vocale_contradictoire.mp3" },
};

let currentRunId = null;
let seenSteps = [];
let submittedText = "";

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

function formatNumber(value) {
  return String(value ?? "").replace(".", ",");
}

function setRunBusy(busy) {
  submitBtn.disabled = busy;
  for (const btn of exampleBtns) btn.disabled = busy;
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

function lastStep(tool) {
  for (let i = seenSteps.length - 1; i >= 0; i -= 1) {
    if (seenSteps[i].tool === tool) return seenSteps[i];
  }
  return null;
}

// The verified claims are the draft the streamed verify_report accepted
// (empty problem list); build_report only formats that same draft.
function verifiedClaims() {
  for (let i = seenSteps.length - 1; i >= 0; i -= 1) {
    const step = seenSteps[i];
    if (step.tool !== "verify_report") continue;
    if (!Array.isArray(step.result) || step.result.length !== 0) continue;
    const claims = step.args && step.args.report && step.args.report.claims;
    if (Array.isArray(claims)) return claims;
  }
  const build = lastStep("build_report");
  const claims = build && build.args && build.args.report && build.args.report.claims;
  return Array.isArray(claims) ? claims : [];
}

function gradeSheetResult() {
  const step = lastStep("read_grade_sheet");
  return step && step.result && Array.isArray(step.result.matieres) ? step.result : null;
}

function transcriptSourceText() {
  const step = lastStep("transcribe_voice");
  if (step && step.result && typeof step.result.text === "string") return step.result.text;
  return submittedText;
}

function offerSource(offreId) {
  const step = lastStep("lookup_filieres");
  if (!step || !step.result) return null;
  for (const key of ["accessible", "excluded"]) {
    const rows = step.result[key];
    if (!Array.isArray(rows)) continue;
    const found = rows.find((row) => row && row.Offre_ID === offreId);
    if (found) return found;
  }
  return null;
}

function proofLabel(proof) {
  if (proof.type === "grade") return `Note · ${proof.matiere} ${formatNumber(proof.note)}/20`;
  if (proof.type === "transcript") return `Citation · « ${proof.quote} »`;
  if (proof.type === "filiere") return `Guide · ${proof.offre_id} (page ${proof.page_pdf})`;
  if (proof.type === "calc") return `Calcul · ${formatNumber(proof.result)}`;
  return `Preuve · ${proof.type}`;
}

function addRow(table, label, value) {
  const row = document.createElement("tr");
  const head = document.createElement("th");
  head.textContent = label;
  const cell = document.createElement("td");
  cell.textContent = value === null || value === undefined ? "" : String(value);
  row.append(head, cell);
  table.appendChild(row);
}

function addTable(parent, rows) {
  const table = document.createElement("table");
  for (const [label, value] of rows) addRow(table, label, value);
  parent.appendChild(table);
  return table;
}

function addNote(parent, text) {
  const note = document.createElement("p");
  note.textContent = text;
  parent.appendChild(note);
  return note;
}

function showGradeProof(proof) {
  proofTitle.textContent = `Preuve note — ${proof.matiere} : ${formatNumber(proof.note)}/20`;
  addNote(proofBody, "Note lue sur la photo du relevé (outil read_grade_sheet).");
  const sheet = gradeSheetResult();
  if (!sheet) {
    addNote(proofBody, "Le détail du relevé n’est plus dans la trace affichée.");
    return;
  }
  const wanted = String(proof.matiere || "").toLocaleLowerCase("fr");
  const lines = sheet.matieres.filter(
    (line) => String(line.matiere || "").toLocaleLowerCase("fr") === wanted
  );
  const shown = lines.length ? lines : sheet.matieres;
  addTable(
    proofBody,
    shown.map((line) => [
      line.matiere,
      `${formatNumber(line.note)}/20${line.lisible === false ? " (illisible)" : ""}`,
    ])
  );
  if (sheet.serie) addNote(proofBody, `Série lue : ${sheet.serie}.`);
  if (sheet.moyenne_affichee !== null && sheet.moyenne_affichee !== undefined) {
    addNote(proofBody, `Moyenne affichée sur le relevé : ${formatNumber(sheet.moyenne_affichee)}/20.`);
  }
}

function showTranscriptProof(proof) {
  proofTitle.textContent = "Preuve citation — note vocale";
  addNote(proofBody, "Citation exacte cherchée mot pour mot dans la transcription.");
  const text = transcriptSourceText();
  const paragraph = document.createElement("p");
  const index = text ? text.indexOf(proof.quote) : -1;
  if (index >= 0) {
    paragraph.append(document.createTextNode(text.slice(0, index)));
    const mark = document.createElement("mark");
    mark.textContent = proof.quote;
    paragraph.append(mark, document.createTextNode(text.slice(index + proof.quote.length)));
  } else {
    paragraph.textContent = `« ${proof.quote} »`;
    if (!text) addNote(proofBody, "Transcription indisponible dans la trace affichée.");
  }
  proofBody.appendChild(paragraph);
}

function showFiliereProof(proof) {
  proofTitle.textContent = `Preuve guide — ${proof.offre_id}, page ${proof.page_pdf}`;
  addNote(
    proofBody,
    "Ligne du Guide d’information 2026-2027 officiel. Seules les lignes Statut_qualité = OK sont recommandées."
  );
  const rows = [
    ["Offre_ID", proof.offre_id],
    ["Page du guide (PDF)", proof.page_pdf],
    ["Champ prouvé", proof.champ],
    ["Valeur prouvée", proof.valeur],
  ];
  const offer = offerSource(proof.offre_id);
  if (offer) {
    rows.push(
      ["Filière", offer["Filière"]],
      ["Établissement", offer["Établissement"]],
      ["Bac_recommandé", offer["Bac_recommandé"]],
      ["Mode_entrée", offer["Mode_entrée"]],
      ["Bourse", offer["Bourse"]],
      ["Aide_FPP", offer["Aide_FPP"]],
      ["Débouchés_Métiers", offer["Débouchés_Métiers"]],
      ["Statut_qualité", offer["Statut_qualité"]]
    );
  }
  addTable(proofBody, rows);
}

function showCalcProof(proof) {
  proofTitle.textContent = `Preuve calcul — ${formatNumber(proof.result)}/20`;
  addNote(proofBody, `Formule du guide (page 8) : ${proof.formula}. Coefficients de la série, jamais calculés par le modèle.`);
  const inputs = Array.isArray(proof.inputs) ? proof.inputs : [];
  const table = document.createElement("table");
  const head = document.createElement("tr");
  for (const label of ["Matière", "Note", "Coefficient", "Note × coefficient"]) {
    const cell = document.createElement("th");
    cell.textContent = label;
    head.appendChild(cell);
  }
  table.appendChild(head);
  let total = 0;
  let coefficients = 0;
  for (const entry of inputs) {
    const product = Number(entry.note) * Number(entry.coefficient);
    total += product;
    coefficients += Number(entry.coefficient);
    const row = document.createElement("tr");
    for (const value of [entry.matiere, formatNumber(entry.note), entry.coefficient, formatNumber(product)]) {
      const cell = document.createElement("td");
      cell.textContent = String(value ?? "");
      row.appendChild(cell);
    }
    table.appendChild(row);
  }
  proofBody.appendChild(table);
  addNote(
    proofBody,
    `Détail : ${formatNumber(total)} / ${coefficients} = ${formatNumber(proof.result)}/20 (arrondi du guide).`
  );
}

function openProof(proof) {
  proofBody.innerHTML = "";
  if (proof.type === "grade") showGradeProof(proof);
  else if (proof.type === "transcript") showTranscriptProof(proof);
  else if (proof.type === "filiere") showFiliereProof(proof);
  else if (proof.type === "calc") showCalcProof(proof);
  else {
    proofTitle.textContent = "Preuve";
    addNote(proofBody, JSON.stringify(proof));
  }
  if (typeof proofDialog.showModal === "function") proofDialog.showModal();
}

function renderClaims() {
  claimsEl.innerHTML = "";
  const claims = verifiedClaims();
  proofsEl.hidden = !claims.length;
  for (const claim of claims) {
    const card = document.createElement("article");
    card.className = "claim";
    const text = document.createElement("p");
    text.textContent = claim.text || "";
    card.appendChild(text);
    for (const proof of claim.proofs || []) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "proof-chip";
      chip.textContent = proofLabel(proof);
      chip.addEventListener("click", () => openProof(proof));
      card.appendChild(chip);
    }
    claimsEl.appendChild(card);
  }
}

function renderReport(report) {
  reportEl.innerHTML = "";
  if (!report) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "Le rapport apparaîtra ici.";
    reportEl.appendChild(empty);
    proofsEl.hidden = true;
    claimsEl.innerHTML = "";
    return;
  }
  const pre = document.createElement("pre");
  pre.textContent = report;
  reportEl.appendChild(pre);
  renderClaims();
}

function renderProblems(problems) {
  reportEl.innerHTML = "";
  const intro = document.createElement("p");
  intro.textContent = "Affirmations refusées par le vérificateur (jamais présentées comme des faits) :";
  reportEl.appendChild(intro);
  const list = document.createElement("ul");
  for (const problem of problems || []) {
    const item = document.createElement("li");
    item.textContent = `${problem.claim_id || "rapport"} — ${problem.type || "preuve"}`;
    list.appendChild(item);
  }
  reportEl.appendChild(list);
  proofsEl.hidden = true;
  claimsEl.innerHTML = "";
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
      renderProblems(event.problems);
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

function resetRunView() {
  closeSession();
  seenSteps = [];
  renderSteps();
  renderReport(null);
}

async function startRun(body) {
  setRunBusy(true);
  resetRunView();
  setStatus("Envoi au serveur…");
  try {
    await postRun(body);
  } catch (err) {
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    setRunBusy(false);
  }
}

async function fetchSampleFile(name) {
  const response = await fetch(`/samples/${name}`);
  if (!response.ok) throw new Error(`exemple illisible (${name})`);
  const blob = await response.blob();
  return new File([blob], name, { type: blob.type || "application/octet-stream" });
}

async function runExample(key) {
  const example = EXAMPLES[key];
  if (!example) return;
  submittedText = "";
  setRunBusy(true);
  resetRunView();
  setStatus("Chargement de l’exemple fictif…");
  try {
    const body = new FormData();
    body.append("image", await fetchSampleFile(example.image));
    if (example.audio) body.append("audio", await fetchSampleFile(example.audio));
    setStatus("Envoi au serveur…");
    await postRun(body);
  } catch (err) {
    setStatus(`Erreur : ${err.message}`, true);
  } finally {
    setRunBusy(false);
  }
}

for (const btn of exampleBtns) {
  btn.addEventListener("click", () => runExample(btn.dataset.example));
}

proofClose.addEventListener("click", () => proofDialog.close());

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
