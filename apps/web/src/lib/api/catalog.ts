import { ApiError } from './client.ts';

export type LessonSummary = { id: string; versionId: string; title: string; availability: string; releaseReady: boolean; bookId?: string | null; kind?: string; sequence?: number | null; displayNumber?: string | null };
export type Book = { id: string; title: string; sequence: number; editionLabel: string; declaredLessonCount: number; actualLessonCount: number; availableLessonCount: number; availability: 'catalog_only' };
export type Catalog = { books: Book[]; standaloneLessons: LessonSummary[] };
export type BookLesson = LessonSummary & { readable: boolean };
export type LessonPage = { items: BookLesson[]; nextCursor: string | null };
export type LessonVersion = { versionId: string; number: number; isCurrent: boolean; readable: boolean };
export type Paragraph = { id: string; stableKey: string; sequence: number };
export type Sentence = { id: string; sequence: number; paragraphId?: string; speaker: string; text: string; translation: string; explanation: string; focus: string; audio: { id: string; uri: string; durationMs: number; sha256?: string; status: string } };
export type Lesson = LessonSummary & { sentences: Sentence[]; paragraphs?: Paragraph[]; explanationLabel: string; audioLabel?: string; availableTasks?: string[]; hasWritingTask?: boolean; licenses?: { sourceRef: string; reviewStatus: string; sourceType: string }[] };
export type Checkpoint = { lessonId: string; versionId: string; sentenceId: string; tab: string; showEnglish: boolean; showTranslation: boolean; playingSentenceId?: string | null; positionMs?: number };
export type Resume = Checkpoint & { sessionId: string; rowVersion: number };

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { cache: 'no-store', signal: AbortSignal.timeout(6000), ...init });
  } catch {
    throw new ApiError('暂时无法连接本地服务，请确认服务已启动后重试。', 0, 'NETWORK_ERROR');
  }
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as { detail?: string; code?: string } | null;
    throw new ApiError(problem?.detail ?? (response.status === 404 ? '课次不存在或尚未开放。' : response.status === 412 ? '另一页面更新了浏览位置。当前内容仍保留，请重新载入后再同步。' : '本地服务暂不可用，请稍后重试。'), response.status, problem?.code ?? 'REQUEST_FAILED');
  }
  if (response.status === 204) return null as T;
  return response.json() as Promise<T>;
}

export const getCatalog = () => request<Catalog>('/books');
export function validateLesson(value: unknown, id: string, versionId?: string): Lesson {
  const lesson = value as Lesson;
  if (!lesson || lesson.id !== id || typeof lesson.versionId !== 'string' || (versionId && lesson.versionId !== versionId)
      || typeof lesson.title !== 'string' || !Array.isArray(lesson.sentences)) throw new ApiError('课程响应不完整，请恢复对应版本内容。', 503, 'INVALID_CONTENT');
  const ids = new Set<string>();
  for (const sentence of lesson.sentences) {
    if (!sentence || typeof sentence.id !== 'string' || ids.has(sentence.id) || !Number.isInteger(sentence.sequence)
        || typeof sentence.text !== 'string' || !sentence.audio || sentence.audio.status !== 'ready'
        || sentence.audio.uri !== `/api/v1/audio/${sentence.audio.id}`) throw new ApiError('句子或音频关联无效。', 503, 'INVALID_CONTENT');
    ids.add(sentence.id);
  }
  if (lesson.paragraphs) {
    const paragraphs = new Set(lesson.paragraphs.map(p => p.id));
    if (paragraphs.size !== lesson.paragraphs.length || lesson.sentences.some(s => !s.paragraphId || !paragraphs.has(s.paragraphId))) throw new ApiError('段落关联无效。', 503, 'INVALID_CONTENT');
  }
  return lesson;
}
export const getLesson = async (id: string, versionId?: string) => validateLesson(await request<unknown>(`/lessons/${encodeURIComponent(id)}${versionId ? `?versionId=${encodeURIComponent(versionId)}` : ''}`), id, versionId);
export const getBookLessons = (id: string, cursor?: string) => request<LessonPage>(`/books/${encodeURIComponent(id)}/lessons?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
export const getLessonVersions = (id: string) => request<{ versions: LessonVersion[] }>(`/lessons/${encodeURIComponent(id)}/versions`);
export const getResume = () => request<Resume | null>('/study/resume');
export const saveResume = (value: Checkpoint, revision: number) => request<{ rowVersion: number }>('/study/resume', {
  method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Northstar-Request': 'local-workspace', 'If-Match': `"${revision}"` }, body: JSON.stringify(value),
});
