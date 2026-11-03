import { test } from "node:test";
import assert from "node:assert/strict";
import { ConceptQueuePager, mergeCards, visibleCards } from "../src/lib/review/conceptQueue.ts";
import type { ConceptReviewCard } from "../src/lib/api/conceptReviews.ts";

const card = (id: string, rowVersion = 1, due = true): ConceptReviewCard => ({
  id, due, dueAt: "2026-11-03T00:00:00Z", reps: 0, rowVersion, promptKind: "meaning_recall",
  protocolVersion: "concept_review_v1", schedulerVersion: "simple_v1", conceptId: "c-" + id,
  kind: "vocabulary", canonicalKey: "w-" + id, senseKey: "s", displayName: "D-" + id,
  explanation: "e", visibleSourceCount: 0,
});

test("mergeCards dedups by card id and keeps the higher row version", () => {
  const merged = mergeCards([card("a", 1), card("b", 2)], [card("b", 1), card("c", 1), card("a", 3)]);
  assert.deepEqual(merged.map(item => [item.id, item.rowVersion]), [["a", 3], ["b", 2], ["c", 1]]);
});

test("mergeCards preserves page order for newly loaded cards", () => {
  const merged = mergeCards([card("a")], [card("b"), card("c")]);
  assert.deepEqual(merged.map(item => item.id), ["a", "b", "c"]);
});

test("visibleCards keeps due and pending-outbox cards in due mode", async () => {
  const cards = [card("a"), card("b", 1, false), card("c", 1, false)];
  const visible = await visibleCards(cards, false, id => Promise.resolve(id === "c"));
  assert.deepEqual(visible.map(item => item.id), ["a", "c"]);
  assert.equal((await visibleCards(cards, true, async () => { throw new Error("must not read outbox"); })).length, 3);
});

test("real pager traverses 0, 1, 20, 21, 22 and 100 cards in backend order", async () => {
  for (const count of [0, 1, 20, 21, 22, 100]) {
    const cards = Array.from({ length: count }, (_, index) => card(String(index)));
    const pager = new ConceptQueuePager(async cursor => {
      const offset = Number(cursor ?? 0), items = cards.slice(offset, offset + 20);
      return { items, nextCursor: items.length === 20 ? String(offset + 20) : null };
    }, async () => false, () => {});
    await pager.reset(true);
    while (pager.state.nextCursor) await pager.more();
    assert.deepEqual(pager.state.items, cards);
  }
});

test("pager ignores late mode responses and locks duplicate page requests", async () => {
  let resolveOld!: (page: { items: ConceptReviewCard[]; nextCursor: string | null }) => void;
  let calls = 0;
  const pager = new ConceptQueuePager(async () => {
    calls += 1;
    if (calls === 1 || calls === 3) return new Promise(resolve => { resolveOld = resolve; });
    return { items: [card('due'), card('future', 1, false)], nextCursor: 'next' };
  }, async () => false, () => {});
  const old = pager.reset(true);
  await pager.reset(false);
  resolveOld({ items: [card('old')], nextCursor: null }); await old;
  assert.deepEqual(pager.state.items?.map(item => item.id), ['due']);
  const more = pager.more(); await pager.more();
  assert.equal(calls, 3);
  const finishMore = resolveOld;
  await pager.reset(true);
  finishMore({ items: [card('late')], nextCursor: null }); await more;
  assert.deepEqual(pager.state.items?.map(item => item.id), ['due', 'future']);
});

test("pagination failure retains cards and retries the same cursor", async () => {
  let fail = true;
  const cursors: (string | undefined)[] = [];
  const pager = new ConceptQueuePager(async cursor => {
    cursors.push(cursor);
    if (!cursor) return { items: [card('a')], nextCursor: 'p2' };
    if (fail) { fail = false; throw new Error('offline'); }
    return { items: [card('a'), card('b')], nextCursor: null };
  }, async () => false, () => {});
  await pager.reset(true); await pager.more();
  assert.equal(pager.state.error, 'offline');
  assert.equal(pager.state.items?.length, 1);
  await pager.retry();
  assert.deepEqual(cursors, [undefined, 'p2', 'p2']);
  assert.deepEqual(pager.state.items?.map(item => item.id), ['a', 'b']);
});

test("dispose and refresh ignore delayed outbox reads", async () => {
  let finish!: (value: boolean) => void;
  const pager = new ConceptQueuePager(async () => ({ items: [card('a')], nextCursor: null }), () => new Promise(resolve => { finish = resolve; }), () => {});
  const old = pager.reset(false); await Promise.resolve();
  pager.dispose(); finish(true); await old;
  assert.equal(pager.state.items, null);
  await pager.reset(true);
  assert.deepEqual(pager.state.items, [card('a')]);
});
