import type { ConceptReviewCard } from '../api/conceptReviews.ts';
import type { ConceptReviewPage } from '../api/conceptReviews.ts';

export function mergeCards(current: ConceptReviewCard[], incoming: ConceptReviewCard[]) {
  const byId = new Map(current.map(item => [item.id, item]));
  for (const item of incoming) {
    const existing = byId.get(item.id);
    if (!existing || item.rowVersion > existing.rowVersion) byId.set(item.id, item);
  }
  return [...byId.values()];
}

export async function visibleCards(cards: ConceptReviewCard[], all: boolean, hasPending: (id: string) => Promise<unknown>) {
  if (all) return cards;
  const pending = await Promise.all(cards.map(item => hasPending(item.id)));
  return cards.filter((item, index) => item.due || !!pending[index]);
}

export type QueueState = { items: ConceptReviewCard[] | null; nextCursor: string | null; loading: boolean; error: string };
export const emptyQueue: QueueState = { items: null, nextCursor: null, loading: true, error: '' };

export class ConceptQueuePager {
  state: QueueState = emptyQueue;
  private generation = 0;
  private all = false;
  private fetchPage: (cursor?: string) => Promise<ConceptReviewPage>;
  private hasPending: (id: string) => Promise<unknown>;
  private changed: (state: QueueState) => void;
  constructor(fetchPage: (cursor?: string) => Promise<ConceptReviewPage>, hasPending: (id: string) => Promise<unknown>, changed: (state: QueueState) => void) {
    this.fetchPage = fetchPage; this.hasPending = hasPending; this.changed = changed;
  }

  reset(all: boolean) {
    this.generation += 1;
    this.all = all;
    this.publish(emptyQueue);
    return this.load();
  }
  dispose() { this.generation += 1; }
  more() {
    if (this.state.loading || !this.state.nextCursor) return Promise.resolve();
    return this.load(this.state.nextCursor);
  }
  retry() {
    if (this.state.loading) return Promise.resolve();
    return this.load(this.state.nextCursor ?? undefined);
  }
  private publish(state: QueueState) { this.state = state; this.changed(state); }
  private async load(cursor?: string) {
    const generation = this.generation, all = this.all;
    this.publish({ ...this.state, loading: true, error: '' });
    try {
      const page = await this.fetchPage(cursor);
      if (generation !== this.generation) return;
      const items = await visibleCards(page.items, all, this.hasPending);
      if (generation !== this.generation) return;
      this.publish({ items: cursor ? mergeCards(this.state.items ?? [], items) : mergeCards([], items), nextCursor: page.nextCursor, loading: false, error: '' });
    } catch (error) {
      if (generation === this.generation) this.publish({ ...this.state, loading: false, error: error instanceof Error ? error.message : '概念卡读取失败' });
    }
  }
}
