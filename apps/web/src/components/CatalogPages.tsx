'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getCatalog, getResume } from '@/lib/api/catalog';
import type { Catalog, Resume } from '@/lib/api/catalog';
import { lessonHref } from '@/lib/state/context';
import { Button, Card, EmptyState, Message } from '@/components/ui/Primitives';

export function CatalogPage({ dashboard = false }: { dashboard?: boolean }) {
  const [data, setData] = useState<Catalog | null>(null);
  const [resume, setResume] = useState<Resume | null>(null);
  const [resumeFailed, setResumeFailed] = useState(false);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true;
    getCatalog().then(result => { if (active) setData(result); }).catch(() => { if (active) setFailed(true); });
    getResume().then(result => { if (active) setResume(result); }).catch(() => { if (active) setResumeFailed(true); });
    return () => { active = false; };
  }, [retry]);
  const lesson = data?.standaloneLessons.find(l => l.id === resume?.lessonId && l.versionId === resume.versionId) ?? data?.standaloneLessons[0];
  const href = lesson ? resume?.lessonId === lesson.id && resume.versionId === lesson.versionId ? lessonHref(resume) : `/lesson/${lesson.id}` : '/courses';
  return <><p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p><h1>{dashboard ? '今天，来学一点英语。' : '找到下一次学习的起点'}</h1><p className="intro">{dashboard ? '从一句自然的表达开始，让每次练习都有真实的依据。' : '原创 Demo 已开放本地浏览。四册目录仅作学习路径参考。'}</p>
    {failed ? <Card><Message error>课程加载失败，请确认本地服务已启动。</Message><Button onClick={() => { setFailed(false); setData(null); setRetry(n => n + 1); }}>重新加载</Button></Card> : !data ? <Message>正在从本地 API 读取课程…</Message> : <>
    {resumeFailed && <Message error>上次浏览位置读取失败；仍可从原创课入口进入。</Message>}
    {lesson ? <section className="welcome"><p className="eyebrow">{resume && resume.lessonId === lesson.id ? 'CONTINUE LEARNING' : 'START LEARNING'} · 原创演示课</p><h2>{lesson.title}<br />在社区花园里学习自然表达</h2><p>日常对话 · 原创 Demo 01 · 本地预置讲解</p><div className="hero-actions"><Link className="button primary" href={href}>{resume && resume.lessonId === lesson.id ? '继续学习' : '开始浏览原创课'} ↗</Link><Link className="button hero-secondary" href={dashboard ? '/courses' : '/lesson/' + lesson.id}>{dashboard ? '查看四册课程' : '打开课文工作台'}</Link></div><small>本地测试内容 · 来源与声音授权待审查</small></section> : <Card><EmptyState title="暂无可用原创课"><p>请检查内容包与本地服务，当前没有可浏览的课程。</p></EmptyState></Card>}
    {dashboard ? <><div className="stats-grid">{[['练习证据', '进入听写查看', '累计次数以听写服务端回执为准'], ['待复习来源', '复习页查看', '真实听写差异保留源句和原始尝试'], ['写作版本', '暂无版本', '草稿与正式写作版本分开保存']].map(([label, value, detail]) => <Card key={label}><p className="muted">{label}</p><h2>{value}</h2><small>{detail}</small></Card>)}</div><div className="content-grid"><Card><h2>今天的学习路径</h2><ol className="learning-path">{[['浏览课文与预置讲解', 'text'], ['精听听写 · Phase 04', 'dictation'], ['精读词汇 · Phase 05', 'vocabulary'], ['口语与写作 · Phase 06', 'writing']].map(([label, tab], i) => <li key={tab}><span className="path-number">{i + 1}</span><span>{label}</span>{lesson && <Link className="button" href={`/lesson/${lesson.id}?tab=${tab}`}>进入 →</Link>}</li>)}</ol></Card><Card><h2>从真实尝试开始</h2><p className="muted">浏览课文、切换句子和保存草稿都不会计为练习完成。</p><p className="boundary">当前支持播放、听写与复习来源；报告汇总将在 Phase 08 开放。尚未接入 AI、ASR 或专业语音评测。</p><Link className="text-link" href="/reports">查看学习报告 →</Link></Card></div></> : <section aria-labelledby="catalog-title"><div className="section-heading"><h2 id="catalog-title">四册学习目录</h2><span className="tag">catalog_only · 未开放学习</span></div>{data.books.length ? <div className="books-grid">{data.books.map(book => <Card key={book.id} className="book-card"><span className={`book-cover book-${book.sequence}`}>N<span>BOOK {String(book.sequence).padStart(2, '0')}</span></span><div><p className="eyebrow">BOOK {String(book.sequence).padStart(2, '0')}</p><h2>{book.title}</h2><p className="muted">{book.declaredLessonCount} 课 · 目录元信息</p><span className="tag">仅目录 · 暂不可学习</span><p className="muted">未提供教材正文或录音。</p></div></Card>)}</div> : <EmptyState title="暂无目录"><p>课程 API 未返回目录元信息。</p></EmptyState>}</section>}
    </>}
  </>;
}
