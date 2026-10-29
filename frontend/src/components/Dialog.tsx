import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

type DialogProps = { title: string; eyebrow?: string; onClose: () => void; children: React.ReactNode; size?: 'standard' | 'wide' };

export function Dialog({ title, eyebrow, onClose, children, size = 'standard' }: DialogProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLElement>(null);
  const scrimRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const scrim = scrimRef.current;
    const background = Array.from(scrim?.parentElement?.children ?? []).filter((element) => element !== scrim) as HTMLElement[];
    const priorInertStates = background.map((element) => element.inert);
    background.forEach((element) => { element.inert = true; });
    const previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { onCloseRef.current(); return; }
      if (event.key !== 'Tab') return;
      const focusable = dialogRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])');
      if (!focusable?.length) { event.preventDefault(); return; }
      const first = focusable[0]; const last = focusable[focusable.length - 1]; const active = document.activeElement;
      if (event.shiftKey && (active === first || !dialogRef.current?.contains(active))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (active === last || !dialogRef.current?.contains(active))) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      background.forEach((element, index) => { element.inert = priorInertStates[index]; });
      document.body.style.overflow = previousBodyOverflow;
      if (previousFocusRef.current?.isConnected) previousFocusRef.current.focus();
    };
  }, []);

  return (
    <div ref={scrimRef} className="dialog-scrim" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section ref={dialogRef} className={`dialog dialog--${size}`} role="dialog" aria-modal="true" aria-labelledby="dialog-title">
        <header className="dialog-head">
          <div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2 id="dialog-title">{title}</h2></div>
          <button ref={closeRef} className="icon-button" type="button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button>
        </header>
        {children}
      </section>
    </div>
  );
}
