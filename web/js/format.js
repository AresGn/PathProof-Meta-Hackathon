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

function decimalParts(value) {
  const match = /^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(String(value));
  if (!match) throw new TypeError(`not a finite decimal: ${value}`);
  const fraction = match[3] || "";
  const exponent = Number(match[4] || 0);
  let units = BigInt(`${match[2]}${fraction}`);
  let scale = fraction.length - exponent;
  if (scale < 0) {
    units *= 10n ** BigInt(-scale);
    scale = 0;
  }
  if (match[1] === "-") units *= -1n;
  return { units, scale };
}

function rescaleDecimal(decimal, scale) {
  return decimal.units * 10n ** BigInt(scale - decimal.scale);
}

export function sumWeightedGrades(inputs) {
  const grades = inputs.map((entry) => decimalParts(entry.note));
  const scale = Math.max(0, ...grades.map((grade) => grade.scale));
  const products = grades.map(
    (grade, index) => rescaleDecimal(grade, scale) * BigInt(inputs[index].coefficient)
  );
  return { products, total: products.reduce((sum, product) => sum + product, 0n), scale };
}

export function formatCalculationNumber(units, scale) {
  const displayScale = 2;
  let cents = units;
  if (scale > displayScale) {
    const divisor = 10n ** BigInt(scale - displayScale);
    const absolute = cents < 0n ? -cents : cents;
    cents = (absolute + divisor / 2n) / divisor * (units < 0n ? -1n : 1n);
  } else if (scale < displayScale) {
    cents *= 10n ** BigInt(displayScale - scale);
  }
  const absoluteCents = cents < 0n ? -cents : cents;
  const whole = absoluteCents / 100n;
  const fraction = String(absoluteCents % 100n).padStart(2, "0");
  const sign = cents < 0n ? "-" : "";
  return formatNumber(`${sign}${whole}.${fraction}`);
}
