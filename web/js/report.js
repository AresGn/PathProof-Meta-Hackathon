// Report view: verified text, claim cards with proof buttons, refusals.
// Rendering only; claim extraction lives in proofs.js, streaming in api.js.
import { t } from "./i18n.js";
import { proofLabel } from "./proofs.js";

export function renderClaims(view, claims, openProof) {
  view.claims.innerHTML = "";
  view.proofs.hidden = !claims.length;
  for (const claim of claims) {
    const card = document.createElement("article");
    card.className = "claim";
    const text = document.createElement("p");
    text.textContent = claim.text || "";
    card.appendChild(text);
    for (const proof of claim.proofs || []) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = `proof-chip chip-${proof.type}`;
      chip.textContent = proofLabel(proof);
      chip.addEventListener("click", () => openProof(proof));
      card.appendChild(chip);
    }
    view.claims.appendChild(card);
  }
}

export function renderReport(view, report, claims, openProof) {
  view.report.innerHTML = "";
  if (!report) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = t("reportEmpty");
    view.report.appendChild(empty);
    view.proofs.hidden = true;
    view.banner.hidden = true;
    view.claims.innerHTML = "";
    return;
  }
  view.banner.hidden = false;
  const pre = document.createElement("pre");
  pre.textContent = report;
  view.report.appendChild(pre);
  renderClaims(view, claims, openProof);
}

export function renderProblems(view, problems) {
  view.banner.hidden = true;
  view.report.innerHTML = "";
  const intro = document.createElement("p");
  intro.textContent = t("problemsIntro");
  view.report.appendChild(intro);
  const list = document.createElement("ul");
  for (const problem of problems || []) {
    const item = document.createElement("li");
    item.textContent = `${problem.claim_id || "report"} — ${problem.type || "proof"}`;
    list.appendChild(item);
  }
  view.report.appendChild(list);
  view.proofs.hidden = true;
  view.claims.innerHTML = "";
}
