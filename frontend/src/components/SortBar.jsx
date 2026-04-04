const BASE_LABELS = {
  annual_yield: "Годовая доходность",
  price: "Цена",
  rating: "Рейтинг",
};

export default function SortBar({ sortKey, sortPhase, hasIndicator, indicatorLabel, onCycle }) {
  const keys = hasIndicator
    ? ["annual_yield", "price", "rating", "indicator"]
    : ["annual_yield", "price", "rating"];
  const labels = {
    ...BASE_LABELS,
    indicator: indicatorLabel || "Свой индикатор",
  };

  const arrow = (key) => {
    if (sortKey !== key || sortPhase === 0) return "↕";
    if (sortPhase === 1) return "↓";
    return "↑";
  };

  return (
    <div className="sort-bar">
      {keys.map((key) => (
        <button
          key={key}
          type="button"
          className={`sort-pill tap-scale ${sortKey === key && sortPhase > 0 ? "active" : ""}`}
          onClick={() => onCycle(key)}
        >
          {labels[key]} {arrow(key)}
        </button>
      ))}
    </div>
  );
}
