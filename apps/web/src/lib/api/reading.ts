import { request } from './catalog';
export type Vocabulary = { id: string; sentenceId: string; sequence: number; sourceText: string; term: string; meaning: string; usageNote: string; example: string; favorite: boolean };
export type ReadingResult = { correct: boolean; correctOptionId: string; correctText: string; sentenceId: string; knowledgePointId: string; standardText: string; explanation: string };
export type ReadingQuestionData = { id: string; prompt: string; sentenceId: string; knowledgePointId: string; state: string; options: { id: string; text: string }[]; history: { attemptId: string; eventId: string; optionId: string; correct: boolean; resultJson: string; recordedAt: string }[] };
export type ReadingData = { vocabulary: Vocabulary[]; questions: ReadingQuestionData[] };
export const getReading = (lessonId: string, versionId: string) => request<ReadingData>(`/reading?${new URLSearchParams({ lessonId, versionId })}`);
