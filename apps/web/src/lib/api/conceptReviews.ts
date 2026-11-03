import { request } from './catalog.ts';
import type { KnowledgeKind } from './knowledge.ts';

export type ConceptReviewCard = {
  id: string;
  due: boolean;
  dueAt: string;
  reps: number;
  rowVersion: number;
  promptKind: string;
  protocolVersion: string;
  schedulerVersion: string;
  conceptId: string;
  kind: KnowledgeKind;
  canonicalKey: string;
  senseKey: string;
  displayName: string;
  explanation: string;
  visibleSourceCount: number;
};
export type ConceptReviewPage = { items: ConceptReviewCard[]; nextCursor: string | null };
export type ConceptReviewSource = {
  attemptId: string;
  occurrenceId: string;
  lessonId?: string;
  versionId?: string;
  exerciseKind?: string;
  correct?: boolean;
  recordedAt: string;
  visible: boolean;
  restricted: boolean;
  lessonTitle?: string;
  scope?: string;
  sequence?: number | null;
  sentenceText?: string | null;
};
export type ConceptReviewSourcePage = { items: ConceptReviewSource[]; nextCursor: string | null };

export const getConceptReviews = (all: boolean, cursor?: string) =>
  request<ConceptReviewPage>(`/concept-reviews/due?all=${all}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
export const getConceptReviewSources = (cardId: string, cursor?: string) =>
  request<ConceptReviewSourcePage>(`/concept-reviews/${encodeURIComponent(cardId)}/sources${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`);
