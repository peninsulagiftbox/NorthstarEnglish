'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { request } from '@/lib/api/catalog';
import { Button, Card, EmptyState, Message } from '@/components/ui/Primitives';
type Source = { id: string; attemptId: string; lessonId: string; versionId: string; sentenceId: string; sequence: number; standardText: string; rawText: string; reason: string };
export function ReviewSources() {
  const [rows, setRows] = useState<Source[] | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; request<Source[]>('/reviews/items').then(data => { if (active) { setRows(data); setError(''); } }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, [retry]);
  if (error) return <Message error>{error} <Button onClick={() => { setError(''); setRows(null); setRetry(n => n + 1); }}>重新加载</Button></Message>;
  if (!rows) return <Message>正在读取真实复习来源…</Message>;
  if (!rows.length) return <Card><EmptyState title="暂无待复习来源"><p>听写中的错误会留下来源；草稿、浏览、播放与跳过不会生成复习记录。</p><Link className="button" href="/lesson/demo-01?tab=dictation">开始精听听写 →</Link></EmptyState></Card>;
  const ids = [...new Set(rows.map(row => row.id))];
  return <><p>{ids.length} 个待复习句子 · {rows.length} 条真实错误来源。翻卡、自评和调度将在 Phase 07 开放。</p>{ids.map(id => <Card key={id} className="review-source"><h2>第 {rows.find(row => row.id === id)!.sequence} 句 · 听写差异 · {rows.find(row => row.id === id)!.versionId}</h2>{rows.filter(row => row.id === id).map(row => <div key={row.attemptId}><p>你的原文：{row.rawText}</p><p lang="en">标准写法：{row.standardText}</p><small>来源：{row.lessonId} / {row.versionId} / {row.sentenceId} / {row.attemptId}</small><p><Link className="button" href={`/lesson/${row.lessonId}?version=${row.versionId}&tab=dictation&sentence=${row.sentenceId}`}>回到源句重练 →</Link></p></div>)}</Card>)}</>;
}
