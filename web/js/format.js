// Small display formatters shared by the steps, proofs and report views.
import { getLanguage } from "./i18n.js";

export function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );
}

export function formatDetail(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? null, null, 2);
  return text.length > 2000 ? `${text.slice(0, 2000)}…` : text;
}

// French writes decimals with a comma (13,15); English keeps the point.
export function formatNumber(value) {
  return getLanguage() === "fr"
    ? String(value ?? "").replace(".", ",")
    : String(value ?? "");
}
