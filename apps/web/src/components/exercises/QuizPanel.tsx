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

type Question = { id: string; prompt: string; options: { id: string; text: string }[]; ordinal: number; sequence: number; sentenceId: string };
type Answer = { exerciseId: string; sentenceId: string; optionId: string; correct: boolean; explanation: string; answerKey: string };
type RunAnswer = { exerciseId: string; sentenceId: string; attemptId: string; optionId: string; questionJson: string; correct: boolean; resultJson: string; sequence: number };
type Run = { id: string; correctCount: number; totalCount: number; submittedCount: number; setId: string; setHash: string; submittedAt: string; verified: boolean; contentAvailable: boolean; answers: RunAnswer[] };
type Quiz = { questions: Question[]; setId?: string; setHash?: string; protocolVersion?: string; totalCount: number; state: string; history: Run[] };
type Draft = { protocolVersion: 'quiz-submit-v2'; answers: Record<string, string> };
type Snapshot = { id: string; prompt: string; options: { id: string; text: string }[]; answerKey?: string; explanation?: string };
const states: Record<string, string> = { not_started: '未开始', in_progress: '正在尝试', practiced: '已有完整交卷', skipped: '本轮已跳过', paused: '本轮已暂停' };
const legacyKey = (versionId: string) => `northstar:quiz:${versionId}`;
const scopeKey = (lessonId: string, versionId: string, quiz: Quiz) => `northstar:quiz:v2:${lessonId}:${versionId}:${quiz.setId}:${quiz.setHash}`;
const legacyCompatible = (draft: Record<string, string>, questions: Question[]) => questions.every(q => draft[q.id] !== undefined && q.options.some(o => o.id === draft[q.id])) && Object.keys(draft).length === questions.length;
function exportLegacy(versionId: string, draft: Record<string, string>) {
  const url = URL.createObjectURL(new Blob([JSON.stringify({ scope: legacyKey(versionId), answers: draft }, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = `quiz-draft-${versionId}.json`; link.click(); URL.revokeObjectURL(url);
}
export function QuizPanel() {
  const sourceAttempt = useSearchParams().get('attempt');
  const { lesson } = useLesson();
  const [data, setData] = useState<Quiz | null>(null), [answers, setAnswers] = useState<Record<string, string>>({});
  const [pending, setPending] = useState<Command | null>(null), [legacyPending, setLegacyPending] = useState<Command | null>(null);
  const [legacyDraft, setLegacyDraft] = useState<Record<string, string> | null>(null), [incompatible, setIncompatible] = useState(false);
  const [busy, setBusy] = useState(false), [ready, setReady] = useState(false), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  const [result, setResult] = useState<{ correctCount: number; totalCount: number; answers: Answer[] } | null>(null);
  const lock = useRef(false), alive = useRef(true);
  useEffect(() => {
    alive.current = true; let active = true;
    setData(null); setAnswers({}); setResult(null); setPending(null); setLegacyPending(null); setLegacyDraft(null); setIncompatible(false); setReady(false);
    request<Quiz>(`/quiz?lessonId=${lesson.id}&versionId=${lesson.versionId}`).then(async quiz => {
      if (!active) return;
      setData({ ...quiz, questions: [...quiz.questions].sort((a, b) => a.ordinal - b.ordinal).map(q => ({ ...q, options: shuffleChoices(q.options) })) });
      const key = quiz.setId && quiz.setHash ? scopeKey(lesson.id, lesson.versionId, quiz) : null;
      const [draft, command, legacy, legacyCommand] = await Promise.all([
        key ? read<Draft>('drafts', key) : undefined, key ? pendingCommand(key) : undefined,
        read<Record<string, string>>('drafts', legacyKey(lesson.versionId)), pendingCommand(legacyKey(lesson.versionId)),
      ]);
      if (!active) return;
      if (legacyCommand) setLegacyPending(legacyCommand);
      else if (key && command) setPending(command);
      else if (key && draft?.protocolVersion === 'quiz-submit-v2') setAnswers(draft.answers);
      else if (legacy && quiz.questions.length && legacyCompatible(legacy, quiz.questions) && key) {
        setAnswers(legacy); await write('drafts', key, { protocolVersion: 'quiz-submit-v2', answers: legacy });
      } else if (legacy && Object.keys(legacy).length) { setLegacyDraft(legacy); setIncompatible(true); }
      if (active) { setReady(true); setError(''); }
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; alive.current = false; };
  }, [lesson.id, lesson.versionId, retry]);
  async function select(id: string, option: string) {
    if (lock.current || pending || legacyPending || !ready || !data?.setId || !data?.setHash) return;
    lock.current = true;
    const previous = answers;
    try {
      const next = { ...answers, [id]: option }; setAnswers(next); setResult(null);
      await write('drafts', scopeKey(lesson.id, lesson.versionId, data), { protocolVersion: 'quiz-submit-v2', answers: next });
    } catch { if (alive.current) { setAnswers(previous); setError('无法保存本机草稿，选择尚未生效；请恢复存储后重试。'); } }
    finally { lock.current = false; }
  }
  async function refresh() {
    const refreshed = await request<Quiz>(`/quiz?lessonId=${lesson.id}&versionId=${lesson.versionId}`);
    setData(old => ({ ...refreshed, questions: old?.questions ?? [...refreshed.questions].sort((a, b) => a.ordinal - b.ordinal).map(q => ({ ...q, options: shuffleChoices(q.options) })) }));
  }
  async function send(action?: string, retryOriginal = false) {
    if (lock.current || !ready || (pending && !retryOriginal)) return;
    if (!data?.setId || !data?.setHash) { setError('题集尚未加载完成，无法提交。'); return; }
    lock.current = true; setBusy(true); setError('');
    const key = scopeKey(lesson.id, lesson.versionId, data);
    try {
      const command = pending ?? await enqueue(key, action ? '/quiz/events' : `/quiz/sets/${data.setId}/attempts`,
        { lessonId: lesson.id, versionId: lesson.versionId, ...(action ? { action } : { protocolVersion: 'quiz-submit-v2', setId: data.setId, setHash: data.setHash, answers }) });
      setPending(command);
      const saved = await deliver<{ correctCount?: number; totalCount?: number; answers?: Answer[] }>(key, command);
      if (command.path.includes('/attempts')) await remove('drafts', key);
      if (!alive.current) return;
      setPending(null);
      if (saved.answers) {
        setResult({ correctCount: saved.correctCount!, totalCount: saved.totalCount ?? data.totalCount, answers: saved.answers }); setAnswers({});
        setData(old => old ? { ...old, questions: old.questions.map(q => ({ ...q, options: shuffleChoices(q.options) })) } : old);
      }
      await refresh();
    } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : '交卷失败，保留原提交。'); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  async function retryLegacy() {
    if (!legacyPending || lock.current) return;
    lock.current = true; setBusy(true); setError('');
    try {
      const saved = await deliver<{ correctCount?: number; totalCount?: number; answers?: Answer[] }>(legacyKey(lesson.versionId), legacyPending);
      if (legacyPending.path === '/quiz/attempts') await remove('drafts', legacyKey(lesson.versionId));
      if (!alive.current) return;
      setLegacyPending(null); setIncompatible(false);
      if (saved.answers) setResult({ correctCount: saved.correctCount!, totalCount: saved.totalCount ?? 3, answers: saved.answers });
      await refresh();
    } catch (e) { if (alive.current) setError(e instanceof Error ? e.message : '旧提交重试失败，原事件已保留。'); }
    finally { lock.current = false; if (alive.current) setBusy(false); }
  }
  const feedback = (items: Answer[]) => <ol className="quiz-feedback">{items.map(item => <li key={item.exerciseId}><p>{item.correct ? '回答正确' : '回答错误 · 已加入复习来源'}{item.explanation ? ` · ${item.explanation}` : ' · 暂无本地预置讲解'}</p><p>你的选择：{data?.questions.find(q => q.id === item.exerciseId)?.options.find(o => o.id === item.optionId)?.text}</p><p>正确选项：{data?.questions.find(q => q.id === item.exerciseId)?.options.find(o => o.id === item.answerKey)?.text}</p><Link className="button" href={`/lesson/${lesson.id}?version=${lesson.versionId}&tab=text&sentence=${item.sentenceId}`}>回到来源句重学 →</Link></li>)}</ol>;
  const runFeedback = (run: Run) => <ol className="quiz-feedback">{run.answers.map(item => {
    let frozen: Snapshot | null = null; try { frozen = JSON.parse(item.questionJson) as Snapshot; } catch {}
    let saved: Answer | null = null; try { saved = JSON.parse(item.resultJson) as Answer; } catch {}
    const sequence = Number.isInteger(item.sequence) && item.sequence > 0 ? `第 ${item.sequence} 句` : null;
    return <li key={item.exerciseId}><p>{item.correct ? '回答正确' : '回答错误'}{saved?.explanation ? ` · ${saved.explanation}` : ' · 暂无本地预置讲解'}</p><p>你的选择：{frozen?.options.find(o => o.id === item.optionId)?.text}</p>{frozen?.answerKey && <p>正确选项：{frozen.options.find(o => o.id === frozen.answerKey)?.text}</p>}<p>{sequence ? `来源：${sequence}` : '来源：本轮未保存来源句'}{frozen?.prompt ? ` · ${frozen.prompt}` : ''}</p><Link className="button" href={`/lesson/${lesson.id}?version=${lesson.versionId}&tab=text&sentence=${item.sentenceId}`}>{sequence ? `回到 ${sequence} 重学 →` : '返回来源句 →'}</Link></li>;
  })}</ol>;
  if (!data) return <Message error={!!error}>{error || '正在读取本课测验…'}{error && <Button onClick={() => setRetry(n => n + 1)}>重新加载</Button>}</Message>;
  if (!data.questions.length) return <EmptyState title="此版本暂无测验"><p>没有可提交的题目。</p></EmptyState>;
  const total = data.totalCount || data.questions.length;
  const unanswered = data.questions.length - data.questions.filter(q => answers[q.id]).length;
  const locked = !ready || busy || !!pending || !!legacyPending;
  return <section className="quiz-panel" aria-busy={busy}><h2>课时测验</h2><p className="boundary">{total} 道原创选择题 · 记录本课理解题的作答结果，不代表听说读写综合能力。</p><p role="status">{states[data.state]} · 完整交卷 {data.history.length} 轮 · 已答 {total - unanswered} / {total} 题 · 选项即时保存到本机草稿</p>
    {legacyPending && <Message>存在旧版待同步提交，将按原路径与内容重试，不升级为题集协议。<Button onClick={() => void retryLegacy()}>重试旧提交</Button></Message>}
    {incompatible && legacyDraft && <Message>旧草稿与当前题集不兼容，已保留；可查看或导出，不会自动覆盖。<details><summary>查看旧草稿</summary><pre>{JSON.stringify(legacyDraft, null, 2)}</pre><Button onClick={() => exportLegacy(lesson.versionId, legacyDraft)}>导出旧草稿 JSON</Button></details></Message>}
    <div className="toolbar"><Button disabled={locked} onClick={() => void send('start')}>开始 / 恢复本轮</Button><Button disabled={locked} onClick={() => void send('pause')}>暂停测验</Button><Button disabled={locked} onClick={() => void send('skip')}>跳过测验</Button></div>
    {data.questions.map(q => <fieldset className="quiz-question" key={q.id} disabled={locked}><legend lang="en">{q.ordinal}. {q.prompt}</legend>{q.options.map(o => <label className="reading-option" key={o.id}><input type="radio" name={q.id} checked={answers[q.id] === o.id} onChange={() => void select(q.id, o.id)} /><span lang="en">{o.text}</span></label>)}</fieldset>)}
    <p role="status" className="quiz-progress">{unanswered ? `还有 ${unanswered} 题未作答，作答完整后才能交卷。` : '全部题目已作答，可以交卷。'}</p>
    <Button variant="primary" disabled={locked || unanswered > 0} onClick={() => void send()}>提交本轮 {total} 题</Button>
    {busy && <Message>正在保存，请稍候…</Message>}{error && <Message error>{error}</Message>}
    {pending && !busy && <Message>原提交待确认，重试不会新增一轮。<Button onClick={() => void send(undefined, true)}>重试原提交</Button></Message>}
    {result && <div className="quiz-result" role="status"><h3>本轮结果：{result.correctCount} / {result.totalCount} 题正确</h3>{feedback(result.answers)}<div className="quiz-result-actions"><p>可重新作答再交卷，历史不会被覆盖。</p><Link className="button" href="/review">查看到期复习 →</Link></div></div>}
    <details className="quiz-history" open={!!sourceAttempt || undefined}><summary>交卷历史（{data.history.length} 轮）</summary>{!data.history.length ? <p>尚无正式交卷。草稿、暂停、跳过均不计完成。</p> : data.history.map((run, i) => <article key={run.id} className={run.answers.some(a => a.attemptId === sourceAttempt) ? 'quiz-source-attempt' : undefined}><h3>{i === data.history.length - 1 ? '首次交卷' : '重做'} · {run.correctCount} / {run.totalCount}{run.verified ? '' : ' · 未核验历史'}</h3><p>{formatBeijingTime(run.submittedAt)}（北京时间）</p>{run.contentAvailable ? runFeedback(run) : <p>此轮明细不可见。</p>}</article>)}</details>
  </section>;
}
