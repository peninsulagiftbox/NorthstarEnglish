import { request } from './catalog.ts';

export type KnowledgeKind = 'vocabulary' | 'grammar' | 'collocation' | 'pattern';
export type KnowledgeConcept = { id: string; kind: KnowledgeKind; canonicalKey: string; senseKey: string; displayName: string; lessonCount: number };
export type KnowledgeConceptPage = { items: KnowledgeConcept[]; nextCursor: string | null };
export type KnowledgeOccurrence = {
  id: string;
  scope: 'lesson' | 'paragraph' | 'sentence';
  lessonId: string;
  versionId: string;
  title?: string | null;
  sequence?: number | null;
  sentenceText?: string | null;
  usage?: Record<string, unknown> | null;
  exerciseCount?: number;
  wrongAttemptCount?: number;
  restricted: boolean;
};
export type KnowledgeOccurrencePage = { items: KnowledgeOccurrence[]; nextCursor: string | null };

const kindNames: Record<KnowledgeKind, string> = { vocabulary: '词汇', grammar: '语法', collocation: '搭配', pattern: '句型' };
export const knowledgeKindName = (kind: KnowledgeKind) => kindNames[kind] ?? kind;

export const getKnowledgeConcepts = (lessonId: string, versionId: string, cursor?: string) =>
  request<KnowledgeConceptPage>(`/knowledge/concepts?lessonId=${encodeURIComponent(lessonId)}&versionId=${encodeURIComponent(versionId)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
export const getKnowledgeOccurrences = (conceptId: string, cursor?: string) =>
  request<KnowledgeOccurrencePage>(`/knowledge/concepts/${encodeURIComponent(conceptId)}/occurrences${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`);
