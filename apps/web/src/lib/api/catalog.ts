import { ApiError } from './client.ts';

export type PublicationState = 'draft' | 'validated' | 'published' | 'withdrawn';
export type ContentReadiness = 'legacy_unassessed' | 'basic_content' | 'teaching_complete';
export type LessonKind = 'original_demo' | 'original' | 'licensed';
export type AudioSourceKind = 'original_tts' | 'original_recording' | 'licensed_audio';

export type LessonSummary = { id: string; versionId: string; title: string; availability: string; releaseReady: boolean; bookId?: string | null; kind?: LessonKind; publicationState?: PublicationState; contentReadiness?: ContentReadiness; sequence?: number | null; displayNumber?: string | null };
export type Book = { id: string; title: string; sequence: number; editionLabel: string; declaredLessonCount: number; actualLessonCount: number; availableLessonCount: number; availability: 'catalog_only' };
export type Catalog = { books: Book[]; standaloneLessons: LessonSummary[] };
export type BookLesson = LessonSummary & { readable: boolean; publicationState?: PublicationState; contentReadiness?: ContentReadiness; targetSentenceId?: string; mappingStatus?: string; relation?: string };
export type LessonPage = { items: BookLesson[]; nextCursor: string | null };
export type LessonVersion = { versionId: string; number: number; isCurrent: boolean; readable: boolean; publicationState?: PublicationState; contentReadiness?: ContentReadiness; targetSentenceId?: string; mappingStatus?: string; relation?: string };
export type Paragraph = { id: string; stableKey: string; identityId?: string; sequence: number };
export type AudioAsset = { id: string; uri: string; durationMs: number; sourceKind?: AudioSourceKind; sha256?: string; status: string; code?: string };
export type Sentence = { id: string; identityId?: string; sequence: number; paragraphId?: string; speaker: string; text: string; translation: string; explanation: string; focus: string; assetId?: string; audioAssetId?: string; startMs?: number; endMs?: number; audio: AudioAsset };
export type Lesson = LessonSummary & { sentences: Sentence[]; audioAssets?: AudioAsset[]; fullAudioAssetId?: string; paragraphs?: Paragraph[]; hasHistoricalEvidence?: boolean; explanationLabel: string; audioLabel?: string; availableTasks?: string[]; hasWritingTask?: boolean; licenses?: { sourceRef: string; reviewStatus: string; sourceType: string }[] };
export type Checkpoint = { lessonId: string; versionId: string; sentenceId: string; tab: string; showEnglish: boolean; showTranslation: boolean; playingSentenceId?: string | null; positionMs?: number; playbackCoordinate?: 'segment_offset_v1' | null; playbackMode?: 'segment' | 'full' | null; fullAssetId?: string | null; assetPositionMs?: number | null };
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
  if ((lesson.publicationState !== undefined && !['draft', 'validated', 'published', 'withdrawn'].includes(lesson.publicationState))
      || (lesson.contentReadiness !== undefined && !['legacy_unassessed', 'basic_content', 'teaching_complete'].includes(lesson.contentReadiness))
      || (lesson.kind !== undefined && !['original_demo', 'original', 'licensed'].includes(lesson.kind))) throw new ApiError('课程发布或来源类型无效。', 503, 'INVALID_CONTENT');
  const identities = new Set<string>();
  const ids = new Set<string>();
  for (const sentence of lesson.sentences) {
    if (!sentence || typeof sentence.id !== 'string' || ids.has(sentence.id) || !Number.isInteger(sentence.sequence)
        || typeof sentence.text !== 'string' || !sentence.audio || !['ready', 'unavailable'].includes(sentence.audio.status)
        || sentence.audio.uri !== `/api/v1/audio/${sentence.audio.id}`) throw new ApiError('句子或音频关联无效。', 503, 'INVALID_CONTENT');
    if (sentence.identityId !== undefined) {
      if (!sentence.identityId || identities.has(sentence.identityId)) throw new ApiError('版本内稳定身份重复。', 503, 'INVALID_CONTENT');
      identities.add(sentence.identityId);
    }
    if (sentence.audio.sourceKind !== undefined && !['original_tts', 'original_recording', 'licensed_audio'].includes(sentence.audio.sourceKind)) throw new ApiError('音频来源类型无效。', 503, 'INVALID_CONTENT');
    const start = sentence.startMs ?? 0, end = sentence.endMs ?? sentence.audio.durationMs;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || !Number.isInteger(sentence.audio.durationMs) || end > sentence.audio.durationMs
        || (sentence.assetId !== undefined && sentence.assetId !== sentence.audio.id) || (sentence.audioAssetId !== undefined && sentence.audioAssetId !== sentence.audio.id)) throw new ApiError('句子时间范围无效。', 503, 'INVALID_CONTENT');
    ids.add(sentence.id);
  }
  const ends = new Map<string, number>();
  for (const sentence of lesson.sentences) {
    const start = sentence.startMs ?? 0, end = sentence.endMs ?? sentence.audio.durationMs;
    if (start < (ends.get(sentence.audio.id) ?? 0)) throw new ApiError('同音轨句子区间重叠或逆序。', 503, 'INVALID_CONTENT');
    ends.set(sentence.audio.id, end);
  }
  if (lesson.audioAssets) {
    const assets = new Map(lesson.audioAssets.map(a => [a.id, a]));
    if (assets.size !== lesson.audioAssets.length || lesson.sentences.some(s => {
      const asset = assets.get(s.audio.id); return !asset || asset.uri !== s.audio.uri || asset.sha256 !== s.audio.sha256 || asset.durationMs !== s.audio.durationMs || asset.status !== s.audio.status;
    }) || (lesson.fullAudioAssetId && !assets.has(lesson.fullAudioAssetId))) throw new ApiError('音轨清单或主音轨关联无效。', 503, 'INVALID_CONTENT');
    for (const asset of assets.values()) if (!Number.isInteger(asset.durationMs) || asset.durationMs <= 0 || asset.uri !== `/api/v1/audio/${asset.id}` || !['ready', 'unavailable'].includes(asset.status)) throw new ApiError('音轨清单无效。', 503, 'INVALID_CONTENT');
  } else if (lesson.fullAudioAssetId) throw new ApiError('主音轨缺少清单。', 503, 'INVALID_CONTENT');
  if (lesson.paragraphs) {
    const paragraphs = new Set(lesson.paragraphs.map(p => p.id));
    if (paragraphs.size !== lesson.paragraphs.length || lesson.sentences.some(s => !s.paragraphId || !paragraphs.has(s.paragraphId))) throw new ApiError('段落关联无效。', 503, 'INVALID_CONTENT');
  }
  return lesson;
}
export const getLesson = async (id: string, versionId?: string) => validateLesson(await request<unknown>(`/lessons/${encodeURIComponent(id)}${versionId ? `?versionId=${encodeURIComponent(versionId)}` : ''}`), id, versionId);
export const getBookLessons = (id: string, cursor?: string) => request<LessonPage>(`/books/${encodeURIComponent(id)}/lessons?limit=20${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
export const getLessonVersions = (id: string, fromVersion?: string, fromSentence?: string) => request<{ versions: LessonVersion[] }>(`/lessons/${encodeURIComponent(id)}/versions${fromVersion && fromSentence ? `?fromVersion=${encodeURIComponent(fromVersion)}&fromSentence=${encodeURIComponent(fromSentence)}` : ''}`);
export const getResume = () => request<Resume | null>('/study/resume');
export const saveResume = (value: Checkpoint, revision: number) => request<{ rowVersion: number }>('/study/resume', {
  method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-Northstar-Request': 'local-workspace', 'If-Match': `"${revision}"` }, body: JSON.stringify(value),
});
