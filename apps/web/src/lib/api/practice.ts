import { request } from './catalog';
import { commandHeaders } from '../persistence/outbox';
export type Revision = { id: string; versionNo: number; text: string; createdAt: string; parentRevisionId: string | null };
export type WritingData = { taskId: string; prompt: string; sourceSentenceIds: string[]; draft: { text: string; rowVersion: number }; state: string; revisions: Revision[] };
export type RecordingData = { state: string; recordings: { id: string; mimeType: string; durationMs: number; byteSize: number; status: string; createdAt: string; playbackCount: number }[] };
export const writingData = (lessonId: string, versionId: string) => request<WritingData>(`/writing?${new URLSearchParams({ lessonId, versionId })}`);
export const postPractice = <T,>(path: string, body: unknown) => request<T>(path, { method: 'POST', headers: commandHeaders, body: JSON.stringify(body) });
export const stateLabel: Record<string, string> = { not_started: '未开始', in_progress: '正在练习', practiced: '已有练习证据', skipped: '本轮已跳过', paused: '本轮已暂停' };
