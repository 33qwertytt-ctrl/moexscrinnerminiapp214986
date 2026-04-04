import TooltipHelp from "./TooltipHelp.jsx";

const YIELD_HELP =
  "Годовая доходность здесь соответствует расчёту скринера: доходность до выбранного горизонта, " +
  "масштабированная на год для сравнения бумаг.";

const HORIZON_HELP =
  "Доходность до горизонта — ожидаемая доходность за выбранный период " +
  "относительно текущей цены по правилам скринера.";

function openTinkoffDeep(ticker) {
  const deep = `tinkoff://invest/bond/${encodeURIComponent(ticker)}`;
  const web = `https://www.tinkoff.ru/invest/bonds/${encodeURIComponent(ticker)}/`;
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink) {
    tg.openLink(deep);
  } else {
    window.open(web, "_blank", "noopener,noreferrer");
  }
}

function openTinkoffWeb(ticker) {
  const web = `https://www.tinkoff.ru/invest/bonds/${encodeURIComponent(ticker)}/`;
  const tg = window.Telegram?.WebApp;
  if (tg?.openLink) {
    tg.openLink(web);
  } else {
    window.open(web, "_blank", "noopener,noreferrer");
  }
}

function buildBondTitle(name, company) {
  const normalizedName = String(name || "").trim();
  const normalizedCompany = String(company || "").trim();
  if (!normalizedCompany) {
    return normalizedName;
  }
  if (normalizedName.toLowerCase().includes(normalizedCompany.toLowerCase())) {
    return normalizedName;
  }
  return `${normalizedName}, ${normalizedCompany}`;
}

export default function BondCard({ bond, indicatorName, indicatorValue }) {
  const annualYield = Number(bond.annual_yield);
  const annualYieldClass =
    annualYield > 20 ? "yield-accent-high" : annualYield < 10 ? "yield-accent-low" : "yield-accent-mid";
  const title = buildBondTitle(bond.name, bond.company);

  return (
    <article className="bond-card tap-scale">
      <div className="bond-card-top">
        <div className="bond-ticker-row">
          <span className="bond-ticker">{bond.ticker}</span>
          <span className="bond-rating-pill">{bond.rating}</span>
        </div>
        <h3 className="bond-name">{title}</h3>
      </div>

      <div className="bond-yield-hero">
        <span className="bond-yield-label">
          Годовая доходность, %
          <TooltipHelp label="Справка по годовой" text={YIELD_HELP} />
        </span>
        <span className={`bond-yield-value ${annualYieldClass}`}>{annualYield.toFixed(2)}</span>
      </div>

      <div className="bond-grid">
        <div>
          <span className="muted">Цена</span>
          <div className="bond-stat">{Number(bond.price).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted">
            До горизонта, %
            <TooltipHelp label="Справка по горизонту" text={HORIZON_HELP} />
          </span>
          <div className="bond-stat">{Number(bond.yield_to_horizon).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted">Купон, %</span>
          <div className="bond-stat">{Number(bond.coupon_percent).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted">Купонов / год</span>
          <div className="bond-stat">{bond.coupons_per_year}</div>
        </div>
        <div className="span-2">
          <span className="muted">Месяцев до погашения</span>
          <div className="bond-stat">{Number(bond.months_to_maturity).toFixed(1)}</div>
        </div>
      </div>

      {indicatorName && Number.isFinite(indicatorValue) && (
        <div className="bond-custom-metric">
          <span className="muted">{indicatorName}</span>
          <span className="bond-custom-value">{indicatorValue.toFixed(4)}</span>
        </div>
      )}

      <div className="bond-actions">
        <button type="button" className="btn-tinkoff" onClick={() => openTinkoffDeep(bond.ticker)}>
          Открыть в Т-Инвестициях
        </button>
        <button type="button" className="btn-linky" onClick={() => openTinkoffWeb(bond.ticker)}>
          В браузере
        </button>
      </div>
    </article>
  );
}
