'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getBookLessons, getCatalog, getLesson, getResume } from '@/lib/api/catalog';
import type { Book, Catalog, LessonPage, Resume } from '@/lib/api/catalog';
import { lessonHref } from '@/lib/state/context';
import { LearningReport } from './LearningReport';
import { Button, Card, EmptyState, Message } from '@/components/ui/Primitives';

function BookCourses({ book }: { book: Book }) {
  const [open, setOpen] = useState(false), [data, setData] = useState<LessonPage | null>(null);
  const [busy, setBusy] = useState(false), [error, setError] = useState('');
  async function load(cursor?: string) {
    setBusy(true); setError('');
    try { const page = await getBookLessons(book.id, cursor); setData(old => ({ ...page, items: cursor && old ? [...old.items, ...page.items] : page.items })); }
    catch (e) { setError(e instanceof Error ? e.message : '课程列表读取失败。'); }
    finally { setBusy(false); }
  }
  return <Card className="book-card"><span className={`book-cover book-${book.sequence}`}>N<span>BOOK {String(book.sequence).padStart(2, '0')}</span></span><div className="book-details"><p className="eyebrow">BOOK {String(book.sequence).padStart(2, '0')}</p><h2>{book.title}</h2><p className="muted">{book.declaredLessonCount} 课 · 目录元信息</p><div className="book-availability"><span className="book-status">{book.availableLessonCount > 0 ? '课程内容见下方列表' : '仅目录 · 暂不可学习'}</span><p className="muted">实际 {book.actualLessonCount} 课 · 可学习 {book.availableLessonCount} 课</p></div><Button aria-expanded={open} onClick={() => { setOpen(!open); if (!open && !data && !busy) void load(); }}>{open ? '收起课程列表' : '查看实际课程'}</Button>
    {open && <div aria-label={`${book.title}实际课程`}>
      {busy && <Message>正在读取课程…</Message>}
      {error && <Message error>{error}<Button disabled={busy} onClick={() => void load(data?.nextCursor ?? undefined)}>重新读取</Button></Message>}
      {data && !data.items.length && <EmptyState title="本册尚无已导入课程"><p>当前只有目录元信息，未提供教材正文或录音。</p></EmptyState>}
      {!!data?.items.length && <ul>{data.items.map(item => <li key={item.id}>{item.readable && item.versionId ? <Link href={`/lesson/${encodeURIComponent(item.id)}?version=${encodeURIComponent(item.versionId)}`}>{item.displayNumber ?? (item.sequence ? `第 ${item.sequence} 课` : '课次未设置')} · {item.title}</Link> : <span>{item.displayNumber ?? '课次未设置'} · 尚不可学习（{item.availability}）</span>}</li>)}</ul>}
      {data?.nextCursor && !error && <Button disabled={busy} onClick={() => void load(data.nextCursor!)}>加载更多课程</Button>}
    </div>}
  </div></Card>;
}

export function CatalogPage({ dashboard = false }: { dashboard?: boolean }) {
  const [data, setData] = useState<Catalog | null>(null), [resume, setResume] = useState<Resume | null>(null);
  const [resumeFailed, setResumeFailed] = useState(false), [failed, setFailed] = useState(false), [retry, setRetry] = useState(0);
  useEffect(() => { let active = true;
    getCatalog().then(result => { if (active) setData(result); }).catch(() => { if (active) setFailed(true); });
    // Resolve a book-bound or historical resume directly, without guessing it from the standalone list.
    getResume().then(async result => { if (result) await getLesson(result.lessonId, result.versionId); if (active) { setResume(result); setResumeFailed(false); } }).catch(() => { if (active) setResumeFailed(true); });
    return () => { active = false; };
  }, [retry]);
  const lesson = data?.standaloneLessons.find(l => l.id === resume?.lessonId) ?? data?.standaloneLessons[0];
  const href = resume ? lessonHref(resume) : lesson ? `/lesson/${encodeURIComponent(lesson.id)}` : '/courses';
  return <><p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p><h1>{dashboard ? '今天，来学一点英语。' : '找到下一次学习的起点'}</h1><p className="intro">{dashboard ? '从一句自然的表达开始，让每次练习都有真实的依据。' : '读取本地真实课程。四册目录元信息与已导入内容分别展示。'}</p>
    {failed ? <Card><Message error>课程加载失败，请确认本地服务已启动。</Message><Button onClick={() => { setFailed(false); setData(null); setRetry(n => n + 1); }}>重新加载</Button></Card> : !data ? <Message>正在从本地 API 读取课程…</Message> : <>
    {resumeFailed && <Message error>上次浏览位置或对应资源读取失败；仍可从课程列表进入。</Message>}
    {resume || lesson ? <section className="welcome"><p className="eyebrow">{resume ? 'CONTINUE LEARNING' : 'START LEARNING'}</p><h2>{resume && resume.lessonId !== lesson?.id ? '继续上次的课程' : lesson?.title}</h2><p>本地内容 · 本地预置讲解</p><div className="hero-actions"><Link className="button primary" href={href}>{resume ? '继续学习' : '开始浏览原创课'} ↗</Link><Link className="button hero-secondary" href={dashboard ? '/courses' : href}>{dashboard ? '查看四册课程' : '打开课文工作台'}</Link></div><small>内容来源与音频授权按各版本记录展示</small></section> : <Card><EmptyState title="暂无可用课程"><p>当前没有可浏览的课程，请检查内容包与本地服务。</p></EmptyState></Card>}
    {dashboard ? <LearningReport dashboard /> : <>
      <section className="catalog-section" aria-labelledby="catalog-title"><div className="catalog-section-heading"><h2 id="catalog-title">四册目录</h2><p className="muted">目录与实际内容分别计数</p></div>{data.books.length ? <div className="books-grid">{data.books.map(book => <BookCourses key={book.id} book={book} />)}</div> : <EmptyState title="暂无目录"><p>课程 API 未返回目录元信息。</p></EmptyState>}</section>
      <section className="catalog-section" aria-labelledby="standalone-title"><div className="catalog-section-heading"><h2 id="standalone-title">独立原创课程</h2></div>{data.standaloneLessons.length ? <div className="books-grid">{data.standaloneLessons.map(item => <Card key={item.id}><h3>{item.title}</h3><p className="muted">独立课程 · {item.versionId}</p><Link className="button" href={`/lesson/${encodeURIComponent(item.id)}?version=${encodeURIComponent(item.versionId)}`}>浏览 {item.title}</Link></Card>)}</div> : <EmptyState title="暂无独立课程"><p>不会将独立原创课归入教材四册。</p></EmptyState>}</section>
    </>}
    </>}
  </>;
}
