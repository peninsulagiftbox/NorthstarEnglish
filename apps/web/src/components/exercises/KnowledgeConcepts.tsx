'use client';
import { useEffect, useState } from 'react';
import { Button, Message } from '@/components/ui/Primitives';
import { getKnowledgeConcepts, getKnowledgeOccurrences, knowledgeKindName } from '@/lib/api/knowledge';
import type { KnowledgeConcept, KnowledgeOccurrence } from '@/lib/api/knowledge';

function OccurrenceList({ concept }: { concept: KnowledgeConcept }) {
  const [items, setItems] = useState<KnowledgeOccurrence[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async (after?: string) => {
    setBusy(true); setError('');
    try {
      const page = await getKnowledgeOccurrences(concept.id, after);
      setItems(old => after && old ? [...old, ...page.items] : page.items);
    } catch (e) { setError(e instanceof Error ? e.message : '读取知识出现位置失败'); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    let active = true;
    getKnowledgeOccurrences(concept.id).then(page => { if (active) { setItems(page.items); setError(''); } })
      .catch(e => { if (active) { setItems([]); setError(e instanceof Error ? e.message : '读取知识出现位置失败'); } });
    return () => { active = false; };
  }, [concept.id]);
  if (!items) return <p className="muted">正在读取出现位置…</p>;
  if (error) return <Message error>{error}<Button onClick={() => void load()}>重试</Button></Message>;
  if (!items.length) return <p className="muted">暂无可见出现位置。</p>;
  return <ul className="knowledge-occurrences">{items.map(item => <li key={item.id}>
    {item.restricted
      ? <span className="muted">受限来源 · 课程或版本当前不可查看。</span>
      : <>{item.title ?? item.lessonId}{item.sequence ? ` · 第 ${item.sequence} 句` : item.scope === 'paragraph' ? ' · 段落出现' : ' · 课程级出现'}{item.wrongAttemptCount ? ` · 错答 ${item.wrongAttemptCount} 次` : ''}{item.sentenceText ? <span lang="en">：{item.sentenceText}</span> : null}</>}
  </li>)}</ul>;
}

export function KnowledgeConcepts({ lessonId, versionId }: { lessonId: string; versionId: string }) {
  const [concepts, setConcepts] = useState<KnowledgeConcept[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const load = async (after?: string) => {
    setBusy(true); setError('');
    try {
      const page = await getKnowledgeConcepts(lessonId, versionId, after);
      setConcepts(old => after ? [...old, ...page.items] : page.items);
      setCursor(page.nextCursor);
    } catch (e) { setError(e instanceof Error ? e.message : '读取跨课知识失败'); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    let active = true;
    getKnowledgeConcepts(lessonId, versionId).then(page => { if (active) { setConcepts(page.items); setCursor(page.nextCursor); setError(''); } })
      .catch(e => { if (active) { setConcepts([]); setError(e instanceof Error ? e.message : '读取跨课知识失败'); } });
    return () => { active = false; };
  }, [lessonId, versionId]);
  if (!concepts) return <p className="muted">正在读取跨课知识概念…</p>;
  if (error) return <Message error>{error}<Button onClick={() => { setConcepts([]); setCursor(undefined); void load(); }}>重新读取知识概念</Button></Message>;
  if (!concepts.length) return null;
  return <section className="knowledge-concepts" aria-label="跨课知识概念">
    <h3>跨课知识概念 · 已人工审校</h3>
    <ul>{concepts.map(concept => <li key={concept.id}>
      <button className="knowledge-concept" aria-expanded={open === concept.id} onClick={() => setOpen(old => old === concept.id ? null : concept.id)}>
        <strong lang="en">{concept.displayName}</strong>
        <span>{knowledgeKindName(concept.kind)} · {concept.lessonCount} 门课出现</span>
      </button>
      {open === concept.id && <OccurrenceList concept={concept} />}
    </li>)}</ul>
    {cursor && <Button disabled={busy} onClick={() => void load(cursor)}>加载更多概念</Button>}
  </section>;
}
