'use client';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useSearchParams } from 'next/navigation';
import { ApiError } from '@/lib/api/client';
import { getLesson, getResume, saveResume } from '@/lib/api/catalog';
import type { Checkpoint, Lesson, Resume } from '@/lib/api/catalog';
import { lessonHref, resolveContext } from './context';
import { Button, Message } from '@/components/ui/Primitives';
import Link from 'next/link';

type Workspace = { lesson: Lesson; checkpoint: Checkpoint; update: (patch: Partial<Checkpoint>) => void; sync: string; syncError: boolean; playback: Pick<Checkpoint, "playingSentenceId" | "positionMs">; savePlayback: (id: string, ms: number) => void };
const Context = createContext<Workspace | null>(null);
export function useLesson() { const value = useContext(Context); if (!value) throw new Error('LessonProvider required'); return value; }
export function LessonProvider({ lessonId, children }: { lessonId: string; children: ReactNode }) {
  const versionId = useSearchParams().get('version');
  return <VersionedLessonProvider key={`${lessonId}:${versionId ?? 'current'}`} lessonId={lessonId} versionId={versionId}>{children}</VersionedLessonProvider>;
}
function VersionedLessonProvider({ lessonId, versionId, children }: { lessonId: string; versionId: string | null; children: ReactNode }) {
  const params = useSearchParams();
  const [loaded, setLoaded] = useState<{ lesson: Lesson; resume: Resume | null } | null>(null);
  const [playback, setPlayback] = useState<Pick<Checkpoint, 'playingSentenceId' | 'positionMs'>>({});
  const savePlayback = useCallback((id: string, ms: number) => setPlayback(old => old.playingSentenceId === id && old.positionMs === ms ? old : { playingSentenceId: id, positionMs: ms }), []);
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [retry, setRetry] = useState(0);
  const [sync, setSync] = useState('正在读取浏览位置…');
  const [syncError, setSyncError] = useState(false);
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const revision = useRef<number | null>(null);
  const queue = useRef<Promise<void>>(Promise.resolve());
  useEffect(() => {
    let active = true;
    Promise.all([getLesson(lessonId, versionId ?? undefined), getResume().then(resume => ({ resume, failed: false })).catch(() => ({ resume: null, failed: true }))]).then(([lesson, result]) => {
      if (!active) return;
      if (!lesson.sentences.length) { setError(new Error('本课暂无可浏览句子。')); return; }
      revision.current = result.failed ? null : result.resume?.rowVersion ?? 0;
      setSync(result.failed ? '浏览位置读取失败；当前页面可浏览，暂不覆盖服务端记录。' : '浏览位置已读取');
      setSyncError(result.failed);
      const checkpoint = resolveContext(lesson, new URLSearchParams(window.location.search), result.resume);
      window.history.replaceState(null, '', lessonHref(checkpoint));
      if (result.resume?.versionId === lesson.versionId) setPlayback({ playingSentenceId: result.resume.playingSentenceId, positionMs: result.resume.positionMs });
      setLoaded({ lesson, resume: result.resume });
    }).catch(e => { if (active) setError(e); });
    return () => { active = false; };
  }, [lessonId, versionId, retry]);
  const checkpoint = useMemo(() => loaded ? resolveContext(loaded.lesson, new URLSearchParams(params.toString()), loaded.resume) : null, [loaded, params]);
  const serialized = checkpoint ? JSON.stringify({ ...checkpoint, ...playback }) : null;
  useEffect(() => {
    if (!serialized || revision.current === null) return;
    let active = true;
    const timer = setTimeout(() => {
      queue.current = queue.current.then(async () => {
        if (!active || revision.current === null) return;
        setSync('正在保存浏览位置…');
        try {
          const response = await saveResume(JSON.parse(serialized) as Checkpoint, revision.current);
          revision.current = response.rowVersion;
          setSavedKey(serialized);
          setSync('浏览位置已保存 · 不计练习完成'); setSyncError(false);
        } catch (e) {
          // Do not silently overwrite another tab, or retry an uncertain response with stale revision.
          revision.current = null;
          setSync(e instanceof Error ? e.message : '浏览位置保存失败，请重新载入后重试。'); setSyncError(true);
        }
      });
    }, 350);
    return () => { active = false; clearTimeout(timer); };
  }, [serialized]);
  if (error) return <section className="surface"><h1>{error instanceof ApiError && error.status === 404 ? '找不到这个课次' : '暂时无法打开课文'}</h1><Message error>{error.message}</Message><Button onClick={() => { setError(null); setRetry(r => r + 1); }}>重新加载</Button> <Link className="button" href="/courses">返回课程中心</Link></section>;
  if (!loaded || !checkpoint) return <Message>正在读取课文与浏览位置…</Message>;
  const update = (patch: Partial<Checkpoint>) => window.history.pushState(null, '', lessonHref({ ...checkpoint, ...patch }));
  const displaySync = !syncError && serialized !== savedKey ? '浏览位置更新中…' : sync;
  return <Context.Provider value={{ lesson: loaded.lesson, checkpoint, update, sync: displaySync, syncError, playback, savePlayback }}>{children}</Context.Provider>;
}
