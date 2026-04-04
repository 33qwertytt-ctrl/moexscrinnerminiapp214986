/** Согласовано с API / app/bonds_service (шкала для сортировки). */

export const RATING_ORDER = [
  "NR",
  "BBB-",
  "BBB",
  "BBB+",
  "A-",
  "A",
  "A+",
  "AA-",
  "AA",
  "AA+",
  "AAA",
];

function normalizeRatingToken(raw) {
  const lowered = String(raw || "")
    .toLowerCase()
    .trim();
  if (!lowered || lowered === "н/д" || lowered === "n/a") return "NR";

  const ruSuffix = lowered.match(/([ab]{1,3}[+-]?)\s*\(ru\)/);
  if (ruSuffix) return ruSuffix[1].toUpperCase();

  const ruPrefix = lowered.match(/ru([ab]{1,3}[+-]?)/);
  if (ruPrefix) return ruPrefix[1].toUpperCase();

  for (const rating of [...RATING_ORDER].sort((a, b) => b.length - a.length)) {
    if (rating !== "NR" && lowered.includes(rating.toLowerCase())) return rating;
  }
  return "NR";
}

export function rankToken(token) {
  const n = normalizeRatingToken(token);
  const idx = RATING_ORDER.indexOf(n);
  return idx === -1 ? 0 : idx;
}

/** Для строки `выпуск/эмитент` берём худший ранг (ниже по шкале). */
export function ratingSortValue(rawRating) {
  const parts = String(rawRating || "").split("/");
  let worst = RATING_ORDER.length;
  for (const p of parts) {
    const r = rankToken(p.trim());
    worst = Math.min(worst, r);
  }
  return worst === RATING_ORDER.length ? 0 : worst;
}
