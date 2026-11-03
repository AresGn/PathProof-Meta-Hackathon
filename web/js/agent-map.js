// Live agent map: the agent at the centre, one node per tool around it.
// A node lights up when its tool answers; the core pulses while the agent
// chooses the next tool. Steps are streamed after execution, so the map never
// claims a tool is "running": it shows who answered and what comes next.
import { t } from "./i18n.js";
import { TOOL_ICONS, toolKind } from "./steps.js";

const TOOL_ORDER = [
  "transcribe_voice", "read_grade_sheet", "extract_profile", "ask_student",
  "compute_ranking_average", "lookup_filieres", "verify_report", "build_report",
];
const MAP_SIZE = 360;  // SVG viewBox side, in user units
const MAP_RADIUS = 138;  // distance from the core to each tool node
const NODE_RADIUS = 27;
const ICON_SCALE = 0.95;  // 24-unit icons drawn at about 23 units
const CORE_RADIUS = 40;

function nodePosition(index) {
  const angle = (index / TOOL_ORDER.length) * 2 * Math.PI - Math.PI / 2;
  const centre = MAP_SIZE / 2;
  return {
    x: centre + MAP_RADIUS * Math.cos(angle),
    y: centre + MAP_RADIUS * Math.sin(angle),
  };
}

function buildSvg() {
  const centre = MAP_SIZE / 2;
  const links = [];
  const nodes = [];
  TOOL_ORDER.forEach((tool, index) => {
    const { x, y } = nodePosition(index);
    links.push(`<line class="map-link" data-tool="${tool}" x1="${centre}" y1="${centre}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}"/>`);
    const offset = (-12 * ICON_SCALE).toFixed(1);
    nodes.push(
      `<g class="map-node kind-${toolKind(tool)}" data-tool="${tool}" style="--i:${index}" transform="translate(${x.toFixed(1)} ${y.toFixed(1)})">` +
        `<circle class="map-node-halo" r="${NODE_RADIUS + 7}"/>` +
        `<circle class="map-node-ring" r="${NODE_RADIUS}"/>` +
        `<g class="map-node-icon" transform="translate(${offset} ${offset}) scale(${ICON_SCALE})" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${TOOL_ICONS[tool]}</g>` +
        `<text class="map-node-label" y="${NODE_RADIUS + 15}" text-anchor="middle" data-short="${tool}"></text>` +
        `<g class="map-node-count" transform="translate(${NODE_RADIUS - 4} ${-NODE_RADIUS + 4})"><circle r="9"/><text text-anchor="middle" y="3.5"></text></g>` +
      `</g>`
    );
  });
  return (
    `<svg viewBox="0 0 ${MAP_SIZE} ${MAP_SIZE}" role="img" aria-hidden="true" class="map-svg">` +
      `<circle class="map-orbit" cx="${centre}" cy="${centre}" r="${MAP_RADIUS}"/>` +
      links.join("") +
      `<g class="map-core" transform="translate(${centre} ${centre})">` +
        `<circle class="map-core-wave" r="${CORE_RADIUS}"/><circle class="map-core-wave wave-2" r="${CORE_RADIUS}"/>` +
        `<circle class="map-core-disc" r="${CORE_RADIUS}"/>` +
        `<text class="map-core-label" text-anchor="middle" y="4" data-core></text>` +
      `</g>` +
      nodes.join("") +
    `</svg>`
  );
}

function buildLegend() {
  return TOOL_ORDER.map((tool) => (
    `<li class="legend-item" data-tool="${tool}"><span class="legend-dot kind-${toolKind(tool)}"></span>` +
    `<span class="legend-name" data-legend-name></span><span class="legend-calls" data-legend-calls></span></li>`
  )).join("");
}

function countCalls(steps) {
  const counts = {};
  for (const step of steps) counts[step.tool] = (counts[step.tool] || 0) + 1;
  return counts;
}

function restartAnimation(element, className) {
  element.classList.remove(className);
  void element.getBoundingClientRect();  // forces a reflow so the animation replays
  element.classList.add(className);
}

export function createAgentMap(container) {
  container.innerHTML =
    `<div class="map-stage">${buildSvg()}</div>` +
    `<ul class="map-legend">${buildLegend()}</ul>`;
  const root = container.closest("[data-agent-map-root]") || container;
  let flashedCount = 0;

  const nodeOf = (tool) => container.querySelector(`.map-node[data-tool="${tool}"]`);
  const linkOf = (tool) => container.querySelector(`.map-link[data-tool="${tool}"]`);

  function translateLabels() {
    container.querySelector("[data-core]").textContent = t("agentCore");
    for (const label of container.querySelectorAll("[data-short]")) {
      label.textContent = t(`short_${label.dataset.short}`);
    }
    for (const item of container.querySelectorAll(".legend-item")) {
      const tool = item.dataset.tool;
      item.querySelector("[data-legend-name]").textContent = t(`tool_${tool}`);
    }
  }

  function applyCounts(counts) {
    for (const tool of TOOL_ORDER) {
      const count = counts[tool] || 0;
      const node = nodeOf(tool);
      node.classList.toggle("is-done", count > 0);
      node.querySelector(".map-node-count text").textContent = String(count);
      const item = container.querySelector(`.legend-item[data-tool="${tool}"]`);
      item.classList.toggle("is-done", count > 0);
      item.querySelector("[data-legend-calls]").textContent = count ? `×${count}` : "";
    }
  }

  function flashNewSteps(steps) {
    if (steps.length < flashedCount) flashedCount = 0;
    for (const step of steps.slice(flashedCount)) {
      const node = nodeOf(step.tool);
      const link = linkOf(step.tool);
      if (node) restartAnimation(node, "is-flash");
      if (link) restartAnimation(link, "is-flash");
    }
    flashedCount = steps.length;
  }

  function agentState(steps, { busy, waiting }) {
    if (waiting) return "waiting";
    if (busy) return "thinking";
    return steps.length ? "done" : "idle";
  }

  function update(steps, flags) {
    translateLabels();
    applyCounts(countCalls(steps));
    flashNewSteps(steps);
    const state = agentState(steps, flags);
    root.dataset.agentState = state;
    const statusEl = root.querySelector("[data-agent-status]");
    if (statusEl) {
      const keys = {
        idle: "agentIdle", thinking: "agentThinking", waiting: "agentWaiting", done: "agentDone",
      };
      statusEl.textContent = t(keys[state], { n: steps.length });
    }
  }

  return { update };
}
