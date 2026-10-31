import test from 'node:test';
import assert from 'node:assert/strict';
import { AudioController, validAB } from '../src/lib/media/AudioController.ts';
class FakeAudio extends EventTarget {
  src=''; currentTime=0; duration=20; playbackRate=1; defaultPlaybackRate=1; preservesPitch=true; preload=''; paused=true; seeking=false; readyState=0; loads=0; plays=0;
  reject: Error | null=null;
  play() { ++this.plays; if(this.reject) return Promise.reject(this.reject); this.paused=false; this.dispatchEvent(new Event('playing'));return Promise.resolve(); }
  pause() { this.paused=true;this.dispatchEvent(new Event('pause')); }
  load() { ++this.loads; this.readyState=0; this.playbackRate=this.defaultPlaybackRate; } removeAttribute() { this.src=''; } emit(name: string) { if(name==='loadedmetadata')this.readyState=1;this.dispatchEvent(new Event(name)); }
}
globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
const tracks=[{id:'one',assetId:'shared',uri:'/shared',startMs:8400,endMs:12100},{id:'two',assetId:'shared',uri:'/shared',startMs:13000,endMs:15000},{id:'three',assetId:'independent',uri:'/three',startMs:0,endMs:2000}];
function setup() { const audio=new FakeAudio(); const player=new AudioController(tracks,()=>{},audio as unknown as HTMLAudioElement,{assetId:'shared',uri:'/shared',durationMs:20000});return {audio,player}; }
async function flush() { await Promise.resolve();await Promise.resolve(); }
async function start(player: AudioController,audio: FakeAudio,id='one') { const p=player.playTrack(id);audio.emit('loadedmetadata');await p; }
test('AB rejects invalid local bounds and NaN duration',()=>{
  for(const [a,b,d] of [[-1,2,3],[1,1,3],[1,4,3],[0,2,NaN]])assert.equal(validAB(a,b,d),false);
  assert.equal(validAB(0,2,3),true);assert.equal(validAB(null,2,3),false);
});
test('nonzero start uses asset=8400+1500 and exposes only 1500 as offset',async()=>{
  const {audio,player}=setup();player.load('one',1.5);audio.emit('loadedmetadata');assert.equal(audio.currentTime,9.9);assert.equal(player.state.segmentOffsetMs,1500);assert.equal(player.state.segmentDurationMs,3700);assert.equal(player.state.time,1.5);
  await player.play();audio.currentTime=10;audio.emit('timeupdate');assert.deepEqual(player.state.played,['one']);player.seek(100);assert.equal(audio.currentTime,12.1);assert.equal(player.state.status,'ended');player.dispose();
});
test('same asset reuses source; independent assets load separately and preserve speed',async()=>{
  const {audio,player}=setup();await start(player,audio);player.speed(1.5);await player.playTrack('two');assert.equal(audio.loads,1);assert.equal(audio.currentTime,13);assert.equal(audio.playbackRate,1.5);
  const next=player.playTrack('three');assert.equal(audio.paused,true);audio.emit('loadedmetadata');await next;assert.equal(audio.loads,2);assert.equal(audio.currentTime,0);assert.equal(audio.playbackRate,1.5);player.dispose();
});
test('segment boundaries do not await file ended; sequence advances once and skips silence',async()=>{
  const {audio,player}=setup();await start(player,audio);player.mode('sequence');audio.currentTime=12.11;audio.emit('timeupdate');await flush();assert.equal(player.state.sentenceId,'two');assert.equal(audio.currentTime,13);assert.equal(audio.loads,1);
  audio.emit('timeupdate');assert.equal(player.state.sentenceId,'two');player.dispose();
});
test('10 sentence loops and all four speeds preserve asset coordinates',async()=>{
  for(const speed of [.75,1,1.25,1.5]) { const {audio,player}=setup();await start(player,audio);player.speed(speed);player.mode('sentence');
    for(let i=0;i<10;i++){audio.currentTime=12.11;audio.emit('timeupdate');assert.equal(audio.currentTime,8.4);assert.equal(player.state.sentenceId,'one');}
    assert.equal(audio.loads,1);assert.equal(audio.playbackRate,speed);player.dispose(); }
});
test('AB uses sentence offset and takes priority over sentence/list modes',async()=>{
  const {audio,player}=setup();await start(player,audio);player.mode('list');player.setAB(.2,1);player.loopAB();audio.currentTime=9.5;audio.emit('timeupdate');assert.equal(audio.currentTime,8.6);
  await player.playTrack('two');assert.equal(player.state.ab,false);assert.equal(player.state.a,null);player.dispose();
});
test('pause during metadata/seek wait cancels pending playback',async()=>{
  const {audio,player}=setup();const pending=player.playTrack('one');player.pause();audio.seeking=true;audio.emit('loadedmetadata');assert.equal(audio.plays,0);audio.seeking=false;audio.emit('seeked');await pending;assert.equal(audio.plays,0);assert.equal(audio.paused,true);
  await player.play();assert.equal(audio.paused,false);player.background();assert.equal(audio.paused,true);player.dispose();
});
test('20 rapid switches and delayed old play rejection cannot corrupt newest track',async()=>{
  const {audio,player}=setup();let reject!:(e:Error)=>void;
  audio.play=()=>new Promise<void>((_,r)=>{reject=r;});const old=player.playTrack('one');audio.emit('loadedmetadata');await flush();
  for(let i=0;i<20;i++)player.load(i%2?'two':'three',.5);
  audio.emit('loadedmetadata');reject(new Error('old playback'));await old;assert.equal(player.state.sentenceId,'two');assert.equal(player.state.status,'paused');assert.equal(audio.currentTime,13.5);player.dispose();
});
test('full track retains silence, matches half-open segments, and restores >10 minute asset time',async()=>{
  const {audio,player}=setup();player.loadFull(12500);audio.emit('loadedmetadata');assert.equal(player.state.mode,'full');assert.equal(player.state.sentenceId,null);assert.equal(player.state.assetTimeMs,12500);assert.equal(player.state.segmentOffsetMs,0);
  await player.play();audio.currentTime=13;audio.emit('timeupdate');assert.equal(player.state.sentenceId,'two');assert.equal(player.state.segmentOffsetMs,0);audio.currentTime=15;audio.emit('timeupdate');assert.equal(player.state.sentenceId,null);player.dispose();
  const long=new FakeAudio();long.duration=660;const p=new AudioController([{id:'last',assetId:'long',uri:'/long',startMs:640000,endMs:650000}],()=>{},long as unknown as HTMLAudioElement,{assetId:'long',uri:'/long',durationMs:660000});p.loadFull(645000);long.emit('loadedmetadata');assert.equal(p.state.assetTimeMs,645000);assert.equal(p.state.segmentOffsetMs,5000);assert.equal(long.paused,true);p.dispose();
});
test('cross-file seek stays paused, restores on metadata and clears AB; sentence-end resume restarts',async()=>{
  const {audio,player}=setup();player.load('one');audio.emit('loadedmetadata');player.setAB(.2,1);player.loopAB();player.seekTrack('three',1.25);assert.equal(audio.paused,true);audio.emit('loadedmetadata');assert.equal(audio.currentTime,1.25);assert.equal(player.state.ab,false);
  player.load('one',3.7);audio.emit('loadedmetadata');assert.equal(audio.currentTime,12.1);await player.play();assert.equal(audio.currentTime,8.4);player.dispose();
});
test('decoder/play failures never retain played evidence; invalid ranges reject',async()=>{
  const {audio,player}=setup();player.load('one');audio.emit('loadedmetadata');audio.reject=new Error('blocked');await player.play();assert.equal(player.state.status,'error');assert.deepEqual(player.state.played,[]);player.dispose();
  const a=new FakeAudio();a.duration=1;const p=new AudioController(tracks,()=>{},a as unknown as HTMLAudioElement);p.load('one');a.emit('loadedmetadata');assert.equal(p.state.status,'error');p.dispose();
});

test('full playback ends once at declared asset boundary and stores a bounded resume coordinate', async()=>{
  const {audio,player}=setup();player.loadFull(19500);audio.emit('loadedmetadata');await player.play();audio.currentTime=20.01;audio.emit('timeupdate');assert.equal(player.state.status,'ended');assert.equal(audio.paused,true);assert.equal(player.state.assetTimeMs,20000);await player.play();assert.equal(audio.currentTime,0);player.dispose();
});
