import test from 'node:test';
import assert from 'node:assert/strict';
import { SentenceRecorder } from '../src/lib/media/recorder.ts';
import type { RecorderState } from '../src/lib/media/recorder.ts';

test('late microphone permission after unmount releases every track and never saves', async () => {
  let resolve!: (stream: MediaStream) => void, stopped = 0, saved = 0;
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: () => new Promise<MediaStream>(r => { resolve = r; }) } } });
  Object.defineProperty(globalThis, 'MediaRecorder', { configurable: true, value: class {} });
  const states: RecorderState[] = [];
  const recorder = new SentenceRecorder(s => states.push(s), async () => { saved++; });
  const promise = recorder.start(); recorder.dispose();
  resolve({ getTracks: () => [{ stop: () => stopped++ }] } as unknown as MediaStream);
  await promise;
  assert.equal(stopped, 1); assert.equal(saved, 0); assert.deepEqual(states, ['requesting_permission']);
});
test('permission denial and absent browser APIs are explicit, never practice evidence', async () => {
  let saved = 0; const states: RecorderState[] = [];
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async () => { throw new DOMException('denied', 'NotAllowedError'); } } } });
  const recorder = new SentenceRecorder(s => states.push(s), async () => { saved++; });
  await recorder.start(); assert.deepEqual(states, ['requesting_permission', 'denied']);
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: {} });
  await recorder.start(); assert.equal(states.at(-1), 'failed'); assert.equal(saved, 0);
});
