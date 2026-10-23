'use client';
import { useEffect, useId, useRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'secondary' | 'primary' | 'danger' };
export function Button({ className = '', variant = 'secondary', type = 'button', ...props }: ButtonProps) { return <button type={type} className={`button ${variant === 'secondary' ? '' : variant} ${className}`} {...props} />; }
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`surface ${className}`}>{children}</section>; }
export function Message({ children, error = false }: { children: ReactNode; error?: boolean }) { return <p role={error ? 'alert' : 'status'} className={`message ${error ? 'error' : ''}`}>{children}</p>; }
export function EmptyState({ title, children }: { title: string; children: ReactNode }) { return <div className="empty-state"><span className="empty-icon" aria-hidden="true">◇</span><h2>{title}</h2><div className="muted">{children}</div></div>; }
export function Toast({ children }: { children: ReactNode }) { return <div className="toast" role="status">{children}</div>; }
export function Modal({ title, onClose, children, drawer = false, actions, tone = 'default', dismissible = true }: {
  title: string; onClose: () => void; children: ReactNode; drawer?: boolean; actions?: ReactNode; tone?: 'default' | 'danger'; dismissible?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null), titleId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    ref.current?.showModal();
    ref.current?.querySelector<HTMLElement>('[data-modal-initial-focus]')?.focus({ preventScroll: true });
    return () => { if (previous?.isConnected) previous.focus({ preventScroll: true }); };
  }, []);
  return <dialog className={`modal ${drawer ? 'drawer' : ''}`} ref={ref} aria-labelledby={titleId} onKeyDown={e => {
    if (e.key !== 'Tab') return;
    const items = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]')).filter(node => node.getClientRects().length);
    const first = items[0], last = items.at(-1);
    if (!first) { e.preventDefault(); return; }
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }} onCancel={e => { e.preventDefault(); if (dismissible) onClose(); }} onClick={e => {
    if (e.target !== e.currentTarget || !dismissible) return;
    const rect = e.currentTarget.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientX > rect.right || e.clientY < rect.top || e.clientY > rect.bottom) onClose();
  }}>
    <header className="modal-header"><span className={`modal-symbol ${tone}`} aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">{tone === 'danger' ? <><path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 10v7M14 10v7" /></> : <><circle cx="12" cy="12" r="9" /><path d="M12 10v7M12 6v2" /></>}</svg></span><h2 id={titleId}>{title}</h2><Button className="modal-close" aria-label="关闭弹窗" disabled={!dismissible} onClick={onClose}><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m6 6 12 12M18 6 6 18" /></svg></Button></header>
    <div className="modal-body">{children}</div>
    {actions && <footer className="modal-actions">{actions}</footer>}
  </dialog>;
}
