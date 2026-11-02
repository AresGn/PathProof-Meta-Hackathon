// Clickable proofs: claims of the accepted draft, sources from the trace.
// A proof button opens its source (sheet grade, transcript quote, guide row,
// calculation detail) in the dialog. All values are written as text nodes.
import { t } from "./i18n.js";
import { formatNumber } from "./format.js";
import { lastStep } from "./steps.js";

// The verified claims are the draft the streamed verify_report accepted
// (empty problem list); build_report only formats that same draft.
export function verifiedClaims(steps) {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    const step = steps[i];
    if (step.tool !== "verify_report") continue;
    if (!Array.isArray(step.result) || step.result.length !== 0) continue;
    const claims = step.args && step.args.report && step.args.report.claims;
    if (Array.isArray(claims)) return claims;
  }
  const build = lastStep(steps, "build_report");
  const claims = build && build.args && build.args.report && build.args.report.claims;
  return Array.isArray(claims) ? claims : [];
}

function gradeSheetResult(steps) {
  const step = lastStep(steps, "read_grade_sheet");
  return step && step.result && Array.isArray(step.result.matieres) ? step.result : null;
}

function transcriptSourceText(steps, submittedText) {
  const step = lastStep(steps, "transcribe_voice");
  if (step && step.result && typeof step.result.text === "string") return step.result.text;
  return submittedText;
}

function offerSource(steps, offreId) {
  const step = lastStep(steps, "lookup_filieres");
  if (!step || !step.result) return null;
  for (const key of ["accessible", "excluded"]) {
    const rows = step.result[key];
    if (!Array.isArray(rows)) continue;
    const found = rows.find((row) => row && row.Offre_ID === offreId);
    if (found) return found;
  }
  return null;
}

export function proofLabel(proof) {
  if (proof.type === "grade") return t("proofGrade", { matiere: proof.matiere, note: formatNumber(proof.note) });
  if (proof.type === "transcript") return t("proofTranscript", { quote: proof.quote });
  if (proof.type === "filiere") return t("proofFiliere", { id: proof.offre_id, page: proof.page_pdf });
  if (proof.type === "calc") return t("proofCalc", { result: formatNumber(proof.result) });
  return t("proofOther", { type: proof.type });
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

// The viewer reads the live trace through getters, so a source always
// reflects the steps currently on screen (retries and rollbacks included).
export function createProofViewer({ dialog, title, body, getSteps, getSubmittedText }) {
  function showGradeProof(proof) {
    title.textContent = t("gradeTitle", { matiere: proof.matiere, note: formatNumber(proof.note) });
    addNote(body, t("gradeNote"));
    const sheet = gradeSheetResult(getSteps());
    if (!sheet) {
      addNote(body, t("sheetUnavailable"));
      return;
    }
    const wanted = String(proof.matiere || "").toLocaleLowerCase("fr");
    const lines = sheet.matieres.filter(
      (line) => String(line.matiere || "").toLocaleLowerCase("fr") === wanted
    );
    const shown = lines.length ? lines : sheet.matieres;
    addTable(
      body,
      shown.map((line) => [
        line.matiere,
        `${formatNumber(line.note)}/20${line.lisible === false ? ` (${t("unreadable")})` : ""}`,
      ])
    );
    if (sheet.serie) addNote(body, t("serieRead", { serie: sheet.serie }));
    if (sheet.moyenne_affichee !== null && sheet.moyenne_affichee !== undefined) {
      addNote(body, t("displayedAverage", { avg: formatNumber(sheet.moyenne_affichee) }));
    }
  }

  function showTranscriptProof(proof) {
    title.textContent = t("transcriptTitle");
    addNote(body, t("transcriptNote"));
    const text = transcriptSourceText(getSteps(), getSubmittedText());
    const paragraph = document.createElement("p");
    const index = text ? text.indexOf(proof.quote) : -1;
    if (index >= 0) {
      paragraph.append(document.createTextNode(text.slice(0, index)));
      const mark = document.createElement("mark");
      mark.textContent = proof.quote;
      paragraph.append(mark, document.createTextNode(text.slice(index + proof.quote.length)));
    } else {
      paragraph.textContent = `« ${proof.quote} »`;
      if (!text) addNote(body, t("transcriptUnavailable"));
    }
    body.appendChild(paragraph);
  }

  function showFiliereProof(proof) {
    title.textContent = t("filiereTitle", { id: proof.offre_id, page: proof.page_pdf });
    addNote(body, t("filiereNote"));
    const rows = [
      ["Offre_ID", proof.offre_id],
      [t("fieldPage"), proof.page_pdf],
      [t("fieldChamp"), proof.champ],
      [t("fieldValeur"), proof.valeur],
    ];
    const offer = offerSource(getSteps(), proof.offre_id);
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
    addTable(body, rows);
  }

  function showCalcProof(proof) {
    title.textContent = t("calcTitle", { result: formatNumber(proof.result) });
    addNote(body, t("calcNote", { formula: proof.formula }));
    const inputs = Array.isArray(proof.inputs) ? proof.inputs : [];
    const table = document.createElement("table");
    const head = document.createElement("tr");
    for (const label of [t("calcSubject"), t("calcGrade"), t("calcCoefficient"), t("calcProduct")]) {
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
    body.appendChild(table);
    addNote(body, t("calcDetail", {
      total: formatNumber(total), coeffs: coefficients, result: formatNumber(proof.result),
    }));
  }

  function openProof(proof) {
    body.innerHTML = "";
    if (proof.type === "grade") showGradeProof(proof);
    else if (proof.type === "transcript") showTranscriptProof(proof);
    else if (proof.type === "filiere") showFiliereProof(proof);
    else if (proof.type === "calc") showCalcProof(proof);
    else {
      title.textContent = t("proofOther", { type: proof.type });
      addNote(body, JSON.stringify(proof));
    }
    if (typeof dialog.showModal === "function") dialog.showModal();
  }

  return { openProof };
}
