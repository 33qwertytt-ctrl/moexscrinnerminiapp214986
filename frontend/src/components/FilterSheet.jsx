import { useEffect, useState } from "react";

const HORIZON = ["7", "14", "30", "90"];
const RATINGS = ["ruA", "ruA+", "ruAA-", "ruAA", "ruAA+", "ruAAA"];
const CURRENCIES = [
  { value: "RUB", label: "Рубли" },
  { value: "CNY", label: "Юани" },
];
const INVESTOR_PROFILES = [
  { value: "NONQUAL", label: "Не квал" },
  { value: "QUAL", label: "Квал" },
];

export default function FilterSheet({
  open,
  onClose,
  horizon,
  rating,
  currency,
  investorProfile,
  limit,
  yieldMin,
  yieldMax,
  onApply,
}) {
  const [localHorizon, setLocalHorizon] = useState(horizon);
  const [localRating, setLocalRating] = useState(rating);
  const [localCurrency, setLocalCurrency] = useState(currency);
  const [localInvestorProfile, setLocalInvestorProfile] = useState(investorProfile);
  const [localLimit, setLocalLimit] = useState(limit);
  const [localYieldMin, setLocalYieldMin] = useState(yieldMin);
  const [localYieldMax, setLocalYieldMax] = useState(yieldMax);

  useEffect(() => {
    if (!open) return;
    setLocalHorizon(horizon);
    setLocalRating(rating);
    setLocalCurrency(currency);
    setLocalInvestorProfile(investorProfile);
    setLocalLimit(limit);
    setLocalYieldMin(yieldMin);
    setLocalYieldMax(yieldMax);
  }, [open, horizon, rating, currency, investorProfile, limit, yieldMin, yieldMax]);

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

        <label className="field-label">Мин. рейтинг с сервера</label>
        <div className="chip-row wrap">
          {RATINGS.map((value) => (
            <button
              key={value}
              type="button"
              className={value === localRating ? "chip active" : "chip"}
              onClick={() => setLocalRating(value)}
            >
              {value}
            </button>
          ))}
        </div>

        <label className="field-label">Лимит бумаг с сервера</label>
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
        <div className="chip-row">
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

        <label className="field-label">Годовая доходность, %</label>
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
                rating: localRating,
                currency: localCurrency,
                investorProfile: localInvestorProfile,
                limit: localLimit,
                yieldMin: localYieldMin,
                yieldMax: localYieldMax,
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
