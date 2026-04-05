import assert from "node:assert/strict";
import test from "node:test";

import { compileIndicator, tokensToFormula } from "./indicator.js";

const sampleBond = {
  annual_yield: 18,
  bond_annual_yield: 16,
  yield_to_horizon: 7,
  price: 95,
  coupon_percent: 12,
  coupons_per_year: 4,
  months_to_maturity: 14,
  rating: "AA-/AA",
};

test("tokensToFormula joins blocks into expression", () => {
  assert.equal(tokensToFormula(["annual_yield", "/", "price"]), "annual_yield / price");
});

test("compileIndicator evaluates arithmetic expression", () => {
  const fn = compileIndicator("( annual_yield + horizon_yield ) / 2");
  assert.equal(fn(sampleBond), 12.5);
});

test("compileIndicator supports functions and derivatives", () => {
  const fn = compileIndicator("diff_price( annual_yield * price )");
  assert.ok(Math.abs(fn(sampleBond) - 18) < 0.01);
});

test("compileIndicator rejects unsafe global access", () => {
  assert.throws(() => compileIndicator("globalThis.alert(1)"));
});
