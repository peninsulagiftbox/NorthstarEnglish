import test from 'node:test';
import assert from 'node:assert/strict';
import { AudioController, validAB } from '../src/lib/media/AudioController.ts';
class FakeAudio extends EventTarget {
  src=''; currentTime=0; duration=3.2; playbackRate=1; preservesPitch=true; preload=''; paused=true;
  reject: Error | null=null;
  play() { if(this.reject) return Promise.reject(this.reject); this.paused=false; this.dispatchEvent(new Event('playing'));return Promise.resolve(); }
  pause() { this.paused=true;this.dispatchEvent(new Event('pause')); }
  load() {} removeAttribute() {} emit(name: string) { this.dispatchEvent(new Event(name)); }
}
globalThis.requestAnimationFrame=()=>1;globalThis.cancelAnimationFrame=()=>{};
test('AB validates finite local bounds', () => {
  for(const [a,b,d] of [[-1,2,3],[1,1,3],[1,4,3],[0,2,NaN]]) assert.equal(validAB(a,b,d),false);
  assert.equal(validAB(0,2,3),true);assert.equal(validAB(null,2,3),false);
});
test('selection, real seek, speed, AB priority and source cleanup', async () => {
  const audio=new FakeAudio();const player=new AudioController([{id:'one',uri:'/one'},{id:'two',uri:'/two'}],()=>{},audio as unknown as HTMLAudioElement);
  await player.playTrack('one');audio.emit('loadedmetadata');player.seek(2);assert.equal(audio.currentTime,2);
  player.speed(1.5);assert.equal(audio.playbackRate,1.5);
  player.setAB(.2,1);player.loopAB();audio.currentTime=1.1;audio.emit('timeupdate');assert.equal(audio.currentTime,.2);
  player.mode('list');audio.emit('ended');assert.equal(player.state.sentenceId,'one');
  await player.playTrack('two');assert.equal(player.state.ab,false);assert.equal(player.state.a,null);assert.equal(audio.src,'/two');
  audio.emit('loadedmetadata');player.seek(100);assert.equal(audio.currentTime,3.2);
  player.dispose();assert.equal(audio.paused,true);
});
test('late promise rejection cannot corrupt a newer source; failed playback is not evidence', async () => {
  const audio=new FakeAudio();let reject!: (reason: Error)=>void;
  audio.play=()=>new Promise<void>((_,r)=>{reject=r;});
  const player=new AudioController([{id:'one',uri:'/one'},{id:'two',uri:'/two'}],()=>{},audio as unknown as HTMLAudioElement);
  const pending=player.playTrack('one');player.load('two');reject(new Error('old failure'));await pending;assert.equal(player.state.status,'loading');assert.equal(player.state.sentenceId,'two');
  audio.emit('error');assert.equal(player.state.status,'error');assert.deepEqual(player.state.played,[]);player.dispose();
});

test('toggle during a pending source uses actual paused state', async () => {
  const audio=new FakeAudio();
  audio.play=()=>{audio.paused=false;return new Promise<void>(()=>{});};
  const player=new AudioController([{id:'one',uri:'/one'}],()=>{},audio as unknown as HTMLAudioElement);
  player.toggle('one');assert.equal(audio.paused,false);assert.equal(player.state.status,'loading');
  player.toggle('one');assert.equal(audio.paused,true);assert.equal(player.state.status,'paused');player.dispose();
});

test('cross-file seek restores offsets on metadata, preserves pause intent, and cancels AB', async () => {
  const audio=new FakeAudio();const player=new AudioController([{id:'one',uri:'/one'},{id:'two',uri:'/two'}],()=>{},audio as unknown as HTMLAudioElement);
  player.load('one');audio.emit('loadedmetadata');player.setAB(.2,1);player.loopAB();
  player.seekTrack('two',1.25);assert.equal(audio.paused,true);assert.equal(player.state.ab,false);
  audio.emit('loadedmetadata');assert.equal(audio.currentTime,1.25);
  await player.play();player.seekTrack('one',.4);audio.emit('loadedmetadata');assert.equal(audio.paused,false);assert.equal(audio.currentTime,.4);
  player.pause();player.seekTrack('two',2);player.seekTrack('one',.7);audio.emit('loadedmetadata');assert.equal(audio.currentTime,.7);assert.equal(player.state.sentenceId,'one');
  player.dispose();
});
