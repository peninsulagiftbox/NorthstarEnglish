import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { clockTime, matchingWords, sentenceEndPoints } from '../src/lib/media/timeline.ts';

test('sentence clock formats short durations and invalid input', () => {
  assert.equal(clockTime(2.904),'0:02');assert.equal(clockTime(61.9),'1:01');assert.equal(clockTime(NaN),'0:00');
});

test('published word boundaries match all ten original audio hashes and refuse stale versions', () => {
  const data=JSON.parse(readFileSync(new URL('../src/lib/media/demo-word-timings.json',import.meta.url),'utf8'));
  const manifest=JSON.parse(readFileSync(new URL('../../../content/demo-01/v2/manifest.json',import.meta.url),'utf8'));
  const lesson=JSON.parse(readFileSync(new URL('../../../content/demo-01/v2/lesson.json',import.meta.url),'utf8'));
  let count=0;
  for(const sentence of lesson.sentences) {
    const asset=manifest.audioAssets.find((a:{id:string})=>a.id===sentence.audioAssetId);
    const s={id:sentence.id,audio:asset};const words=matchingWords(lesson.versionId,s,data);
    count+=words.length;assert.ok(words.length>0);
    assert.equal(words.map(w=>w.text).join(' ').toLowerCase(),sentence.text.replace(/[.,?!]/g,'').toLowerCase());
    assert.deepEqual(matchingWords('demo-01-v1',s,data),[]);
    assert.deepEqual(matchingWords(lesson.versionId,{...s,audio:{...asset,sha256:'changed'}},data),[]);
    assert.deepEqual(matchingWords(lesson.versionId,{...s,audio:{...asset,durationMs:1}},data),[]);
  }
  assert.equal(count,68);assert.equal(data.tracks.length,10);
  assert.deepEqual(matchingWords(data.versionId,{id:data.tracks[0].sentenceId,audio:{durationMs:data.tracks[0].durationMs,sha256:data.tracks[0].audioSha256}},{...data,tracks:[{...data.tracks[0],words:[{text:'bad',startMs:NaN,durationMs:1}]}]}),[]);
});


test('punctuation endpoints use the last word duration and skip commas and unmatched words', () => {
  const data=JSON.parse(readFileSync(new URL('../src/lib/media/demo-word-timings.json',import.meta.url),'utf8'));
  const words=data.tracks.find((t:{sentenceId:string})=>t.sentenceId==='demo-01-v2-s04').words;
  assert.deepEqual(sentenceEndPoints('Nice to meet you, Mia. I am Leo.',words),[{wordIndex:4,endMs:1687.5},{wordIndex:7,endMs:3337.5}]);
  assert.deepEqual(sentenceEndPoints('Nice to meet you, Mia. I am Leo.',[]),[]);
  assert.deepEqual(sentenceEndPoints('Different text.',words),[]);
  assert.deepEqual(sentenceEndPoints('Nice to meet you, Mia, I am Leo',words),[]);
});

test('all original sentence terminators map to word endings, including question and exclamation marks', () => {
  const data=JSON.parse(readFileSync(new URL('../src/lib/media/demo-word-timings.json',import.meta.url),'utf8'));
  const lesson=JSON.parse(readFileSync(new URL('../../../content/demo-01/v2/lesson.json',import.meta.url),'utf8'));
  const counts=[2,2,2,2,1,1,1,2,1,2];
  for(const [i,sentence] of lesson.sentences.entries()) {
    const timing=data.tracks.find((t:{sentenceId:string})=>t.sentenceId===sentence.id);
    const ends=sentenceEndPoints(sentence.text,timing.words);assert.equal(ends.length,counts[i]);
    for(const end of ends){const word=timing.words[end.wordIndex];assert.equal(end.endMs,word.startMs+word.durationMs);assert.ok(end.endMs>word.startMs&&end.endMs<timing.durationMs);}
  }
});
