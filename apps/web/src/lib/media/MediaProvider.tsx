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
    const player = new AudioController(lesson.sentences.map(s => ({ id: s.id, uri: s.audio.uri })), state => { latestMedia.current = state; setMedia(state); }, audio.current!);
    player.speed(preferences?.defaultSpeed ?? 1);
    setController(player);
    if (playback.playingSentenceId) player.load(playback.playingSentenceId, (playback.positionMs ?? 0) / 1000);
    return () => player.dispose();
    // Restore only once per immutable lesson; subsequent state comes from the element.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lesson]);
  useEffect(() => { controller?.pause(); }, [controller, checkpoint.tab]);
  useEffect(() => {
    const save = () => { const state = latestMedia.current; if (state.sentenceId && state.duration && state.status !== 'loading') savePlayback(state.sentenceId, Math.floor(state.time * 1000)); };
    const timer = setInterval(save, 1500); return () => { clearInterval(timer); save(); };
  }, [savePlayback]);
  useEffect(() => {
    if (media.sentenceId && media.duration && ['paused', 'ended'].includes(media.status)) savePlayback(media.sentenceId, Math.floor(media.time * 1000));
  }, [media.sentenceId, media.status, media.time, media.duration, savePlayback]);
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
