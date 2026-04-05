import { useMemo, useState } from "react";

function formatApiError(rawText, status) {
  try {
    const parsed = JSON.parse(rawText);
    if (typeof parsed?.detail === "string") {
      return parsed.detail;
    }
  } catch {
    /* ignore invalid JSON */
  }
  return rawText || `Ошибка ${status}`;
}

export default function FeedbackPanel({
  maxAttachmentBytes,
  maxMessageChars,
  allowedMimeTypes,
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const initData = typeof window !== "undefined" ? window.Telegram?.WebApp?.initData || "" : "";
  const maxMb = maxAttachmentBytes ? (maxAttachmentBytes / (1024 * 1024)).toFixed(0) : "25";
  const acceptValue = useMemo(
    () => (Array.isArray(allowedMimeTypes) ? allowedMimeTypes.join(",") : ""),
    [allowedMimeTypes],
  );

  async function submitFeedback() {
    setStatus("");
    if (!initData) {
      setStatus("Откройте приложение из Telegram, чтобы отправить фидбек.");
      return;
    }
    if (!text.trim() && !file) {
      setStatus("Введите текст или прикрепите файл.");
      return;
    }
    setBusy(true);
    try {
      const formData = new FormData();
      formData.append("init_data", initData);
      formData.append("message", text.trim());
      if (file) formData.append("file", file);
      const response = await fetch("/api/feedback/submit", { method: "POST", body: formData });
      const rawText = await response.text();
      if (!response.ok) {
        setStatus(formatApiError(rawText, response.status));
        return;
      }
      setStatus("Отправлено. Спасибо!");
      setText("");
      setFile(null);
      setOpen(false);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button type="button" className="fab tap-scale" onClick={() => setOpen(true)} aria-label="Фидбек">
        💬
      </button>

      {open && (
        <div className="modal-overlay" onClick={() => !busy && setOpen(false)}>
          <div className="modal-sheet" onClick={(event) => event.stopPropagation()}>
            <div className="modal-handle" />
            <h2 className="modal-title">Фидбек</h2>
            <textarea
              className="text-area"
              rows={4}
              placeholder="Опишите проблему или идею..."
              value={text}
              maxLength={maxMessageChars || undefined}
              onChange={(event) => setText(event.target.value)}
            />
            {maxMessageChars ? (
              <p className="muted small feedback-counter">
                {text.length} / {maxMessageChars}
              </p>
            ) : null}
            <label className="file-row">
              <span className="btn-attach">📎 Прикрепить файл</span>
              <input
                type="file"
                className="visually-hidden"
                accept={acceptValue || undefined}
                onChange={(event) => setFile(event.target.files?.[0] || null)}
              />
              {file && <span className="file-name">{file.name}</span>}
            </label>
            <p className="muted small">Максимум ~{maxMb} МБ.</p>
            <button type="button" className="btn-primary" disabled={busy} onClick={() => void submitFeedback()}>
              {busy ? "Отправка..." : "Отправить"}
            </button>

            {status && <p className="status-msg">{status}</p>}
            <button type="button" className="btn-linky modal-close" onClick={() => setOpen(false)}>
              Закрыть
            </button>
          </div>
        </div>
      )}
    </>
  );
}
