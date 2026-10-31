import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateLesson } from '../src/lib/api/catalog.ts';
import { lessonVersionHref } from '../src/lib/state/context.ts';
const content = { id: 'other', versionId: 'opaque-version', title: 'Test', paragraphs: [{ id: 'p', sequence: 1 }], sentences: [{ id: 'opaque-sentence', sequence: 1, paragraphId: 'p', text: 'Original text.', audio: { id: 'opaque-audio', uri: '/api/v1/audio/opaque-audio', status: 'ready', durationMs: 2000 } }] };
test('validates real identity and paragraph/audio ownership before rendering', () => {
  assert.equal(validateLesson(content, 'other').id, 'other');
  assert.throws(() => validateLesson(content, 'foreign'));
  assert.throws(() => validateLesson(content, 'other', 'old'));
  assert.throws(() => validateLesson({ ...content, sentences: [content.sentences[0], content.sentences[0]] }, 'other'));
  assert.throws(() => validateLesson({ ...content, paragraphs: [] }, 'other'));
  assert.throws(() => validateLesson({ ...content, sentences: [{ ...content.sentences[0], audio: { id: 'a', uri: 'https://outside/audio', status: 'ready', durationMs: 2000 } }] }, 'other'));
});
test('generic version links do not invent cross-version sentence identities', () => {
  const href = lessonVersionHref({ lessonId: 'other', versionId: 'opaque-version', sentenceId: 'opaque-version-s1', tab: 'text', showEnglish: true, showTranslation: false }, 'new-opaque');
  const url = new URL(href, 'http://localhost');
  assert.equal(url.searchParams.get('version'), 'new-opaque');
  assert.equal(url.searchParams.get('sentence'), '');
});

test('rejects unknown lifecycle, source types and duplicate stable identities', () => {
  assert.equal(validateLesson({ ...content, kind: 'original', publicationState: 'published', contentReadiness: 'basic_content' }, 'other').publicationState, 'published');
  for (const extra of [{ publicationState: 'unknown' }, { contentReadiness: 'unknown' }, { kind: 'unknown' }]) assert.throws(() => validateLesson({ ...content, ...extra }, 'other'));
  assert.throws(() => validateLesson({ ...content, sentences: [1, 2].map(n => ({ ...content.sentences[0], id: `physical-${n}`, identityId: 'same-stable' })) }, 'other'));
  assert.throws(() => validateLesson({ ...content, sentences: [{ ...content.sentences[0], audio: { ...content.sentences[0].audio, sourceKind: 'unknown' } }] }, 'other'));
});

test('shared intervals accept gaps, unavailable audio keeps text, and overlap/NaN reject', () => {
  const first={...content.sentences[0],startMs:200,endMs:700};
  const second={...first,id:'second',sequence:2,startMs:900,endMs:1900};
  assert.equal(validateLesson({...content,sentences:[first,second]},'other').sentences.length,2);
  assert.equal(validateLesson({...content,sentences:[{...first,audio:{...first.audio,status:'unavailable',code:'AUDIO_UNAVAILABLE'}}]},'other').sentences[0].text,'Original text.');
  for(const startMs of [600,NaN,-1])assert.throws(()=>validateLesson({...content,sentences:[first,{...second,startMs}]},'other'));
  assert.throws(()=>validateLesson({...content,fullAudioAssetId:'foreign'},'other'));
});
