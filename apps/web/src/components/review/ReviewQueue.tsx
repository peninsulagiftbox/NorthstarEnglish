'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { request } from '@/lib/api/catalog';
import { ApiError } from '@/lib/api/client';
import { enqueue, deliver, pendingCommand, type Command } from '@/lib/persistence/outbox';
import { remove } from '@/lib/persistence/db';
import { formatBeijingTime, utcTimestamp } from '@/lib/formatTime';
import { Button, Card, EmptyState, Message } from '@/components/ui/Primitives';

type Answer = { text: string; explanation: string; attempts: { attemptId: string; rawText: string; recordedAt: string }[] };
type ReviewItem = { id: string; lessonId: string; versionId: string; sentenceId: string; sequence: number; lessonTitle: string; prompt: string; cardKind: string; knowledgePointId?: string; dueAt: string; rowVersion: number; due: boolean; reps: number; sources: { attemptId: string; exerciseId: string; reason: string; recordedAt: string }[]; history: { eventId: string; rating: string; origin: string; nextDueAt: string; recordedAt: string }[] };
function ReviewCard({ item, reload }: { item: ReviewItem; reload: () => Promise<void> }) {
  const key = `northstar:review:${item.id}`;
  const [answer, setAnswer] = useState<Answer | null>(null), [pending, setPending] = useState<Command | null>(null), [busy, setBusy] = useState(false), [ready, setReady] = useState(false), [error, setError] = useState(''), [conflict, setConflict] = useState(false);
  const lock = useRef(false), alive = useRef(true);
  useEffect(() => { alive.current = true; let active = true; pendingCommand(key).then(command => { if (active) { setPending(command ?? null); setReady(true); } }).catch(() => { if (active) setError('无法读取本机待确认操作，请恢复存储后刷新。'); }); return () => { active = false; alive.current = false; }; }, [key]);
  const due = !!item.due;
  async function reveal() {
    if (lock.current || !ready || pending) return;
    lock.current = true; setBusy(true); setError('');
    try { const value = await request<Answer>(`/reviews/${item.id}/answer`); if (alive.current) setAnswer(value); }
    catch (e) { if (alive.current) setError(e instanceof Error ? e.message : '翻卡失败'); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function rate(rating?: string) {
    if (lock.current || !ready || (!pending && !answer)) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const command = pending ?? await enqueue(key, `/reviews/${item.id}/results`, { lessonId: item.lessonId, versionId: item.versionId, sentenceId: item.sentenceId, rowVersion: item.rowVersion, rating, answerRevealed: true });
      setPending(command); await deliver(key, command); if (!alive.current) return;
      setPending(null); setAnswer(null); await reload();
    } catch (e) { if (alive.current) { setError(e instanceof Error ? e.message : '自评保存失败'); if (e instanceof ApiError && e.status === 409) setConflict(true); } }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function resolveConflict() {
    if (lock.current || !pending) return;
    lock.current = true; setBusy(true);
    try { await remove('outbox', key, pending.eventId); setPending(null); setConflict(false); setAnswer(null); await reload(); }
    catch { setError('重新读取失败，请重试。'); } finally { lock.current = false; setBusy(false); }
  }
  return <Card className="review-card"><p className="eyebrow">{item.cardKind === 'quiz_choice' ? '测验错题' : item.cardKind === 'reading_choice' ? '阅读证据' : '听写回忆'}</p><h2>{item.lessonTitle} · 第 {item.sequence} 句</h2><p>先根据中文回想英文，再翻卡核对。</p><p className="review-prompt">{item.prompt}</p><p className="muted">{due ? '已到期' : '尚未到期'} · 下次到期：<time dateTime={utcTimestamp(item.dueAt)}>{formatBeijingTime(item.dueAt)}</time>（北京时间）</p>
    {!answer ? <Button variant="primary" disabled={!ready || busy || !!pending || !due} onClick={() => void reveal()}>翻开答案</Button> : <div className="review-answer"><p lang="en">{answer.text}</p><p>{answer.explanation}</p><p>本地预置讲解 · 人工自评</p><details><summary>查看本卡错误原答</summary>{answer.attempts.map(a => <p key={a.attemptId}>{formatBeijingTime(a.recordedAt)} · <span lang="en">{a.rawText}</span></p>)}</details><div className="toolbar"><Button disabled={busy || !!pending} onClick={() => void rate('again')}>还不会 · 1 分钟后</Button><Button variant="primary" disabled={busy || !!pending} onClick={() => void rate('good')}>记住了 · 延后复习</Button></div></div>}
    {busy && <Message>正在保存或读取…</Message>}{error && <Message error>{error}</Message>}
    {pending && !busy && <Message>{conflict ? '此操作已被拒绝且未计数。' : '待确认操作保留原事件。'}<Button onClick={() => void (conflict ? resolveConflict() : rate())}>{conflict ? '读取最新卡片' : '重试原自评'}</Button></Message>}
    <p><Link className="button" href={`/lesson/${item.lessonId}?version=${item.versionId}&tab=${item.cardKind === 'quiz_choice' ? 'quiz' : item.cardKind === 'reading_choice' ? 'vocabulary' : 'dictation'}&sentence=${item.sentenceId}`}>回到第 {item.sequence} 句重练 →</Link></p>
    <details><summary>错误来源（{item.sources.length} 次）与复习历史（{item.history.length} 次）</summary><p>{item.versionId} · {item.sentenceId} · 知识点：{item.knowledgePointId ?? '听写词序与拼写'}</p>{item.sources.map(source => <p key={source.attemptId}>{formatBeijingTime(source.recordedAt)} · {source.reason}<br /><Link href={`/lesson/${item.lessonId}?version=${item.versionId}&tab=${item.cardKind === 'quiz_choice' ? 'quiz' : item.cardKind === 'reading_choice' ? 'vocabulary' : 'dictation'}&sentence=${item.sentenceId}&attempt=${source.attemptId}`}>查看这次错误：{source.attemptId}</Link></p>)}{item.history.map(h => <p key={h.eventId}>{formatBeijingTime(h.recordedAt)} · 人工自评：{h.rating === 'again' ? '还不会' : '记住了'} · 下次 {formatBeijingTime(h.nextDueAt)}</p>)}</details>
  </Card>;
}
export function ReviewQueue() {
  const [items, setItems] = useState<ReviewItem[] | null>(null), [all, setAll] = useState(false), [error, setError] = useState(''), [retry, setRetry] = useState(0);
    async function reload() { setRetry(n => n + 1); }
  useEffect(() => {
    let active = true;
    request<ReviewItem[]>('/reviews/due?all=true').then(async rows => { const pending = await Promise.all(rows.map(item => pendingCommand(`northstar:review:${item.id}`))); if (active) { setItems(rows.filter((item, i) => all || item.due || !!pending[i])); setError(''); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [all, retry]);
  return <><p className="boundary">简化调度 simple_v1：还不会 1 分钟；记住后按连续自评成功次数安排 1、2、4、8、16、32 天（上限）。人工自评不代表客观掌握，跳过不增加成功次数。</p><div className="toolbar review-queue-actions"><Button aria-pressed={!all} onClick={() => { setItems(null); setAll(false); void reload(); }}>到期复习</Button><Button aria-pressed={all} onClick={() => { setItems(null); setAll(true); void reload(); }}>全部复习计划</Button><Button onClick={() => void reload()}>刷新队列</Button></div>
    {error && <Message error>{error}<Button onClick={() => void reload()}>重新加载</Button></Message>}
    {!items && !error && <Message>正在读取真实复习计划…</Message>}
    {items && !items.length && !error && <Card><EmptyState title={all ? '还没有复习任务' : '当前没有到期卡片'}><p>测验、听写或阅读中的真实错误会进入复习。可查看全部计划或到期后刷新。</p><Link className="button" href="/lesson/demo-01?tab=quiz">返回课时测验 →</Link></EmptyState></Card>}
    {!error && items?.map(item => <ReviewCard key={`${item.id}:${item.rowVersion}`} item={item} reload={reload} />)}</>;
}
