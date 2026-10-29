'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { request } from '@/lib/api/catalog';
import { tabs } from '@/lib/state/context';
import { Button, Card, Message } from './ui/Primitives';
import { formatBeijingTime } from '@/lib/formatTime';
type Path = { tab: string; state: string; evidenceCount: number };
type Report = { generatedAt: string; metrics: Record<string, Record<string, number>>; lessons: { lessonId: string; versionId: string; title: string; practicedStages: number; paths: Path[] }[]; readingHistory: { id: string; lessonId: string; versionId: string; sentenceId: string; exerciseId: string; correct: boolean; recordedAt: string; optionId: string }[] };
const labels: Record<string,string> = { not_started: '未开始', in_progress: '正在尝试', practiced: '已练习', skipped: '已跳过', paused: '已暂停', browsing: '已浏览 · 不计练习' };
function LearningPath({ lessons }: Pick<Report, 'lessons'>) {
  return <Card className="learning-path-panel">
    <header className="learning-path-heading">
      <h2>六步学习路径</h2>
      <p className="muted">从浏览到练习，按自己的节奏前进。课文浏览不计入 5 项训练。</p>
    </header>
    {!lessons.length && <p className="message">还没有学习路径，从课程中心选择一课开始。</p>}
    {lessons.map(lesson => <section className="path-lesson" key={lesson.versionId} aria-label={`${lesson.title} · ${lesson.versionId}`}>
      <header className="path-lesson-heading">
        <div className="path-lesson-title"><h3>{lesson.title}</h3><span className="path-version">{lesson.versionId}</span></div>
        <p className="path-summary">累计练习 <strong>{lesson.practicedStages}<span> / 5</span></strong> 项</p>
      </header>
      <ol className="learning-path">
        {lesson.paths.map((path, index) => {
          const title = tabs.find(tab => tab[0] === path.tab)?.[1] ?? path.tab;
          const continuing = path.state === 'in_progress' || path.state === 'paused';
          return <li key={path.tab} data-state={path.state}>
            <Link className="path-step" href={`/lesson/${encodeURIComponent(lesson.lessonId)}?version=${encodeURIComponent(lesson.versionId)}&tab=${encodeURIComponent(path.tab)}`} aria-label={`${title} · ${labels[path.state] ?? '状态待确认'} · ${lesson.versionId}`}>
              <div className="path-step-heading">
                <span className="path-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
                <span className="path-state">{labels[path.state] ?? '状态待确认'}</span>
              </div>
              <strong className="path-step-title">{title}</strong>
              <div className="path-step-footer">
                <span className="path-evidence">{path.tab === 'text' ? '浏览记录 · 不计练习' : `累计 ${path.evidenceCount} 条练习记录`}</span>
                <span className="path-action">{continuing ? '继续学习' : '进入学习'} <span aria-hidden="true">↗</span></span>
              </div>
            </Link>
          </li>;
        })}
      </ol>
    </section>)}
    <footer className="learning-path-footer"><span>练习记录按内容版本分别保留</span><Link className="text-link" href="/reports">查看完整学习报告 →</Link></footer>
  </Card>;
}
export function LearningReport({ dashboard = false }: { dashboard?: boolean }) {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => { let active=true; request<Report>('/reports').then(r => { if(active)setReport(r); }).catch(e=>{if(active)setError(e.message);});return()=>{active=false;}; },[retry]);
  if(error)return <Card><Message error>{error}</Message><Button onClick={()=>{setError('');setReport(null);setRetry(n=>n+1);}}>重新读取统计</Button></Card>;
  if(!report)return <Message>正在读取真实学习记录…</Message>;
  const m=report.metrics;
  return <><div className="stats-grid"><Card><p className="muted">独立听写完全匹配 / 独立提交</p><h2>{m.dictation.independentSubmitted ? `${m.dictation.independentMatches} / ${m.dictation.independentSubmitted}` : '暂无数据'}</h2><small>样本 {m.dictation.independentSubmitted} 次；排除已暴露答案</small></Card><Card><p className="muted">到期复习 / 全部卡片</p><h2>{m.review.cards ? `${m.review.due} / ${m.review.cards}` : '暂无数据'}</h2><small>自评 {m.selfRatings.submitted} 次 · 不代表客观掌握</small></Card><Card><p className="muted">已保存写作版本</p><h2>{m.writing.versions || '暂无数据'}</h2><small>样本 {m.writing.versions} 个正式版本，不含草稿</small></Card></div>
  {dashboard ? <LearningPath lessons={report.lessons} /> : <><Card className="report-section"><h2>真实行为与样本</h2><dl className="service-list"><div><dt>听写完全匹配 / 全部提交（含暴露答案）</dt><dd>{m.dictation.submitted ? `${m.dictation.exactMatches} / ${m.dictation.submitted}` : '暂无数据'} · 样本 {m.dictation.submitted} 次</dd></div><div><dt>阅读正确 / 作答题次</dt><dd>{m.reading.submitted ? `${m.reading.correct} / ${m.reading.submitted}` : '暂无数据'} · 样本 {m.reading.submitted} 题次</dd></div><div><dt>录音上传 / 当前可用</dt><dd>{m.recordings.recorded ? `${m.recordings.recorded} / ${m.recordings.available}` : '暂无数据'} · 样本 {m.recordings.recorded} 段 · 已删除 {m.recordings.deleted}；回放与人工自评不产生语音分数</dd></div><div><dt>测验正确 / 总作答题次</dt><dd>{m.quiz.total ? `${m.quiz.correct} / ${m.quiz.total}` : '暂无数据'} · {m.quiz.runs} 轮，每轮 3 题</dd></div><div><dt>客观延时复测与能力趋势</dt><dd>暂无数据 · 尚未提供此类测量</dd></div></dl></Card><Card><h2>阅读作答记录</h2>{!report.readingHistory.length ? <p className="muted">暂无数据 · 提交阅读题后显示真实记录。</p> : <ul>{report.readingHistory.map(r=><li key={r.id}><Link href={`/lesson/${r.lessonId}?version=${r.versionId}&tab=vocabulary&sentence=${r.sentenceId}`}>{r.exerciseId}</Link> · {r.correct?'正确':'错误'} · {formatBeijingTime(r.recordedAt)} · 选项 {r.optionId}</li>)}</ul>}</Card></>}
  <p className="boundary">北京时间 · 更新于 {formatBeijingTime(report.generatedAt)}。浏览、播放、跳过、收藏与未提交草稿不算练习证据；报告包含所有保留内容版本的历史。</p></>;
}
