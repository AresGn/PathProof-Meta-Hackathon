// Live trace view: one timeline card per streamed tool step.
import { t } from "./i18n.js";
import { escapeHtml, formatDetail } from "./format.js";
import { deciderOf, runnerOf } from "./models.js";

export const TOOL_ICONS = {
  transcribe_voice: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 19v3"/>',
  extract_profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 5-5.5 8-5.5s6.5 1.5 8 5.5"/>',
  read_grade_sheet: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>',
  compute_ranking_average: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8"/><path d="M8 11h.01M12 11h.01M16 11h.01M8 15h.01M12 15h.01M16 15h.01"/>',
  lookup_filieres: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
  ask_student: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
  verify_report: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  build_report: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/>',
};

// Who does the work: the model reads and decides, code computes and verifies
// (docs/prd.md: the model never calculates), the student answers questions.
export const TOOL_KINDS = {
  transcribe_voice: "model", extract_profile: "model", read_grade_sheet: "model",
  compute_ranking_average: "code", lookup_filieres: "code", verify_report: "code",
  build_report: "code", ask_student: "human",
};

const QUOTE_PREVIEW_LENGTH = 90;

export function toolKind(tool) {
  return TOOL_KINDS[tool] || "code";
}

// One readable line per call, derived only from the streamed result.
function summarizeResult(step) {
  const result = step.result;
  if (step.tool === "verify_report" && Array.isArray(result)) {
    return result.length
      ? { text: t("resultVerifyRejected", { n: result.length }), tone: "bad" }
      : { text: t("resultVerifyOk"), tone: "good" };
  }
  if (step.tool === "lookup_filieres" && Array.isArray(result?.accessible)) {
    return { text: t("resultOffers", { n: result.accessible.length }), tone: "neutral" };
  }
  if (step.tool === "read_grade_sheet" && Array.isArray(result?.matieres)) {
    return { text: t("resultSheet", { serie: result.serie ?? "?", n: result.matieres.length }), tone: "neutral" };
  }
  if (step.tool === "transcribe_voice" && typeof result?.text === "string") {
    const quote = result.text.trim().slice(0, QUOTE_PREVIEW_LENGTH);
    return { text: t("resultQuote", { text: quote }), tone: "neutral" };
  }
  return null;
}

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

function modelChip(label, model, tone) {
  const id = model ? `<code class="model-id">${escapeHtml(model.id)}</code>` : "";
  const effort = model?.effort
    ? `<span class="model-effort">${escapeHtml(t("modelEffort", { effort: model.effort }))}</span>`
    : "";
  return `<span class="model-chip model-${tone}">${escapeHtml(label)}${id}${effort}</span>`;
}

// Who decided and who ran this step: the deciding model is the one the loop
// really called for this turn (journal); the tool then runs on its own model,
// or on plain code when it has none.
function modelLine(step) {
  const decider = deciderOf(step);
  const runner = runnerOf(step.tool);
  const decides = decider
    ? modelChip(t("modelDecides", { model: decider.name }), decider, decider.tone)
    : "";
  const runs = runner
    ? modelChip(t("modelRuns", { model: runner.name }), runner, runner.tone)
    : modelChip(t("modelRunsCode"), null, "code");
  return `<p class="model-line">${decides}${runs}</p>`;
}

function renderStep(step) {
  const label = t(`tool_${step.tool}`) !== `tool_${step.tool}` ? t(`tool_${step.tool}`) : t("tool_other");
  const decisionKey = `decision_${step.decision}`;
  const decision = t(decisionKey) !== decisionKey ? t(decisionKey) : step.decision || "";
  const kind = toolKind(step.tool);
  const summary = summarizeResult(step);
  const summaryHtml = summary
    ? `<p class="step-summary tone-${summary.tone}">${escapeHtml(summary.text)}</p>`
    : "";
  const template = document.createElement("template");
  template.innerHTML =
    `<article class="step-card kind-${kind}"><span class="step-ico">${toolIcon(step.tool)}</span>` +
    `<div class="step-head"><strong>${escapeHtml(label)}</strong>` +
    `<span class="kind-tag kind-tag-${kind}">${escapeHtml(t(`kind${kind[0].toUpperCase()}${kind.slice(1)}`))}</span>` +
    `<span class="step-num">${escapeHtml(t("stepWord"))} ${escapeHtml(step.step)} · ${escapeHtml(step.tool || "")}</span>` +
    `<span class="pill decision-${escapeHtml(step.decision || "continue")}">${escapeHtml(decision)}</span></div>` +
    modelLine(step) +
    summaryHtml +
    `<details><summary>${escapeHtml(t("inputOutput"))}</summary>` +
    `<pre>${escapeHtml(t("input"))} : ${escapeHtml(formatDetail(step.args))}</pre>` +
    `<pre>${escapeHtml(t("output"))} : ${escapeHtml(formatDetail(step.result))}</pre></details></article>`;
  const card = template.content.firstElementChild;
  card.sourceStep = step;
  return card;
}

export function renderSteps(container, steps, busy, force = false) {
  if (!steps.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = busy ? t("stepsWaiting") : t("stepsEmpty");
    container.textContent = "";
    container.appendChild(empty);
    return;
  }
  let timeline = container.querySelector(".timeline");
  if (!timeline) {
    container.textContent = "";
    timeline = document.createElement("div");
    timeline.className = "timeline";
    container.appendChild(timeline);
  }
  let sharedCount = 0;
  while (
    !force &&
    sharedCount < steps.length &&
    sharedCount < timeline.children.length &&
    timeline.children[sharedCount].sourceStep === steps[sharedCount]
  ) {
    sharedCount += 1;
  }
  while (timeline.children.length > sharedCount) {
    timeline.removeChild(timeline.lastElementChild);
  }
  for (let index = sharedCount; index < steps.length; index += 1) {
    timeline.appendChild(renderStep(steps[index]));
  }
}
