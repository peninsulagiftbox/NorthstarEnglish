export type TimelineSentence = { id: string; startMs?: number; endMs?: number; audio: { durationMs: number; sha256?: string } };
export type WordTiming = { text: string; startMs: number; durationMs: number };
export type WordTimingPackage = { versionId: string; tracks: { sentenceId: string; audioSha256: string; durationMs: number; words: WordTiming[] }[] };

export function matchingWords(versionId: string, sentence: TimelineSentence, data: WordTimingPackage): WordTiming[] {
  if (versionId !== data.versionId || (sentence.startMs ?? 0) !== 0 || (sentence.endMs !== undefined && sentence.endMs !== sentence.audio.durationMs)) return [];
  const timing = data.tracks.find(t => t.sentenceId === sentence.id);
  if (!timing || timing.audioSha256 !== sentence.audio.sha256 || timing.durationMs !== sentence.audio.durationMs || !timing.words.length) return [];
  if (timing.words.some((w, i) => !Number.isFinite(w.startMs) || !Number.isFinite(w.durationMs) || w.startMs < 0 || w.durationMs <= 0 || w.startMs + w.durationMs > timing.durationMs + 1 || (i > 0 && w.startMs <= timing.words[i - 1].startMs))) return [];
  return timing.words;
}

/** Align punctuation to the same ordered words, then use the final word's end, not its start. */
export function sentenceEndPoints(text: string, words: WordTiming[]) {
  const tokens = [...text.matchAll(/[a-z]+(?:['’][a-z]+)*/gi)];
  const normalize = (value: string) => value.toLowerCase().replaceAll('’', "'");
  if (!words.length || tokens.length !== words.length || tokens.some((token, i) => normalize(token[0]) !== normalize(words[i].text))) return [];
  return tokens.flatMap((token, wordIndex) => {
    const punctuation = text.slice(token.index! + token[0].length, tokens[wordIndex + 1]?.index ?? text.length);
    return /[.!?]/.test(punctuation) ? [{ wordIndex, endMs: words[wordIndex].startMs + words[wordIndex].durationMs }] : [];
  });
}

export function clockTime(time: number) {
  const seconds = Number.isFinite(time) ? Math.max(0, Math.floor(time)) : 0;
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}
