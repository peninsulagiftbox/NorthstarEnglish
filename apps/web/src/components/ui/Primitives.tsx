'use client';
import { useEffect, useRef } from 'react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';
export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) { return <button className={`button ${className}`} {...props} />; }
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`surface ${className}`}>{children}</section>; }
export function Message({ children, error = false }: { children: ReactNode; error?: boolean }) { return <p role={error ? 'alert' : 'status'} className={`message ${error ? 'error' : ''}`}>{children}</p>; }
export function EmptyState({ title, children }: { title: string; children: ReactNode }) { return <div className="empty-state"><span className="empty-icon" aria-hidden="true">◇</span><h2>{title}</h2><div className="muted">{children}</div></div>; }
export function Toast({ children }: { children: ReactNode }) { return <div className="toast" role="status">{children}</div>; }
export function Modal({ title, onClose, children, drawer = false }: { title: string; onClose: () => void; children: ReactNode; drawer?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const previous = document.activeElement as HTMLElement | null; ref.current?.showModal(); return () => previous?.focus(); }, []);
  return <dialog className={drawer ? 'drawer' : undefined} ref={ref} aria-labelledby="dialog-title" onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}><div className="section-heading"><h2 id="dialog-title">{title}</h2><Button onClick={onClose}>关闭</Button></div>{children}</dialog>;
}
