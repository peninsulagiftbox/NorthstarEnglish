'use client';
import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { isBlind } from '@/lib/state/context';
import { useMedia } from '@/lib/media/MediaProvider';
import type { MediaState } from '@/lib/media/AudioController';
import { clockTime, matchingWords, sentenceEndPoints } from '@/lib/media/timeline';
import wordTimings from '@/lib/media/demo-word-timings.json';
import { Button } from '@/components/ui/Primitives';
import { PlayerSettings } from './PlayerSettings';
const labels = { idle: '尚未播放', loading: '加载中', playing: '正在播放', paused: '已暂停', ended: '播放结束', error: '播放故障' };
const speeds = [1, 1.25, 1.5, 0.75];
const modes: MediaState['mode'][] = ['single', 'sequence', 'sentence', 'list'];
const modeLabels = { single: '单句停止', sequence: '顺序连播', sentence: '单句循环', list: '列表循环' };
function ControlIcon({ kind }: { kind: 'play' | 'pause' | 'repeat' | 'settings' }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">{kind === 'play' ? <path fill="currentColor" d="M8 4.8a1 1 0 0 1 1.5-.86l11 7.2a1 1 0 0 1 0 1.72l-11 7.2A1 1 0 0 1 8 19.2Z" /> : kind === 'pause' ? <path fill="currentColor" d="M6 5h4v14H6zm8 0h4v14h-4z" /> : <g fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{kind === 'repeat' ? <><path d="M18 3l3 3-3 3M6 21l-3-3 3-3M21 6H8a5 5 0 0 0-5 5m0 7h13a5 5 0 0 0 5-5" /></> : <><path d="M3 7h5m4 0h9M3 17h9m4 0h5" /><circle cx="10" cy="7" r="2" /><circle cx="14" cy="17" r="2" /></>}</g>}</svg>;
}
export function PlayerBar() {
  const { lesson, checkpoint, update } = useLesson();
  const { media, controller } = useMedia();
  const [settingsOpen, setSettingsOpen] = useState(false);
  const sentence = lesson.sentences.find(s => s.id === (media.sentenceId ?? checkpoint.sentenceId))!;
  const words = useMemo(() => matchingWords(lesson.versionId, sentence, wordTimings), [lesson.versionId, sentence]);
  const sentenceEnds = useMemo(() => sentenceEndPoints(sentence.text, words), [sentence.text, words]);
  const duration = media.sentenceId === sentence.id && media.duration > 0 ? media.duration : sentence.audio.durationMs / 1000;
  const time = media.sentenceId === sentence.id ? Math.min(media.time, duration) : 0;
  const playing = media.status === 'playing' || (media.status === 'loading' && !!controller && !controller.audio.paused);
  const blind = isBlind(checkpoint);
  const seek = (time: number) => {
    if (!controller || !Number.isFinite(time)) return;
    const target = Math.max(0, Math.min(duration, time));
    if (target >= duration) controller.pause();
    if (controller.state.sentenceId === sentence.id && controller.state.duration > 0) {
      if (controller.state.ab) controller.loopAB();
      controller.seek(target);
    } else controller.seekTrack(sentence.id, target);
    update({ sentenceId: sentence.id });
  };
  const move = (offset: number) => { const index = lesson.sentences.findIndex(s => s.id === sentence.id); const next = lesson.sentences[Math.max(0, Math.min(lesson.sentences.length - 1, index + offset))]; update({ sentenceId: next.id }); void controller?.playTrack(next.id); };
  useEffect(() => {
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setSettingsOpen(false); } };
    window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close);
  }, []);
  return <><section className="player-bar" aria-label="音频播放器" data-status={media.status} data-mode={media.mode} data-sentence={media.sentenceId ?? ''}>
    <Button className="play-button" aria-label={playing ? '暂停播放' : '播放'} disabled={!controller || !duration} onClick={() => controller?.toggle(sentence.id)}><ControlIcon kind={playing ? 'pause' : 'play'} /></Button>
    <time className="player-time" aria-label="已播放时间">{clockTime(time)}</time>
    <div className="player-track" data-at-end={duration > 0 && time >= duration} style={{ '--progress': `${duration ? time / duration * 100 : 0}%` } as CSSProperties} onPointerDown={event => {
      const target = event.target as Element;
      if (target === event.currentTarget || target.closest('.timeline-thumb,.end-marker')) {
        event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId);
        event.currentTarget.querySelector('input')?.focus({ preventScroll: true });
        const rect = event.currentTarget.getBoundingClientRect();
        seek(target.closest('.end-marker') ? duration : (event.clientX - rect.left) / rect.width * duration);
      }
    }} onPointerMove={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) { const rect = event.currentTarget.getBoundingClientRect(); seek((event.clientX - rect.left) / rect.width * duration); } }} onPointerUp={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); }}>
      <div className="timeline-rail" aria-hidden="true"><span /></div>
      <input type="range" aria-label="当前句播放进度" aria-valuetext={`${clockTime(time)} / ${clockTime(duration)}，第 ${sentence.sequence} 句`} min={0} max={duration || 1} step="any" value={time} disabled={!controller || !duration} onChange={e => seek(Number(e.target.value))} onKeyDown={event => {
        const targets: Record<string, number> = { Home: 0, End: duration, ArrowLeft: time - .1, ArrowDown: time - .1, ArrowRight: time + .1, ArrowUp: time + .1, PageDown: time - 1, PageUp: time + 1 };
        if (event.key in targets) { event.preventDefault(); seek(targets[event.key]); }
      }} />
      <span className="timeline-thumb" aria-hidden="true" style={{ left: `${duration ? time / duration * 100 : 0}%` }} />
      <button type="button" className="timeline-marker sentence-marker" style={{ left: '0%' }} data-time={0} data-sentence={sentence.id} data-passed={time > 0} aria-label={`跳到第 ${sentence.sequence} 句起点`} title={`第 ${sentence.sequence} 句起点 · 0:00`} disabled={!controller} onClick={() => seek(0)}><span /></button>
      {words.map((word, n) => <button key={n} type="button" className="timeline-marker word-marker" style={{ left: `${Math.min(100, word.startMs / 1000 / duration * 100)}%` }} data-time={word.startMs / 1000} data-sentence={sentence.id} data-passed={time >= word.startMs / 1000} aria-label={`跳到第 ${sentence.sequence} 句第 ${n + 1} 个单词`} title={blind ? `第 ${sentence.sequence} 句 · 第 ${n + 1} 个单词` : `${word.text} · ${clockTime(word.startMs / 1000)}`} disabled={!controller} onClick={() => seek(word.startMs / 1000)}><span /></button>)}
      {sentenceEnds.map((point, n) => <button key={point.wordIndex} type="button" className="timeline-marker sentence-end-marker" style={{ left: `${Math.min(100, point.endMs / 1000 / duration * 100)}%` }} data-time={point.endMs / 1000} data-word-index={point.wordIndex} data-sentence={sentence.id} data-passed={time >= point.endMs / 1000} aria-label={`跳到第 ${sentence.sequence} 条音频第 ${n + 1} 个句末`} title={`${blind ? `第 ${n + 1} 个句末` : `${words[point.wordIndex].text} 发音结束`} · ${(point.endMs / 1000).toFixed(2)} 秒`} disabled={!controller} onClick={() => seek(point.endMs / 1000)}><span /></button>)}
      <button type="button" className="timeline-marker end-marker" style={{ left: '100%' }} aria-label="跳到本句终点" title={`音频终点 · ${clockTime(duration)}`} disabled={!controller || !duration} onClick={() => seek(duration)}>终</button>
    </div>
    <time className="player-time" aria-label="当前句时长">{clockTime(duration)}</time>
    <Button className="player-icon repeat-button" aria-label={`播放模式：${modeLabels[media.mode]}，点击切换`} title={modeLabels[media.mode]} aria-pressed={media.mode === 'sentence' || media.mode === 'list'} disabled={!controller} onClick={() => controller?.mode(modes[(modes.indexOf(media.mode) + 1) % modes.length])}><ControlIcon kind="repeat" />{media.mode === 'sentence' && <span className="repeat-one" aria-hidden="true">1</span>}</Button>
    <Button className="player-speed" aria-label="播放速度" title="点击循环切换倍速：1x → 1.25x → 1.5x → 0.75x" data-speed={media.speed} disabled={!controller} onClick={() => controller?.speed(speeds[(speeds.indexOf(media.speed) + 1) % speeds.length])}>{media.speed}x</Button>
    <Button className="player-icon" aria-label="播放设置" title="播放设置" aria-controls="player-settings" aria-expanded={settingsOpen} onClick={() => setSettingsOpen(!settingsOpen)}><ControlIcon kind="settings" /></Button>
    <span className="sr-only" role="status">{labels[media.status]}</span>
  </section>{settingsOpen && <PlayerSettings media={media} controller={controller} sentence={sentence} sentenceCount={lesson.sentences.length} hasWordTimings={words.length > 0} onMove={move} onClose={() => setSettingsOpen(false)} />}{media.error && !settingsOpen && <div className="media-error" role="alert">{media.error}<Button onClick={() => void controller?.playTrack(sentence.id)}>重试播放</Button></div>}</>;
}
