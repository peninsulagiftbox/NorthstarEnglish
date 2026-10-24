'use client';
import { useEffect, useRef, useState } from 'react';
import { shuffleChoices } from '@/lib/shuffle';
import { Button, Message } from '@/components/ui/Primitives';
import { EvidenceLink } from '@/components/lesson/EvidenceLink';
import { useLesson } from '@/lib/state/LessonProvider';
import { enqueue, deliver, pendingCommand } from '@/lib/persistence/outbox';
import type { Command } from '@/lib/persistence/outbox';
import type { ReadingQuestionData, ReadingResult } from '@/lib/api/reading';

export function ReadingQuestion({ question, reload }: { question: ReadingQuestionData; reload: () => Promise<void> }) {
  const { lesson, update } = useLesson();
  const key = `northstar:reading:${lesson.versionId}:${question.id}`;
  const [options, setOptions] = useState(() => shuffleChoices(question.options));
  const [selected, setSelected] = useState(''), [pending, setPending] = useState<Command | null>(null);
  const [ready, setReady] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('');
  const [result, setResult] = useState<ReadingResult | null>(null);
  const lock = useRef(false), alive = useRef(true), feedback = useRef<HTMLDivElement>(null);
  useEffect(() => {
    alive.current = true;
    let active = true;
    pendingCommand(key).then(command => { if (active) { setPending(command ?? null); if (typeof command?.body.optionId === 'string') setSelected(command.body.optionId); setReady(true); } }).catch(() => { if (active) setError('无法读取本机待提交记录，请恢复浏览器存储后刷新，避免重复提交。'); });
    return () => { active = false; alive.current = false; };
  }, [key]);
  async function send(action?: string, retry = false) {
    if (lock.current || !ready || (pending && !retry)) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const command = pending ?? await enqueue(key, `/reading/${question.id}/${action ? 'events' : 'attempts'}`, { lessonId: lesson.id, versionId: lesson.versionId, ...(action ? { action } : { optionId: selected }) });
      setPending(command);
      const saved = await deliver<{ result?: ReadingResult }>(key, command);
      if (!alive.current) return;
      setPending(null);
      if (saved.result) {
        setResult(saved.result);
        setSelected(''); setOptions(shuffleChoices(question.options));
        update({ sentenceId: saved.result.sentenceId, showEnglish: true });
        // Focus the feedback containing the actual source sentence after rendering.
        requestAnimationFrame(() => { feedback.current?.focus(); feedback.current?.scrollIntoView({ block: 'center', behavior: 'smooth' }); });
      }
      await reload();
    } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : '保存失败，请重试。'); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const stateNames: Record<string, string> = { not_started: '未开始', in_progress: '正在尝试', practiced: '已有真实作答', skipped: '本轮已跳过', paused: '本轮已暂停' };
  return <section className="reading-question" aria-busy={busy} aria-labelledby="reading-heading"><h3 id="reading-heading">阅读理解 · 用原句找证据</h3>
    <p role="status">{stateNames[question.state] ?? question.state} · 累计真实作答 {question.history.length} 次</p>
    <fieldset disabled={!ready} aria-disabled={busy || !!pending}><legend lang="en">{question.prompt}</legend>{options.map(option => <label className="reading-option" key={option.id}><input type="radio" name={question.id} value={option.id} checked={selected === option.id} aria-disabled={busy || !!pending} onClick={event => { if (lock.current || pending) event.preventDefault(); }} onChange={() => { if (lock.current || pending) return; setSelected(option.id); setResult(null); if (question.state !== 'in_progress') void send('start'); }} /><span lang="en">{option.text}</span></label>)}</fieldset>
    <div className="toolbar"><Button className="primary" disabled={!ready || !selected} aria-disabled={busy || !!pending} onClick={() => void send()}>提交阅读答案</Button><Button disabled={!ready} aria-disabled={busy || !!pending} onClick={() => void send('start')}>开始 / 恢复</Button><Button disabled={!ready} aria-disabled={busy || !!pending} onClick={() => void send('pause')}>暂停本轮</Button><Button disabled={!ready} aria-disabled={busy || !!pending} onClick={() => void send('skip')}>跳过本轮</Button></div>
    <p className="reading-save-status" role="status">{busy ? '正在保存，请稍候…' : '\u00a0'}</p>
    {error && <Message error>{error}</Message>}
    {pending && !busy && <Message>保留了一次待确认提交；重试会沿用原事件，不新建作答。<Button onClick={() => void send(undefined, true)}>重试原提交</Button></Message>}
    {result && <div className="reading-feedback" ref={feedback} tabIndex={-1} role="status"><h4>{result.correct ? '回答正确' : '本次答错 · 已加入复习来源'}</h4><p>正确选项：<span lang="en">{result.correctText}</span></p><p>第 6 句证据：<mark lang="en">{result.standardText}</mark></p><p>{result.explanation}</p><EvidenceLink sentenceId={result.sentenceId} /></div>}
    <details className="reading-history"><summary>答题历史（{question.history.length} 次）</summary>{!question.history.length ? <p>还没有正式作答。浏览、收藏、暂停或跳过都不计练习完成。</p> : <ol>{question.history.map((item, index) => { const saved = JSON.parse(item.resultJson) as ReadingResult; return <li key={item.attemptId}><p>{index === question.history.length - 1 ? '首次作答' : '重做'} · {new Date(item.recordedAt).toLocaleString('zh-CN')} · {item.correct ? '正确' : '错误'}</p><p lang="en">你的选择：{question.options.find(o => o.id === item.optionId)?.text}</p><p>第 6 句证据：{saved.standardText}</p><EvidenceLink sentenceId={saved.sentenceId} /></li>; })}</ol>}</details>
    <p className="boundary">答错也是真实练习；收藏和正确一次均不代表已掌握。可继续浏览或跳过本轮，历史作答会保留。</p>
  </section>;
}
