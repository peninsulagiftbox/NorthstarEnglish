'use client';
import { useLesson } from '@/lib/state/LessonProvider';
import { Button } from '@/components/ui/Primitives';
export function EvidenceLink({ sentenceId }: { sentenceId: string }) {
  const { lesson, update } = useLesson();
  const sentence = lesson.sentences.find(s => s.id === sentenceId);
  if (!sentence) return null;
  return <Button onClick={() => update({ sentenceId, tab: 'text', showEnglish: true })}>在全文中查看上下文 →</Button>;
}
