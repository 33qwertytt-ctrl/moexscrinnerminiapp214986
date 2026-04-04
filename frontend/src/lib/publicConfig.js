let cached = null;

export async function fetchPublicConfig() {
  if (cached) return cached;
  const res = await fetch("/api/public-config");
  if (!res.ok) throw new Error("public-config");
  cached = await res.json();
  return cached;
}

export function clearPublicConfigCache() {
  cached = null;
}
