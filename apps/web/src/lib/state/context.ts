import type { Checkpoint, Lesson, Resume } from '../api/catalog.ts';
export const tabs = [ ['text', '课文'], ['dictation', '精听听写'], ['vocabulary', '精读词汇'], ['speaking', '口语跟读'], ['writing', '写作'], ['quiz', '课时测验'] ] as const;
export type Tab = typeof tabs[number][0];
export function resolveContext(lesson: Lesson, params: URLSearchParams, resume: Resume | null, defaults?: { showTranslation: boolean }): Checkpoint {
  const previous = resume?.lessonId === lesson.id && resume.versionId === lesson.versionId ? resume : null;
  const tab = params.get('tab') ?? previous?.tab ?? 'text';
  const sentence = params.get('sentence') ?? previous?.sentenceId;
  return { lessonId: lesson.id, versionId: lesson.versionId,
    sentenceId: lesson.sentences.find(s => s.id === sentence)?.id ?? lesson.sentences[0].id,
    tab: tabs.some(t => t[0] === tab) ? tab : 'text',
    showEnglish: params.has('english') ? params.get('english') !== '0' : previous?.showEnglish ?? true,
    showTranslation: params.has('translation') ? params.get('translation') !== '0' : previous?.showTranslation ?? defaults?.showTranslation ?? true };
}
export function lessonHref(context: Checkpoint) {
  const params = new URLSearchParams({ version: context.versionId, tab: context.tab, sentence: context.sentenceId, english: context.showEnglish ? '1' : '0', translation: context.showTranslation ? '1' : '0' });
  return `/lesson/${encodeURIComponent(context.lessonId)}?${params}`;
}
/** Only a reviewed server mapping can choose a sentence in a different version. */
export function lessonVersionHref(context: Checkpoint, versionId: string, mappedSentenceId?: string) {
  const sentenceId = versionId === context.versionId ? context.sentenceId : mappedSentenceId ?? '';
  return lessonHref({ ...context, versionId, sentenceId });
}
export function isBlind(context: Checkpoint) { return !context.showEnglish || context.tab === 'dictation'; }
export function draftKey(context: Checkpoint) {
  return `northstar:draft:${context.versionId}:${context.tab}:${context.tab === 'writing' ? 'lesson' : context.sentenceId}`;
}
