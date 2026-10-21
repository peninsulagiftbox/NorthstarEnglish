import { Suspense } from 'react';
import { LessonProvider } from '@/lib/state/LessonProvider';
import { LessonWorkspace } from '@/components/lesson/LessonWorkspace';
export default async function LessonPage({ params }: { params: Promise<{ lessonId: string }> }) {
  const { lessonId } = await params;
  return <Suspense fallback={<p role="status">正在加载工作台…</p>}><LessonProvider key={lessonId} lessonId={lessonId}><LessonWorkspace /></LessonProvider></Suspense>;
}
