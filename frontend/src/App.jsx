import { useCallback, useEffect, useMemo, useState } from "react";
import BondCard from "./components/BondCard.jsx";
import FeedbackPanel from "./components/FeedbackPanel.jsx";
import FilterSheet from "./components/FilterSheet.jsx";
import HeaderBar from "./components/HeaderBar.jsx";
import IndicatorPanel from "./components/IndicatorPanel.jsx";
import SortBar from "./components/SortBar.jsx";
import { fetchBonds } from "./lib/bondApi.js";
import { compileIndicator, tokensToFormula } from "./lib/indicator.js";
import { fetchPublicConfig } from "./lib/publicConfig.js";
import { ratingSortValue } from "./lib/ratings.js";

function applyClientFilters(rows, { search, yieldMin, yieldMax, bondYieldMin, bondYieldMax }) {
  const query = search.trim().toLowerCase();
  return rows.filter((row) => {
    const searchIndex = `${row.ticker} ${row.name} ${row.company || ""}`.toLowerCase();
    if (query && !searchIndex.includes(query)) {
      return false;
    }
    const annualYield = Number(row.annual_yield);
    if (yieldMin !== "" && !Number.isNaN(Number(yieldMin)) && annualYield < Number(yieldMin)) {
      return false;
    }
    if (yieldMax !== "" && !Number.isNaN(Number(yieldMax)) && annualYield > Number(yieldMax)) {
      return false;
    }
    const bondAnnualYield = Number(row.bond_annual_yield);
    if (
      bondYieldMin !== "" &&
      !Number.isNaN(Number(bondYieldMin)) &&
      bondAnnualYield < Number(bondYieldMin)
    ) {
      return false;
    }
    if (
      bondYieldMax !== "" &&
      !Number.isNaN(Number(bondYieldMax)) &&
      bondAnnualYield > Number(bondYieldMax)
    ) {
      return false;
    }
    return true;
  });
}

function sortRows(rows, sortKey, sortPhase, baseIndex, getIndicator) {
  if (sortPhase === 0) {
    return [...rows].sort((a, b) => (baseIndex[a.ticker] ?? 0) - (baseIndex[b.ticker] ?? 0));
  }
  const desc = sortPhase === 1;
  return [...rows].sort((a, b) => {
    let leftValue;
    let rightValue;
    switch (sortKey) {
      case "annual_yield":
        leftValue = Number(a.annual_yield);
        rightValue = Number(b.annual_yield);
        break;
      case "price":
        leftValue = Number(a.price);
        rightValue = Number(b.price);
        break;
      case "rating":
        leftValue = ratingSortValue(a.rating);
        rightValue = ratingSortValue(b.rating);
        break;
      case "indicator":
        leftValue = getIndicator(a);
        rightValue = getIndicator(b);
        break;
      default:
        return (baseIndex[a.ticker] ?? 0) - (baseIndex[b.ticker] ?? 0);
    }
    if (!Number.isFinite(leftValue)) {
      leftValue = desc ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY;
    }
    if (!Number.isFinite(rightValue)) {
      rightValue = desc ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY;
    }
    const comparison = leftValue === rightValue ? 0 : leftValue < rightValue ? -1 : 1;
    const oriented = desc ? -comparison : comparison;
    if (oriented !== 0) return oriented;
    return (baseIndex[a.ticker] ?? 0) - (baseIndex[b.ticker] ?? 0);
  });
}

