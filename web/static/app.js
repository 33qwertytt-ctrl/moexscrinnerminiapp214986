const body = document.getElementById("bondsTableBody");
const emitterSelect = document.getElementById("minEmitterRating");
const bondSelect = document.getElementById("minBondRating");
const refreshBtn = document.getElementById("refreshBtn");
const headers = document.querySelectorAll("#bondsTable th");

let rows = [];
let sortState = { key: "annual_yield", direction: "desc" };

function formatNumber(value, digits = 2) {
  return Number(value).toFixed(digits);
}

function applyYieldClass(td, value) {
  td.classList.remove("yield-high", "yield-low");
  if (value > 20) {
    td.classList.add("yield-high");
  } else if (value < 10) {
    td.classList.add("yield-low");
  }
}

function renderTable() {
  body.innerHTML = "";
  rows.forEach((bond) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${bond.ticker}</td>
      <td>${bond.name}</td>
      <td>${bond.rating}</td>
      <td>${formatNumber(bond.price)}</td>
      <td>${formatNumber(bond.coupon_percent)}</td>
      <td>${bond.coupons_per_year}</td>
      <td data-col="annual">${formatNumber(bond.annual_yield)}</td>
      <td>${formatNumber(bond.yield_to_horizon)}</td>
      <td>${formatNumber(bond.months_to_maturity, 1)}</td>
    `;
    const annualCell = tr.querySelector('[data-col="annual"]');
    applyYieldClass(annualCell, Number(bond.annual_yield));
    body.appendChild(tr);
  });
}

function sortRows(key) {
  const direction = sortState.key === key && sortState.direction === "asc" ? "desc" : "asc";
  sortState = { key, direction };
  applySort();
}

function applySort() {
  const { key, direction } = sortState;
  rows.sort((a, b) => {
    const left = a[key];
    const right = b[key];
    if (typeof left === "number" && typeof right === "number") {
      return direction === "asc" ? left - right : right - left;
    }
    return direction === "asc"
      ? String(left).localeCompare(String(right))
      : String(right).localeCompare(String(left));
  });
  renderTable();
}

function buildApiUrl() {
  const params = new URLSearchParams();
  if (emitterSelect.value) {
    params.set("min_emitter_rating", emitterSelect.value);
  }
  if (bondSelect.value) {
    params.set("min_bond_rating", bondSelect.value);
  }
  return `/api/bonds?${params.toString()}`;
}

async function loadBonds() {
  refreshBtn.disabled = true;
  try {
    const response = await fetch(buildApiUrl(), { headers: { Accept: "application/json" } });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    rows = await response.json();
    applySort();
  } catch (error) {
    body.innerHTML = `<tr><td colspan="9">Failed to load bonds: ${error.message}</td></tr>`;
  } finally {
    refreshBtn.disabled = false;
  }
}

headers.forEach((th) => {
  th.addEventListener("click", () => {
    const key = th.dataset.key;
    if (key) {
      sortRows(key);
    }
  });
});

refreshBtn.addEventListener("click", () => {
  loadBonds();
});

emitterSelect.addEventListener("change", () => {
  loadBonds();
});

bondSelect.addEventListener("change", () => {
  loadBonds();
});

if (window.Telegram && window.Telegram.WebApp) {
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
}

loadBonds();
