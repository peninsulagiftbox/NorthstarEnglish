import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveContext, lessonHref, draftKey, isBlind } from '../src/lib/state/context.ts';
import type { Lesson, Resume } from '../src/lib/api/catalog.ts';
const lesson = { id: 'demo-01', versionId: 'v1', sentences: [{ id: 's1' }, { id: 's2' }] } as Lesson;
const resume = { lessonId: 'demo-01', versionId: 'v1', sentenceId: 's2', tab: 'writing', showEnglish: false, showTranslation: false, rowVersion: 4 } as Resume;
test('restores same-version resume; explicit URL wins and round-trips', () => {
  assert.equal(resolveContext(lesson, new URLSearchParams(), resume).sentenceId, 's2');
  const value = resolveContext(lesson, new URLSearchParams('tab=dictation&sentence=s1&english=1&translation=1'), resume);
  assert.equal(value.tab, 'dictation'); assert.equal(value.sentenceId, 's1');
  assert.deepEqual(resolveContext(lesson, new URL(lessonHref(value), 'http://localhost').searchParams, null), value);
});
test('rejects stale or foreign context and normalizes invalid URL values', () => {
  for (const old of [{ ...resume, versionId: 'old' }, { ...resume, lessonId: 'other' }]) {
    const value = resolveContext(lesson, new URLSearchParams(), old);
    assert.equal(value.sentenceId, 's1'); assert.equal(value.tab, 'text');
  }
  const value = resolveContext(lesson, new URLSearchParams('tab=invalid&sentence=foreign'), resume);
  assert.equal(value.tab, 'text'); assert.equal(value.sentenceId, 's1');
});
test('dictation and blind mode hide target regardless of translation preference', () => {
  assert.equal(isBlind(resume), true);
  assert.equal(isBlind({ ...resume, showEnglish: true, tab: 'dictation' }), true);
  assert.equal(isBlind({ ...resume, showEnglish: true, tab: 'text' }), false);
});
test('drafts are isolated by version, task and sentence; writing stays lesson-wide', () => {
  const value = { ...resume, tab: 'dictation' };
  assert.notEqual(draftKey(value), draftKey({ ...value, sentenceId: 's1' }));
  assert.notEqual(draftKey(value), draftKey({ ...value, versionId: 'v2' }));
  assert.equal(draftKey(resume), draftKey({ ...resume, sentenceId: 's1' }));
});
