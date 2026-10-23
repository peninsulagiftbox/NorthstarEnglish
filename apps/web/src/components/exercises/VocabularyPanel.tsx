'use client';
import { useEffect, useRef, useState } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { isBlind } from '@/lib/state/context';
import { request } from '@/lib/api/catalog';
import { getReading } from '@/lib/api/reading';
import type { ReadingData, Vocabulary } from '@/lib/api/reading';
import { commandHeaders } from '@/lib/persistence/outbox';
import { Button, EmptyState, Message } from '@/components/ui/Primitives';
import { EvidenceLink } from '@/components/lesson/EvidenceLink';
import { ReadingQuestion } from './ReadingQuestion';

export function VocabularyPanel() {
  const { lesson, checkpoint, update } = useLesson();
  const [data, setData] = useState<ReadingData | null>(null), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState(''), [saving, setSaving] = useState<Set<string>>(() => new Set()), [saveErrors, setSaveErrors] = useState<Record<string, string>>({});
  const source = useRef<HTMLDivElement>(null), saveLocks = useRef(new Set<string>());
  useEffect(() => {
    let active = true;
    getReading(lesson.id, lesson.versionId).then(value => { if (active) { setData(value); setError(''); } }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [lesson.id, lesson.versionId, retry]);
  const reload = async () => { setData(await getReading(lesson.id, lesson.versionId)); };
  async function favorite(word: Vocabulary) {
    if (saveLocks.current.has(word.id) || saveErrors[word.id]) return;
    saveLocks.current.add(word.id); setSaving(new Set(saveLocks.current));
    try {
      const saved = await request<{ favorite: boolean }>(`/knowledge/${word.id}/favorite`, { method: 'PUT', headers: commandHeaders, body: JSON.stringify({ lessonId: lesson.id, versionId: lesson.versionId, favorite: !word.favorite }) });
      setData(old => old ? { ...old, vocabulary: old.vocabulary.map(w => w.id === word.id ? { ...w, favorite: saved.favorite } : w) } : old);
    } catch (e) { setSaveErrors(old => ({ ...old, [word.id]: `${word.term}：${e instanceof Error ? e.message : '收藏保存失败'}；请重新读取确认状态后再操作。` })); }
    finally { saveLocks.current.delete(word.id); setSaving(new Set(saveLocks.current)); }
  }
  if (isBlind(checkpoint)) return <Message>精读包含原文和语境释义。<Button onClick={() => update({ showEnglish: true })}>显示英文并开始精读</Button></Message>;
  if (error) return <Message error>{error}<Button onClick={() => { setError(''); setData(null); setRetry(n => n + 1); }}>重新读取精读</Button></Message>;
  if (!data) return <Message>正在读取本课词条、收藏和阅读记录…</Message>;
  if (!data.vocabulary.length) return <EmptyState title="本版本暂无词条"><p>没有生成练习完成记录。</p></EmptyState>;
  const sentence = lesson.sentences.find(s => s.id === checkpoint.sentenceId)!;
  const word = data.vocabulary.find(w => w.id === selected && w.sentenceId === sentence.id);
  return <div className="vocabulary-panel"><p className="muted">本课语境词条 · 本地预置讲解。收藏单独保存，不标记掌握。</p>
    {!!Object.keys(saveErrors).length && <Message error>{Object.values(saveErrors).join(' ')}<Button disabled={saving.size > 0} onClick={() => { setSaveErrors({}); setData(null); setRetry(n => n + 1); }}>重新读取收藏</Button></Message>}
    <div className="vocabulary-grid">{data.vocabulary.map(item => <article className={`vocabulary-card ${item.id === selected ? 'selected' : ''}`} key={item.id}><button className="vocabulary-select" aria-pressed={item.id === selected} onClick={() => { setSelected(item.id); update({ sentenceId: item.sentenceId }); requestAnimationFrame(() => { source.current?.focus(); source.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }); }}><strong lang="en">{item.term}</strong><span>{item.meaning}</span><small>{item.usageNote}</small><span lang="en">{item.example}</span><small>定位原句 · 第 {item.sequence} 句</small></button><Button className="vocabulary-favorite" title={item.favorite ? `取消收藏 ${item.term}` : `收藏 ${item.term}`} disabled={saving.has(item.id) || !!saveErrors[item.id]} aria-busy={saving.has(item.id)} aria-label={`收藏 ${item.term}`} aria-pressed={!!item.favorite} onClick={() => void favorite(item)}><span aria-hidden="true">{item.favorite ? '★' : '☆'}</span></Button></article>)}</div>
    <div className="vocabulary-source" ref={source} tabIndex={-1}><h3>当前句语境 · 第 {sentence.sequence} 句</h3><p lang="en">{word && sentence.text.includes(word.term) ? <>{sentence.text.slice(0, sentence.text.indexOf(word.term))}<mark>{word.term}</mark>{sentence.text.slice(sentence.text.indexOf(word.term) + word.term.length)}</> : <mark>{sentence.text}</mark>}</p>{checkpoint.showTranslation && <p>{sentence.translation}</p>}<EvidenceLink sentenceId={sentence.id} /></div>
    {!data.questions.length ? <EmptyState title="本版本暂无阅读题"><p>当前仅可浏览词条。</p></EmptyState> : data.questions.map(question => <ReadingQuestion key={question.id} question={question} reload={reload} />)}
  </div>;
}
