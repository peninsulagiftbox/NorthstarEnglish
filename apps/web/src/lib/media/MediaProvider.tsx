'use client';
import { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { AudioController, ignoreShortcut, initialMedia } from './AudioController';
import type { MediaState } from './AudioController';
const Context = createContext<{ controller: AudioController | null; media: MediaState; captureBusy: boolean; setCaptureBusy: (busy: boolean) => void } | null>(null);
export function useMedia() { const value = useContext(Context); if (!value) throw new Error('MediaProvider required'); return value; }
export function MediaProvider({ children }: { children: ReactNode }) {
  const { preferences, lesson, checkpoint, playback, savePlayback, update } = useLesson();
  const [captureBusy, setCaptureBusy] = useState(false);
  const audio = useRef<HTMLAudioElement>(null);
  const latestMedia = useRef(initialMedia);
  const [controller, setController] = useState<AudioController | null>(null);
  const [media, setMedia] = useState(initialMedia);
  useEffect(() => {
    const full = lesson.audioAssets?.find(a => a.id === lesson.fullAudioAssetId);
    const player = new AudioController(lesson.sentences.map(s => ({ id: s.id, uri: s.audio.uri, assetId: s.audio.id, startMs: s.startMs ?? 0, endMs: s.endMs ?? s.audio.durationMs })), state => { latestMedia.current = state; setMedia(state); }, audio.current!, full ? { assetId: full.id, uri: full.uri, durationMs: full.durationMs } : undefined);
    player.speed(preferences?.defaultSpeed ?? 1);
    setController(player);
    if (playback.playbackMode === 'full' && playback.fullAssetId === full?.id) player.loadFull(playback.assetPositionMs ?? 0);
    else if (playback.playingSentenceId) player.load(playback.playingSentenceId, (playback.positionMs ?? 0) / 1000);
    return () => player.dispose();
    // Restore only once per immutable lesson; subsequent state comes from the element.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lesson]);
  useEffect(() => { controller?.pause(); }, [controller, checkpoint.tab]);
  useEffect(() => {
    const save = () => {
      const state = latestMedia.current;
      if (!state.duration || ['idle', 'loading', 'error'].includes(state.status)) return;
      savePlayback({ playingSentenceId: state.sentenceId, positionMs: Math.floor(state.segmentOffsetMs), playbackCoordinate: 'segment_offset_v1', playbackMode: state.mode === 'full' ? 'full' : 'segment', fullAssetId: state.mode === 'full' ? state.assetId : null, assetPositionMs: state.mode === 'full' ? Math.floor(state.assetTimeMs) : null });
    };
    const visibility = () => { if (document.hidden) { controller?.background(); save(); } };
    const timer = setInterval(save, 1500);
    document.addEventListener('visibilitychange', visibility);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', visibility); save(); };
  }, [controller, savePlayback]);
  useEffect(() => {
    if (media.duration && media.assetDurationMs && ['paused', 'ended'].includes(media.status)) savePlayback({ playingSentenceId: media.sentenceId, positionMs: Math.floor(media.segmentOffsetMs), playbackCoordinate: 'segment_offset_v1', playbackMode: media.mode === 'full' ? 'full' : 'segment', fullAssetId: media.mode === 'full' ? media.assetId : null, assetPositionMs: media.mode === 'full' ? Math.floor(media.assetTimeMs) : null });
  }, [media, savePlayback]);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (preferences?.shortcutEnabled === false || captureBusy || !controller || ignoreShortcut(event)) return;
      const key = event.key.toLowerCase(); if (![' ', 'j', 'k', 'r'].includes(key)) return;
      event.preventDefault();
      if (key === ' ') { controller.toggle(controller.state.sentenceId ?? checkpoint.sentenceId); }
      if (key === 'r') controller.mode(controller.state.mode === 'sentence' ? 'single' : 'sentence');
      if (key === 'j' || key === 'k') {
        const index = lesson.sentences.findIndex(s => s.id === (controller.state.sentenceId ?? checkpoint.sentenceId));
        const sentence = lesson.sentences[Math.max(0, Math.min(lesson.sentences.length - 1, index + (key === 'j' ? -1 : 1)))];
        update({ sentenceId: sentence.id }); void controller.playTrack(sentence.id);
      }
    };
    window.addEventListener('keydown', handler); return () => window.removeEventListener('keydown', handler);
  }, [controller, media, checkpoint.sentenceId, lesson, update, captureBusy, preferences]);
  return <Context.Provider value={{ controller, media, captureBusy, setCaptureBusy }}><audio ref={audio} hidden preload="metadata" />{children}</Context.Provider>;
}
