export function buildBondsQuery({ horizon, rating, limit, currency, investorProfile }) {
  const p = new URLSearchParams();
  p.set("horizon_days", horizon);
  p.set("limit", limit);
  p.set("min_bond_rating", rating);
  p.set("min_emitter_rating", rating);
  if (currency) {
    p.set("currency", currency);
  }
  if (investorProfile) {
    p.set("investor_profile", investorProfile);
  }
  return p.toString();
}

export async function fetchBonds(params) {
  const qs = buildBondsQuery(params);
  const res = await fetch(`/api/bonds?${qs}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const data = await res.json();
  return Array.isArray(data) ? data : [];
}
