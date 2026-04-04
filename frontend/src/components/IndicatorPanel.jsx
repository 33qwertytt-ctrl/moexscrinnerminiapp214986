import { useEffect, useState } from "react";
import {
  INDICATOR_DERIVATIVE_BLOCKS,
  INDICATOR_FIELD_BLOCKS,
  INDICATOR_FUNCTION_BLOCKS,
  INDICATOR_OPERATOR_BLOCKS,
} from "../lib/indicator.js";

function BlockGroup({ title, items, onAddToken }) {
  return (
    <section className="indicator-group">
      <h3 className="indicator-group-title">{title}</h3>
      <div className="indicator-block-grid">
        {items.map((item) => (
          <button
            key={`${title}-${item.token}`}
            type="button"
            className="indicator-block tap-scale"
            onClick={() => onAddToken(item.token)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </section>
  );
}

export default function IndicatorPanel({
  open,
  onClose,
  name,
  tokens,
  formula,
  error,
  previewValue,
  isActive,
  onNameChange,
  onAddToken,
  onAddConstant,
  onRemoveToken,
  onRemoveLastToken,
  onReset,
  onApply,
}) {
  const [constantValue, setConstantValue] = useState("");

  useEffect(() => {
    if (!open) {
      setConstantValue("");
    }
  }, [open]);

  if (!open) return null;

  return (
    <div className="sheet-overlay" role="presentation" onClick={onClose}>
      <div
        className="sheet-panel indicator-sheet"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sheet-handle" />
        <div className="indicator-sheet-head">
          <div>
            <h2 className="sheet-title">Свой индикатор</h2>
            <p className="section-hint">
              Соберите формулу из блоков. Доступны метрики, арифметика, функции и
              численные производные.
            </p>
          </div>
          {isActive && <span className="indicator-live-badge">Активен</span>}
        </div>

        <label className="field-label" htmlFor="indicator-name">
          Название индикатора
        </label>
        <input
          id="indicator-name"
          type="text"
          className="text-input"
          placeholder="Например, Доходность / Риск"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
        />

        <label className="field-label">Конструктор</label>
        <div className="indicator-canvas" aria-live="polite">
          {tokens.length === 0 && (
            <p className="muted indicator-empty">
              Формула пока пустая. Добавьте блоки ниже.
            </p>
          )}
          {tokens.map((token, index) => (
            <button
              key={`${token}-${index}`}
              type="button"
              className="indicator-token"
              onClick={() => onRemoveToken(index)}
              title="Убрать блок"
            >
              {token}
            </button>
          ))}
        </div>

        <div className="indicator-helpers">
          <div className="indicator-constant-row">
            <input
              type="number"
              className="text-input"
              placeholder="Добавить число"
              value={constantValue}
              onChange={(event) => setConstantValue(event.target.value)}
            />
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                onAddConstant(constantValue);
                setConstantValue("");
              }}
            >
              Добавить число
            </button>
          </div>
          <div className="indicator-helper-actions">
            <button type="button" className="btn-linky" onClick={onRemoveLastToken}>
              Удалить последний
            </button>
            <button type="button" className="btn-linky" onClick={onReset}>
              Очистить все
            </button>
          </div>
        </div>

        <div className="indicator-preview">
          <span className="muted">Формула</span>
          <code className="indicator-formula">{formula || "—"}</code>
          <span className="muted">
            Пробный результат:{" "}
            {Number.isFinite(previewValue) ? previewValue.toFixed(4) : "не вычисляется"}
          </span>
        </div>

        {error && <p className="error-inline">{error}</p>}

        <BlockGroup title="Метрики" items={INDICATOR_FIELD_BLOCKS} onAddToken={onAddToken} />
        <BlockGroup title="Операции" items={INDICATOR_OPERATOR_BLOCKS} onAddToken={onAddToken} />
        <BlockGroup title="Функции" items={INDICATOR_FUNCTION_BLOCKS} onAddToken={onAddToken} />
        <BlockGroup
          title="Производные"
          items={INDICATOR_DERIVATIVE_BLOCKS}
          onAddToken={onAddToken}
        />

        <div className="sheet-actions">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Закрыть
          </button>
          <button type="button" className="btn-primary" onClick={onApply}>
            Сохранить и сортировать
          </button>
        </div>
      </div>
    </div>
  );
}
