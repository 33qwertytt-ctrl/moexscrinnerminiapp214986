import { useEffect, useId, useRef, useState } from "react";

export default function TooltipHelp({ label, text }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("click", onDoc, true);
    return () => document.removeEventListener("click", onDoc, true);
  }, [open]);

  return (
    <span className="tooltip-wrap" ref={wrapRef}>
      <button
        type="button"
        className="tooltip-trigger tap-scale"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        title={label}
      >
        ?
      </button>
      {open && (
        <div className="tooltip-pop" id={id} role="tooltip">
          {text}
        </div>
      )}
    </span>
  );
}