export default function App() {
  const [horizon, setHorizon] = useState("30");
  const [minBondRating, setMinBondRating] = useState("ruA");
  const [minEmitterRating, setMinEmitterRating] = useState("ruA");
  const [currency, setCurrency] = useState("RUB");
  const [investorProfile, setInvestorProfile] = useState("NONQUAL");
  const [limit, setLimit] = useState("100");
  const [search, setSearch] = useState("");
  const [yieldMin, setYieldMin] = useState("");
  const [yieldMax, setYieldMax] = useState("");
  const [bondYieldMin, setBondYieldMin] = useState("");
  const [bondYieldMax, setBondYieldMax] = useState("");

  const [rows, setRows] = useState([]);
  const [baseIndex, setBaseIndex] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const [sortKey, setSortKey] = useState(null);
  const [sortPhase, setSortPhase] = useState(0);

  const [indicatorOpen, setIndicatorOpen] = useState(false);
  const [indName, setIndName] = useState("");
  const [indTokens, setIndTokens] = useState([]);
  const [indError, setIndError] = useState("");
  const [indActive, setIndActive] = useState(false);

  const [pub, setPub] = useState(null);

  const indicatorFormula = useMemo(() => tokensToFormula(indTokens), [indTokens]);

  const indicatorCompiler = useMemo(() => {
    if (!indicatorFormula) {
      return { fn: null, error: "" };
    }
    try {
      return { fn: compileIndicator(indicatorFormula), error: "" };
    } catch (compileError) {
      return {
        fn: null,
        error: compileError instanceof Error ? compileError.message : "Формула не собирается.",
      };
    }
  }, [indicatorFormula]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBonds({
        horizon,
        minBondRating,
        minEmitterRating,
        currency,
        investorProfile,
        limit,
      });
      setRows(data);
      const nextIndex = {};
      data.forEach((row, index) => {
        nextIndex[row.ticker] = index;
      });
      setBaseIndex(nextIndex);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : String(loadError));
      setRows([]);
      setBaseIndex({});
    } finally {
      setLoading(false);
    }
  }, [horizon, minBondRating, minEmitterRating, currency, investorProfile, limit]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void fetchPublicConfig()
      .then(setPub)
      .catch(() => setPub(null));
  }, []);

  useEffect(() => {
    if (!indActive && sortKey === "indicator") {
      setSortKey(null);
      setSortPhase(0);
    }
  }, [indActive, sortKey]);

  const indicatorPreviewValue = useMemo(() => {
    if (!rows[0] || !indicatorCompiler.fn) {
      return Number.NaN;
    }
    return indicatorCompiler.fn(rows[0]);
  }, [rows, indicatorCompiler]);

  const getIndicator = useMemo(() => {
    if (!indActive || !indicatorCompiler.fn) {
      return () => Number.NaN;
    }
    return (bond) => indicatorCompiler.fn(bond);
  }, [indActive, indicatorCompiler]);

  const filtered = useMemo(
    () => applyClientFilters(rows, { search, yieldMin, yieldMax, bondYieldMin, bondYieldMax }),
    [rows, search, yieldMin, yieldMax, bondYieldMin, bondYieldMax],
  );

  const displayed = useMemo(
    () => sortRows(filtered, sortKey, sortPhase, baseIndex, getIndicator),
    [filtered, sortKey, sortPhase, baseIndex, getIndicator],
  );

  function cycleSort(key) {
    if (key === "indicator" && !indActive) return;
    setSortKey((previousKey) => {
      if (previousKey !== key) {
        setSortPhase(1);
        return key;
      }
      setSortPhase((phase) => (phase >= 2 ? 0 : phase + 1));
      return key;
    });
  }

  function touchIndicatorDraft(mutator) {
    mutator();
    setIndError("");
    setIndActive(false);
  }

  function handleIndicatorApply() {
    if (!indicatorFormula) {
      setIndError("Добавьте блоки в формулу.");
      setIndActive(false);
      return;
    }
    if (!indicatorCompiler.fn) {
      setIndError(indicatorCompiler.error || "Формула не собирается.");
      setIndActive(false);
      return;
    }
    if (rows.length > 0 && !Number.isFinite(indicatorPreviewValue)) {
      setIndError("Формула дает нечисловой результат на текущих данных.");
      setIndActive(false);
      return;
    }
    setIndError("");
    setIndActive(true);
    setSortKey("indicator");
    setSortPhase(1);
    setIndicatorOpen(false);
  }

  return (
    <main className="app">
      <HeaderBar
        search={search}
        onSearchChange={setSearch}
        onOpenFilters={() => setFilterOpen(true)}
      />

      <div className="app-title-block">
        <h1 className="app-title">Облигации MOEX</h1>
        <p className="disclaimer">
          Данные носят справочный характер и не являются инвестиционной рекомендацией.
        </p>
      </div>

      <div className="toolbar-inline">
        <button
          type="button"
          className="btn-secondary tap-scale"
          onClick={() => void load()}
          disabled={loading}
        >
          {loading ? "Загрузка…" : "Обновить"}
        </button>
        <button
          type="button"
          className={`btn-secondary tap-scale toolbar-indicator-btn ${
            indActive ? "toolbar-indicator-btn-active" : ""
          }`}
          onClick={() => setIndicatorOpen(true)}
        >
          {indActive ? indName || "Индикатор" : "Свой индикатор"}
        </button>
      </div>

      <SortBar
        sortKey={sortKey}
        sortPhase={sortPhase}
        hasIndicator={indActive}
        indicatorLabel={indName || "Свой индикатор"}
        onCycle={cycleSort}
      />

      <IndicatorPanel
        open={indicatorOpen}
        onClose={() => setIndicatorOpen(false)}
        name={indName}
        tokens={indTokens}
        formula={indicatorFormula}
        error={indError || indicatorCompiler.error}
        previewValue={indicatorPreviewValue}
        isActive={indActive}
        onNameChange={(value) => touchIndicatorDraft(() => setIndName(value))}
        onAddToken={(token) =>
          touchIndicatorDraft(() => setIndTokens((current) => [...current, token]))
        }
        onAddConstant={(value) =>
          touchIndicatorDraft(() => {
            const normalized = String(value).trim();
            if (!normalized) return;
            setIndTokens((current) => [...current, normalized]);
          })
        }
        onRemoveToken={(index) =>
          touchIndicatorDraft(() =>
            setIndTokens((current) =>
              current.filter((_, currentIndex) => currentIndex !== index),
            ),
          )
        }
        onRemoveLastToken={() =>
          touchIndicatorDraft(() => setIndTokens((current) => current.slice(0, -1)))
        }
        onReset={() =>
          touchIndicatorDraft(() => {
            setIndName("");
            setIndTokens([]);
          })
        }
        onApply={handleIndicatorApply}
      />

      {error && <p className="error-banner">{error}</p>}

      <section className="bond-list" aria-busy={loading}>
        {loading &&
          Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="bond-card skeleton" aria-hidden>
              <div className="sk-line lg" />
              <div className="sk-line sm" />
              <div className="sk-block hero" />
              <div className="sk-grid">
                <div className="sk-line" />
                <div className="sk-line" />
                <div className="sk-line" />
                <div className="sk-line" />
              </div>
            </div>
          ))}
        {!loading &&
          displayed.map((row) => (
            <BondCard
              key={row.ticker}
              bond={row}
              indicatorName={indActive ? indName || "Индикатор" : ""}
              indicatorValue={indActive ? getIndicator(row) : Number.NaN}
            />
          ))}
      </section>

      {!loading && displayed.length === 0 && !error && (
        <p className="muted center-pad">Нет бумаг по фильтрам.</p>
      )}

      {pub && (
        <footer className="app-footer muted small">
          {pub.public_domain && <span>Хост: {pub.public_domain}</span>}
          {pub.public_ipv4 && <span> · IPv4 {pub.public_ipv4}</span>}
          {pub.public_ipv6 && <span> · IPv6 {pub.public_ipv6}</span>}
        </footer>
      )}

      <FilterSheet
        open={filterOpen}
        onClose={() => setFilterOpen(false)}
        horizon={horizon}
        minBondRating={minBondRating}
        minEmitterRating={minEmitterRating}
        currency={currency}
        investorProfile={investorProfile}
        limit={limit}
        yieldMin={yieldMin}
        yieldMax={yieldMax}
        bondYieldMin={bondYieldMin}
        bondYieldMax={bondYieldMax}
        onApply={(params) => {
          setHorizon(params.horizon);
          setMinBondRating(params.minBondRating);
          setMinEmitterRating(params.minEmitterRating);
          setCurrency(params.currency);
          setInvestorProfile(params.investorProfile);
          setLimit(params.limit);
          setYieldMin(params.yieldMin);
          setYieldMax(params.yieldMax);
          setBondYieldMin(params.bondYieldMin);
          setBondYieldMax(params.bondYieldMax);
        }}
      />

      <FeedbackPanel
        maxAttachmentBytes={pub?.feedback_max_attachment_bytes}
        maxMessageChars={pub?.feedback_max_message_chars}
        allowedMimeTypes={pub?.feedback_allowed_mime_types}
      />
    </main>
  );
}
