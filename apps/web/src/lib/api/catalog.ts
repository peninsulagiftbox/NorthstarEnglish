import { ApiError } from './client';

export type LessonSummary = { id: string; versionId: string; title: string; availability: string; releaseReady: boolean };
export type Book = { id: string; title: string; sequence: number; declaredLessonCount: number; availability: 'catalog_only' };
export type Catalog = { books: Book[]; standaloneLessons: LessonSummary[] };
export type Sentence = { id: string; sequence: number; speaker: string; text: string; translation: string; explanation: string; focus: string };
export type Lesson = LessonSummary & { sentences: Sentence[]; explanationLabel: string };
export type Checkpoint = { lessonId: string; versionId: string; sentenceId: string; tab: string; showEnglish: boolean; showTranslation: boolean };
export type Resume = Checkpoint & { sessionId: string; rowVersion: number };

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { cache: 'no-store', signal: AbortSignal.timeout(6000), ...init });
  } catch {
    throw new ApiError('暂时无法连接本地服务，请确认服务已启动后重试。', 0, 'NETWORK_ERROR');
  }
  if (!response.ok) {
    throw new ApiError(response.status === 404 ? '课次不存在或尚未开放。' : response.status === 412 ? '另一页面更新了浏览位置。当前内容仍保留，请重新载入后再同步。' : '本地服务暂不可用，请稍后重试。', response.status, 'REQUEST_FAILED');
  }
  if (response.status === 204) return null as T;
  return response.json() as Promise<T>;
}

export const getCatalog = () => request<Catalog>('/books');
export const getLesson = (id: string) => request<Lesson>(`/lessons/${encodeURIComponent(id)}`);
export const getResume = () => request<Resume | null>('/study/resume');
export const saveResume = (value: Checkpoint, revision: number) => request<{ rowVersion: number }>('/study/resume', {
  method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Northstar-Request': 'local-workspace', 'If-Match': `"${revision}"` }, body: JSON.stringify(value),
});
