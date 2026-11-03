'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ApiError } from '@/lib/api/client';
import { enqueue, deliver, pendingCommand, type Command } from '@/lib/persistence/outbox';
import { remove } from '@/lib/persistence/db';
import { formatBeijingTime, utcTimestamp } from '@/lib/formatTime';
import { knowledgeKindName, type KnowledgeKind } from '@/lib/api/knowledge';
import { getConceptReviewSources, type ConceptReviewCard, type ConceptReviewSource } from '@/lib/api/conceptReviews';
import { Button, Card, Message } from '@/components/ui/Primitives';

const kindTab = (kind?: string) => (kind === 'dictation' ? 'dictation' : kind === 'reading_choice' ? 'vocabulary' : 'quiz');

function SourceLine({ source }: { source: ConceptReviewSource }) {
  if (source.restricted) return <p>内容不可用（课程已撤回或无访问权限）· {formatBeijingTime(source.recordedAt)}</p>;
  return <p>
    {formatBeijingTime(source.recordedAt)} · {source.lessonTitle} · 第 {source.sequence} 句 · {source.correct ? '本次作答正确' : '本次作答错误'}
    <br />
    <Link href={`/lesson/${source.lessonId}?version=${source.versionId}&tab=${kindTab(source.exerciseKind)}&attempt=${source.attemptId}`}>查看这次练习：{source.attemptId}</Link>
  </p>;
}

export function ConceptReviewCardView({ item, reload }: { item: ConceptReviewCard; reload: () => Promise<void> }) {
  const key = `northstar:concept-review:${item.id}`;
  const [revealed, setRevealed] = useState(false), [pending, setPending] = useState<Command | null>(null), [busy, setBusy] = useState(false), [ready, setReady] = useState(false), [error, setError] = useState(''), [conflict, setConflict] = useState(false);
  const [sources, setSources] = useState<ConceptReviewSource[] | null>(null), [nextCursor, setNextCursor] = useState<string | null>(null);
  const [sourcesBusy, setSourcesBusy] = useState(false), [sourcesError, setSourcesError] = useState('');
  const lock = useRef(false), sourceLock = useRef(false), alive = useRef(true);
  const loadSources = useCallback(async (after?: string) => {
    if (sourceLock.current) return;
    sourceLock.current = true;
    setSourcesBusy(true); setSourcesError('');
    try {
      const page = await getConceptReviewSources(item.id, after);
      if (!alive.current) return;
      setSources(current => {
        if (!after) return page.items;
        const merged = new Map((current ?? []).map(source => [`${source.attemptId}:${source.occurrenceId}`, source]));
        for (const source of page.items) merged.set(`${source.attemptId}:${source.occurrenceId}`, source);
        return [...merged.values()];
      });
      setNextCursor(page.nextCursor);
    } catch (e) {
      if (alive.current) setSourcesError(e instanceof Error ? e.message : '来源读取失败');
    } finally {
      sourceLock.current = false;
      if (alive.current) setSourcesBusy(false);
    }
  }, [item.id]);
  useEffect(() => {
    alive.current = true; let active = true;
    pendingCommand(key).then(command => { if (active) { setPending(command ?? null); setReady(true); } }).catch(() => { if (active) setError('无法读取本机待确认操作，请恢复存储后刷新。'); });
    queueMicrotask(() => { void loadSources(); });
    return () => { active = false; alive.current = false; };
  }, [key, loadSources]);
  const due = !!item.due;
  async function rate(rating?: string) {
    if (lock.current || !ready || (!pending && !revealed)) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const command = pending ?? await enqueue(key, `/concept-reviews/${item.id}/results`, { rowVersion: item.rowVersion, rating, answerRevealed: true });
      setPending(command); await deliver(key, command); if (!alive.current) return;
      setPending(null); setRevealed(false); await reload();
    } catch (e) { if (alive.current) { setError(e instanceof Error ? e.message : '自评保存失败'); if (e instanceof ApiError && e.status === 409) setConflict(true); } }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function resolveConflict() {
    if (lock.current || !pending) return;
    lock.current = true; setBusy(true);
    try { await remove('outbox', key, pending.eventId); setPending(null); setConflict(false); setRevealed(false); await reload(); }
    catch { setError('重新读取失败，请重试。'); } finally { lock.current = false; setBusy(false); }
  }
  return <Card className="review-card">
    <p className="eyebrow">概念复习 · {knowledgeKindName(item.kind as KnowledgeKind)} · 义项 {item.senseKey}</p>
    <h2>{item.displayName}</h2>
    <p>先根据义项解释回忆这个词的用法，再翻卡核对。</p>
    <p className="review-prompt">{item.explanation}</p>
    <p className="muted">{due ? '已到期' : '尚未到期'} · 下次到期：<time dateTime={utcTimestamp(item.dueAt)}>{formatBeijingTime(item.dueAt)}</time>（北京时间）</p>
    {!revealed
      ? <Button variant="primary" disabled={!ready || busy || !!pending || !due} onClick={() => setRevealed(true)}>翻开答案</Button>
      : <div className="review-answer"><p lang="en">{item.canonicalKey}</p><p>本地预置讲解 · 人工自评</p>
          <div className="toolbar"><Button disabled={busy || !!pending} onClick={() => void rate('again')}>还不会 · 1 分钟后</Button>
          <Button variant="primary" disabled={busy || !!pending} onClick={() => void rate('good')}>记住了 · 延后复习</Button></div></div>}
    {busy && <Message>正在保存或读取…</Message>}{error && <Message error>{error}</Message>}
    {pending && !busy && <Message>{conflict ? '此操作已被拒绝且未计数。' : '待确认操作保留原事件。'}<Button onClick={() => void (conflict ? resolveConflict() : rate())}>{conflict ? '读取最新卡片' : '重试原自评'}</Button></Message>}
    <details><summary>学习来源（{sources ? `已显示 ${sources.filter(s => !s.restricted).length}/${item.visibleSourceCount} 条可见` : '正在读取来源'})</summary>
      {sourcesError && <Message error>{sourcesError}<Button disabled={sourcesBusy} onClick={() => void loadSources(nextCursor ?? undefined)}>重试读取来源</Button></Message>}
      {sourcesBusy && <Message>正在读取来源…</Message>}
      {sources && !sources.length && !nextCursor && <p>暂无可见来源。</p>}
      {sources?.map(source => <SourceLine key={`${source.attemptId}:${source.occurrenceId}`} source={source} />)}
      {nextCursor && !sourcesError && <Button disabled={sourcesBusy} onClick={() => void loadSources(nextCursor)}>加载更多来源</Button>}
    </details>
    <p className="muted">本次是复习自评，不代表客观测验成绩。</p>
  </Card>;
}
