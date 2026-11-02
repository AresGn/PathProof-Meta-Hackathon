// Live trace view: one timeline card per streamed tool step.
import { t } from "./i18n.js";
import { escapeHtml, formatDetail } from "./format.js";

const TOOL_ICONS = {
  transcribe_voice: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 19v3"/>',
  extract_profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 5-5.5 8-5.5s6.5 1.5 8 5.5"/>',
  read_grade_sheet: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  compute_ranking_average: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/>',
  lookup_filieres: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  ask_student: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  verify_report: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  build_report: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/>',
};

function toolIcon(tool) {
  const paths = TOOL_ICONS[tool] || '<circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/>';
  return `<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">${paths}</svg>`;
}

export function lastStep(steps, tool) {
  for (let i = steps.length - 1; i >= 0; i -= 1) {
    if (steps[i].tool === tool) return steps[i];
  }
  return null;
}

export function renderSteps(container, steps, busy) {
  if (!steps.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = busy ? t("stepsWaiting") : t("stepsEmpty");
    container.innerHTML = "";
    container.appendChild(empty);
    return;
  }
  const items = steps
    .map((s) => {
      const label = t(`tool_${s.tool}`) !== `tool_${s.tool}` ? t(`tool_${s.tool}`) : t("tool_other");
      const decisionKey = `decision_${s.decision}`;
      const decision = t(decisionKey) !== decisionKey ? t(decisionKey) : s.decision || "";
      return (
        `<article class="step-card"><span class="step-ico">${toolIcon(s.tool)}</span>` +
        `<div class="step-head"><strong>${escapeHtml(label)}</strong>` +
        `<span class="step-num">${escapeHtml(t("stepWord"))} ${escapeHtml(s.step)} · ${escapeHtml(s.tool || "")}</span>` +
        `<span class="pill decision-${escapeHtml(s.decision || "continue")}">${escapeHtml(decision)}</span></div>` +
        `<details><summary>${escapeHtml(t("inputOutput"))}</summary>` +
        `<pre>${escapeHtml(t("input"))} : ${escapeHtml(formatDetail(s.args))}</pre>` +
        `<pre>${escapeHtml(t("output"))} : ${escapeHtml(formatDetail(s.result))}</pre></details></article>`
      );
    })
    .join("");
  container.innerHTML = `<div class="timeline">${items}</div>`;
}
