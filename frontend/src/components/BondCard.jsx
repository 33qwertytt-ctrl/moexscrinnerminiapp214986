import TooltipHelp from "./TooltipHelp.jsx";

const YIELD_HELP =
  "Аннуализированная доходность здесь соответствует расчёту скринера: доходность до выбранного горизонта, " +
  "масштабированная на год для сравнения бумаг.";

const HORIZON_HELP =
  "Доходность до горизонта — ожидаемая доходность за выбранный период " +
  "относительно текущей цены по правилам скринера.";

const ISSUE_RATING_HELP =
  "Кредитное качество выпуска: рейтинг именно этой облигации, если он присвоен и доступен в источниках данных.";

const ISSUER_RATING_HELP =
  "Качество эмитента: рейтинг компании или организации, выпустившей облигацию.";

const COUPON_HELP =
  "Текущая ставка купона по облигации в процентах годовых.";

const COUPONS_PER_YEAR_HELP =
  "Сколько купонных выплат в год предполагается по параметрам выпуска.";

const MATURITY_HELP =
  "Сколько месяцев осталось до оферты или погашения, в зависимости от того, что наступит раньше.";

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

function splitRating(rawRating) {
  const parts = String(rawRating || "").split("/");
  return {
    issue: parts[0]?.trim() || "NR",
    issuer: parts[1]?.trim() || parts[0]?.trim() || "NR",
  };
}

export default function BondCard({ bond, indicatorName, indicatorValue }) {
  const annualYield = Number(bond.annual_yield);
  const bondAnnualYield = Number(bond.bond_annual_yield);
  const { issue, issuer } = splitRating(bond.rating);
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
          Аннуализированная доходность (линейная), %
          <TooltipHelp label="Справка по годовой" text={YIELD_HELP} />
        </span>
        <span className={`bond-yield-value ${annualYieldClass}`}>{annualYield.toFixed(2)}</span>
      </div>

      <div className="bond-grid">
        <div>
          <span className="muted field-inline-help">
            Кредитное качество
            <TooltipHelp label="Справка по кредитному качеству" text={ISSUE_RATING_HELP} />
          </span>
          <div className="bond-stat">{issue}</div>
        </div>
        <div>
          <span className="muted field-inline-help">
            Качество эмитента
            <TooltipHelp label="Справка по качеству эмитента" text={ISSUER_RATING_HELP} />
          </span>
          <div className="bond-stat">{issuer}</div>
        </div>
        <div>
          <span className="muted">Цена</span>
          <div className="bond-stat">{Number(bond.price).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted">Годовая доходность облигации, %</span>
          <div className="bond-stat">{bondAnnualYield.toFixed(2)}</div>
        </div>
        <div>
          <span className="muted field-inline-help">
            До горизонта, %
            <TooltipHelp label="Справка по горизонту" text={HORIZON_HELP} />
          </span>
          <div className="bond-stat">{Number(bond.yield_to_horizon).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted field-inline-help">
            Купон, %
            <TooltipHelp label="Справка по купону" text={COUPON_HELP} />
          </span>
          <div className="bond-stat">{Number(bond.coupon_percent).toFixed(2)}</div>
        </div>
        <div>
          <span className="muted field-inline-help">
            Купонов / год
            <TooltipHelp label="Справка по частоте купона" text={COUPONS_PER_YEAR_HELP} />
          </span>
          <div className="bond-stat">{bond.coupons_per_year}</div>
        </div>
        <div className="span-2">
          <span className="muted field-inline-help">
            Месяцев до погашения
            <TooltipHelp label="Справка по сроку" text={MATURITY_HELP} />
          </span>
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
