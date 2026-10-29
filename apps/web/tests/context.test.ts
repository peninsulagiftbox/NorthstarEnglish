import { test } from 'node:test';
import assert from 'node:assert/strict';
import { resolveContext, lessonHref, lessonVersionHref, draftKey, isBlind, tabs } from '../src/lib/state/context.ts';
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

test('lesson links pin the immutable version for historical reviews', () => {
  assert.equal(new URL(lessonHref(resume),'http://localhost').searchParams.get('version'),'v1');
});


test('reviewed mappings preserve task and visibility; absent mappings never infer suffixes', () => {
  for (const version of ['demo-01-v1','demo-01-v2']) for (const [tab] of tabs) for (const showEnglish of [true,false]) for (const showTranslation of [true,false]) {
    const context = { ...resume, versionId: version, sentenceId: `${version}-s06`, tab, showEnglish, showTranslation };
    for (const target of ['demo-01-v1','demo-01-v2']) {
      const url = new URL(lessonVersionHref(context,target,`${target}-s06`),'http://localhost');
      const targetLesson = { id:'demo-01',versionId:target,sentences:[{id:`${target}-s01`},{id:`${target}-s06`}] } as Lesson;
      assert.equal(url.searchParams.get('version'),target);
      assert.deepEqual(resolveContext(targetLesson,url.searchParams,null),{lessonId:context.lessonId,versionId:target,sentenceId:`${target}-s06`,tab,showEnglish,showTranslation:context.showTranslation});
    }
  }
  const url = new URL(lessonVersionHref({...resume,sentenceId:'foreign-sentence'},'demo-01-v2'),'http://localhost');
  assert.equal(url.searchParams.get('sentence'),'');
  const noMap = new URL(lessonVersionHref({ ...resume, versionId: 'demo-01-v1', sentenceId: 'demo-01-v1-s06' }, 'demo-01-v2'), 'http://localhost');
  assert.equal(noMap.searchParams.get('sentence'), '');
});
