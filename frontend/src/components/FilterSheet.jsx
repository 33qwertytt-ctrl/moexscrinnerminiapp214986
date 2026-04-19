import { useEffect, useState } from "react";
import TooltipHelp from "./TooltipHelp.jsx";

const HORIZON = ["7", "14", "30", "60", "90", "120", "150", "180", "210", "240", "270", "300", "330", "360"];
const RATINGS = ["NR", "ruA-", "ruA", "ruA+", "ruAA-", "ruAA", "ruAA+", "ruAAA"];
const CURRENCIES = [
  { value: "RUB", label: "Рубли" },
  { value: "CNY", label: "Юани" },
];
const INVESTOR_PROFILES = [
  { value: "NONQUAL", label: "Неквалифицированный" },
  { value: "QUAL", label: "Квалифицированный" },
];

function LabelWithHelp({ text, help }) {
  return (
    <label className="field-label field-label-with-help">
      <span>{text}</span>
      {help ? <TooltipHelp label={`Справка: ${text}`} text={help} /> : null}
    </label>
  );
}

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

        <LabelWithHelp
          text="Горизонт, дней"
          help="Период, на который считаем доходность до горизонта и аннуализированную доходность для сравнения бумаг."
        />
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

        <LabelWithHelp
          text="Мин. рейтинг выпуска"
          help="Кредитное качество конкретного выпуска облигации. Чем выше рейтинг, тем ниже кредитный риск по шкале агентства."
        />
        <RatingGroup value={localMinBondRating} onChange={setLocalMinBondRating} />

        <LabelWithHelp
          text="Мин. рейтинг эмитента"
          help="Качество самого эмитента как заемщика. Фильтр помогает отсечь бумаги компаний с более слабым кредитным профилем."
        />
        <RatingGroup value={localMinEmitterRating} onChange={setLocalMinEmitterRating} />

        <LabelWithHelp
          text="Лимит бумаг"
          help="Сколько облигаций максимум показывать в выдаче после серверной сортировки и фильтрации."
        />
        <select
          className="select-input"
          value={localLimit}
          onChange={(event) => setLocalLimit(event.target.value)}
        >
          <option value="20">20</option>
          <option value="50">50</option>
          <option value="100">100</option>
        </select>

        <LabelWithHelp
          text="Валюта"
          help="Валюта номинала и основных денежных потоков по облигации."
        />
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

        <LabelWithHelp
          text="Статус инвестора"
          help="Позволяет скрыть бумаги, доступные только квалифицированным инвесторам."
        />
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

        <LabelWithHelp
          text="Аннуализированная доходность (линейная), %"
          help="Доходность до выбранного горизонта, линейно приведенная к году. Удобна для быстрого сравнения бумаг между собой."
        />
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

        <LabelWithHelp
          text="Годовая доходность облигации, %"
          help="Биржевая доходность бумаги из данных MOEX. Это отдельный показатель, не равный нашей аннуализации по выбранному горизонту."
        />
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
