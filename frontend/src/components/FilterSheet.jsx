import { useEffect, useState } from "react";

const HORIZON = ["7", "14", "30", "90"];
const RATINGS = ["NR", "ruA-", "ruA", "ruA+", "ruAA-", "ruAA", "ruAA+", "ruAAA"];
const CURRENCIES = [
  { value: "RUB", label: "Рубли" },
  { value: "CNY", label: "Юани" },
];
const INVESTOR_PROFILES = [
  { value: "NONQUAL", label: "Неквалифицированный" },
  { value: "QUAL", label: "Квалифицированный" },
];

function RatingGroup({ value, onChange }) {
  return (
    <div className="chip-row wrap">
      {RATINGS.map((item) => (
        <button
          key={item}
          type="button"
          className={item === value ? "chip active" : "chip"}
          onClick={() => onChange(item)}
        >
          {item}
        </button>
      ))}
    </div>
  );
}

export default function FilterSheet({
  open,
  onClose,
  horizon,
  minBondRating,
  minEmitterRating,
  currency,
  investorProfile,
  limit,
  yieldMin,
  yieldMax,
  bondYieldMin,
  bondYieldMax,
  onApply,
}) {
  const [localHorizon, setLocalHorizon] = useState(horizon);
  const [localMinBondRating, setLocalMinBondRating] = useState(minBondRating);
  const [localMinEmitterRating, setLocalMinEmitterRating] = useState(minEmitterRating);
  const [localCurrency, setLocalCurrency] = useState(currency);
  const [localInvestorProfile, setLocalInvestorProfile] = useState(investorProfile);
  const [localLimit, setLocalLimit] = useState(limit);
  const [localYieldMin, setLocalYieldMin] = useState(yieldMin);
  const [localYieldMax, setLocalYieldMax] = useState(yieldMax);
  const [localBondYieldMin, setLocalBondYieldMin] = useState(bondYieldMin);
  const [localBondYieldMax, setLocalBondYieldMax] = useState(bondYieldMax);

  useEffect(() => {
    if (!open) return;
    setLocalHorizon(horizon);
    setLocalMinBondRating(minBondRating);
    setLocalMinEmitterRating(minEmitterRating);
    setLocalCurrency(currency);
    setLocalInvestorProfile(investorProfile);
    setLocalLimit(limit);
    setLocalYieldMin(yieldMin);
    setLocalYieldMax(yieldMax);
    setLocalBondYieldMin(bondYieldMin);
    setLocalBondYieldMax(bondYieldMax);
  }, [
    open,
    horizon,
    minBondRating,
    minEmitterRating,
    currency,
    investorProfile,
    limit,
    yieldMin,
    yieldMax,
    bondYieldMin,
    bondYieldMax,
  ]);

  if (!open) return null;

  return (
    <div className="sheet-overlay" role="presentation" onClick={onClose}>
      <div
        className="sheet-panel"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sheet-handle" />
        <h2 className="sheet-title">Фильтры</h2>

        <label className="field-label">Горизонт, дней</label>
        <div className="chip-row">
          {HORIZON.map((value) => (
            <button
              key={value}
              type="button"
              className={value === localHorizon ? "chip active" : "chip"}
              onClick={() => setLocalHorizon(value)}
            >
              {value}
            </button>
          ))}
        </div>

        <label className="field-label">Мин. рейтинг выпуска</label>
        <RatingGroup value={localMinBondRating} onChange={setLocalMinBondRating} />

        <label className="field-label">Мин. рейтинг эмитента</label>
        <RatingGroup value={localMinEmitterRating} onChange={setLocalMinEmitterRating} />

        <label className="field-label">Лимит бумаг</label>
        <select
          className="select-input"
          value={localLimit}
          onChange={(event) => setLocalLimit(event.target.value)}
        >
          <option value="20">20</option>
          <option value="50">50</option>
          <option value="100">100</option>
        </select>

        <label className="field-label">Валюта</label>
        <div className="chip-row">
          {CURRENCIES.map((item) => (
            <button
              key={item.value}
              type="button"
              className={item.value === localCurrency ? "chip active" : "chip"}
              onClick={() => setLocalCurrency(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <label className="field-label">Статус инвестора</label>
        <div className="chip-row wrap">
          {INVESTOR_PROFILES.map((item) => (
            <button
              key={item.value}
              type="button"
              className={item.value === localInvestorProfile ? "chip active" : "chip"}
              onClick={() => setLocalInvestorProfile(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <label className="field-label">Аннуализированная доходность (линейная), %</label>
        <div className="two-col">
          <input
            type="number"
            className="text-input"
            placeholder="от"
            value={localYieldMin}
            onChange={(event) => setLocalYieldMin(event.target.value)}
          />
          <input
            type="number"
            className="text-input"
            placeholder="до"
            value={localYieldMax}
            onChange={(event) => setLocalYieldMax(event.target.value)}
          />
        </div>

        <label className="field-label">Годовая доходность облигации, %</label>
        <div className="two-col">
          <input
            type="number"
            className="text-input"
            placeholder="от"
            value={localBondYieldMin}
            onChange={(event) => setLocalBondYieldMin(event.target.value)}
          />
          <input
            type="number"
            className="text-input"
            placeholder="до"
            value={localBondYieldMax}
            onChange={(event) => setLocalBondYieldMax(event.target.value)}
          />
        </div>

        <div className="sheet-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Закрыть
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              onApply({
                horizon: localHorizon,
                minBondRating: localMinBondRating,
                minEmitterRating: localMinEmitterRating,
                currency: localCurrency,
                investorProfile: localInvestorProfile,
                limit: localLimit,
                yieldMin: localYieldMin,
                yieldMax: localYieldMax,
                bondYieldMin: localBondYieldMin,
                bondYieldMax: localBondYieldMax,
              });
              onClose();
            }}
          >
            Применить
          </button>
        </div>
      </div>
    </div>
  );
}
