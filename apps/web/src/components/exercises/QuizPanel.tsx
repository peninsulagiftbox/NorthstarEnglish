'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useLesson } from '@/lib/state/LessonProvider';
import { request } from '@/lib/api/catalog';
import { read, write, remove } from '@/lib/persistence/db';
import { enqueue, deliver, pendingCommand, type Command } from '@/lib/persistence/outbox';
import { shuffleChoices } from '@/lib/shuffle';
import { formatBeijingTime } from '@/lib/formatTime';
import { Button, EmptyState, Message } from '@/components/ui/Primitives';

type Question = { id: string; prompt: string; options: { id: string; text: string }[] };
type Answer = { exerciseId: string; sentenceId: string; optionId: string; correct: boolean; explanation: string; answerKey: string };
type History = { id: string; correctCount: number; submittedAt: string; answers: { attemptId: string; resultJson: string }[] };
type Quiz = { questions: Question[]; state: string; history: History[] };
const states: Record<string, string> = { not_started: '未开始', in_progress: '正在尝试', practiced: '已有完整交卷', skipped: '本轮已跳过', paused: '本轮已暂停' };
export function QuizPanel() {
  const sourceAttempt = useSearchParams().get('attempt');
  const { lesson } = useLesson(), key = `northstar:quiz:${lesson.versionId}`;
  const [data, setData] = useState<Quiz | null>(null), [answers, setAnswers] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Command | null>(null), [busy, setBusy] = useState(false), [ready, setReady] = useState(false), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ correctCount: number; answers: Answer[] } | null>(null);
  const lock = useRef(false), alive = useRef(true);
  useEffect(() => {
    alive.current = true; let active = true;
    Promise.all([request<Quiz>(`/quiz?lessonId=${lesson.id}&versionId=${lesson.versionId}`), read<Record<string, string>>('drafts', key), pendingCommand(key)]).then(([quiz, draft, command]) => {
      if (!active) return;
      setData({ ...quiz, questions: quiz.questions.map(q => ({ ...q, options: shuffleChoices(q.options) })) }); setAnswers(draft ?? {}); setPending(command ?? null); setReady(true); setError('');
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; alive.current = false; };
  }, [key, lesson.id, lesson.versionId, retry]);
  async function select(id: string, option: string) {
    if (lock.current || pending || !ready) return;
    lock.current = true;
    try { const next = { ...answers, [id]: option }; setAnswers(next); setResult(null); await write('drafts', key, next); }
    catch { if (alive.current) { setAnswers(answers); setError('无法保存本机草稿，选择尚未生效；请恢复存储后重试。'); } }
    finally { lock.current = false; }
  }
  async function send(action?: string, retryOriginal = false) {
    if (lock.current || !ready || (pending && !retryOriginal)) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const command = pending ?? await enqueue(key, action ? '/quiz/events' : '/quiz/attempts', { lessonId: lesson.id, versionId: lesson.versionId, ...(action ? { action } : { answers }) });
      setPending(command);
      const saved = await deliver<{ correctCount?: number; answers?: Answer[] }>(key, command);
      if (command.path === '/quiz/attempts') await remove('drafts', key);
      if (!alive.current) return;
      setPending(null);
      if (saved.answers) { setResult({ correctCount: saved.correctCount!, answers: saved.answers }); setAnswers({}); setData(old => old ? { ...old, questions: old.questions.map(q => ({ ...q, options: shuffleChoices(q.options) })) } : old); }
      const refreshed = await request<Quiz>(`/quiz?lessonId=${lesson.id}&versionId=${lesson.versionId}`);
      setData(old => ({ ...refreshed, questions: old?.questions ?? refreshed.questions.map(q => ({ ...q, options: shuffleChoices(q.options) })) }));
    } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : '交卷失败，保留原提交。'); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const feedback = (items: Answer[]) => <ol className="quiz-feedback">{items.map(item => <li key={item.exerciseId}><p>{item.correct ? '回答正确' : '回答错误 · 已加入复习来源'} · {item.explanation}</p><p>你的选择：{data?.questions.find(q => q.id === item.exerciseId)?.options.find(o => o.id === item.optionId)?.text}</p><p>正确选项：{data?.questions.find(q => q.id === item.exerciseId)?.options.find(o => o.id === item.answerKey)?.text}</p><Link className="button" href={`/lesson/${lesson.id}?version=${lesson.versionId}&tab=text&sentence=${item.sentenceId}`}>回到第 {Number(item.sentenceId.slice(-2))} 句重学 →</Link></li>)}</ol>;
  if (!data) return <Message error={!!error}>{error || '正在读取本课测验…'}{error && <Button onClick={() => setRetry(n => n + 1)}>重新加载</Button>}</Message>;
  if (!data.questions.length) return <EmptyState title="此版本暂无测验"><p>没有可提交的题目。</p></EmptyState>;
  return <section className="quiz-panel" aria-busy={busy}><h2>课时测验</h2><p className="boundary">3 道原创选择题 · 记录本课理解题的作答结果，不代表听说读写综合能力。</p><p role="status">{states[data.state]} · 完整交卷 {data.history.length} 轮 · 选项即时保存到本机草稿</p>
    <div className="toolbar"><Button disabled={!ready || busy || !!pending} onClick={() => void send('start')}>开始 / 恢复本轮</Button><Button disabled={!ready || busy || !!pending} onClick={() => void send('pause')}>暂停测验</Button><Button disabled={!ready || busy || !!pending} onClick={() => void send('skip')}>跳过测验</Button></div>
    {data.questions.map((q, i) => <fieldset className="quiz-question" key={q.id} disabled={!ready || busy || !!pending}><legend lang="en">{i + 1}. {q.prompt}</legend>{q.options.map(o => <label className="reading-option" key={o.id}><input type="radio" name={q.id} checked={answers[q.id] === o.id} onChange={() => void select(q.id, o.id)} /><span lang="en">{o.text}</span></label>)}</fieldset>)}
    <Button variant="primary" disabled={!ready || busy || !!pending || data.questions.some(q => !answers[q.id])} onClick={() => void send()}>提交本轮三题</Button>
    {busy && <Message>正在保存，请稍候…</Message>}{error && <Message error>{error}</Message>}
    {pending && !busy && <Message>原提交待确认，重试不会新增一轮。<Button onClick={() => void send(undefined, true)}>重试原提交</Button></Message>}
    {result && <div className="quiz-result" role="status"><h3>本轮结果：{result.correctCount} / 3 题正确</h3>{feedback(result.answers)}<div className="quiz-result-actions"><p>可重新选择三题再交卷，历史不会被覆盖。</p><Link className="button" href="/review">查看到期复习 →</Link></div></div>}
    <details className="quiz-history" open={!!sourceAttempt || undefined}><summary>交卷历史（{data.history.length} 轮）</summary>{!data.history.length ? <p>尚无正式交卷。草稿、暂停、跳过均不计完成。</p> : data.history.map((run, i) => <article key={run.id} className={run.answers.some(a => a.attemptId === sourceAttempt) ? 'quiz-source-attempt' : undefined}><h3>{i === data.history.length - 1 ? '首次交卷' : '重做'} · {run.correctCount} / 3</h3><p>{formatBeijingTime(run.submittedAt)}（北京时间）</p>{feedback(run.answers.map(a => JSON.parse(a.resultJson) as Answer))}</article>)}</details>
  </section>;
}
