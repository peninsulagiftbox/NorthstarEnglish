export type Track = { id: string; uri: string; assetId?: string; startMs?: number; endMs?: number };
export type FullTrack = { assetId: string; uri: string; durationMs: number };
export type MediaState = { sentenceId: string | null; assetId: string | null; status: 'idle' | 'loading' | 'playing' | 'paused' | 'ended' | 'error'; assetTimeMs: number; assetDurationMs: number; segmentOffsetMs: number; segmentDurationMs: number; duration: number; time: number; speed: number; mode: 'single' | 'sequence' | 'sentence' | 'list' | 'full'; a: number | null; b: number | null; ab: boolean; error: string; played: string[] };
// time/duration are UI seconds: segment in sentence modes, asset in full mode.
export const initialMedia: MediaState = { sentenceId: null, assetId: null, status: 'idle', assetTimeMs: 0, assetDurationMs: 0, segmentOffsetMs: 0, segmentDurationMs: 0, duration: 0, time: 0, speed: 1, mode: 'single', a: null, b: null, ab: false, error: '', played: [] };
export function validAB(a: number | null, b: number | null, duration: number) { return a !== null && b !== null && Number.isFinite(a) && Number.isFinite(b) && Number.isFinite(duration) && a >= 0 && a < b && b <= duration; }
export function ignoreShortcut(event: { target: EventTarget | null; isComposing: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean; repeat: boolean }) {
  return event.isComposing || event.ctrlKey || event.metaKey || event.altKey || event.repeat || (event.target instanceof Element && !!event.target.closest('input,textarea,select,button,a,[contenteditable="true"],[role="slider"],[role="tab"]'));
}
/** One element. Generation guards loads/seeks; intent guards late play promises and pause during loading. */
export class AudioController {
  readonly audio: HTMLAudioElement;
  state: MediaState = { ...initialMedia };
  private token = 0;
  private intent = 0;
  private wantsPlay = false;
  private cleanup = () => {};
  private frame = 0;
  private ready: Promise<boolean> = Promise.resolve(false);
  private track: Track | null = null;
  private source: string | null = null;
  private finishing = false;
  private tracks: Track[];
  private change: (state: MediaState) => void;
  readonly fullTrack?: FullTrack;
  constructor(tracks: Track[], change: (state: MediaState) => void, audio?: HTMLAudioElement, fullTrack?: FullTrack) {
    this.tracks = tracks; this.change = change; this.fullTrack = fullTrack;
    this.audio = audio ?? new Audio(); this.audio.preload = 'metadata';
  }
  private emit(patch: Partial<MediaState>) { this.state = { ...this.state, ...patch }; this.change(this.state); }
  private bounds() { return { start: this.track?.startMs ?? 0, end: this.track?.endMs ?? this.state.assetDurationMs }; }
  private monitor = () => {
    const full = this.state.mode === 'full';
    const rawAssetTimeMs = Math.max(0, this.audio.currentTime * 1000);
    const assetTimeMs = full && this.state.assetDurationMs ? Math.min(rawAssetTimeMs, this.state.assetDurationMs) : rawAssetTimeMs;
    const active = full ? this.tracks.find(t => (t.assetId ?? t.id) === this.state.assetId && assetTimeMs >= (t.startMs ?? 0) && assetTimeMs < (t.endMs ?? 0)) : this.track;
    const { start, end } = full ? { start: active?.startMs ?? 0, end: active?.endMs ?? 0 } : this.bounds();
    const segmentDurationMs = end - start;
    const segmentOffsetMs = active ? Math.max(0, Math.min(segmentDurationMs, assetTimeMs - start)) : 0;
    this.emit({ assetTimeMs, segmentOffsetMs, segmentDurationMs, sentenceId: active?.id ?? null,
      time: (full ? assetTimeMs : segmentOffsetMs) / 1000, duration: (full ? this.state.assetDurationMs : segmentDurationMs) / 1000,
      played: !this.audio.paused && active && assetTimeMs > start ? [...new Set([...this.state.played, active.id])] : this.state.played });
    if (this.audio.paused || this.audio.seeking || this.state.status === 'loading' || this.finishing) return;
    if (full) { if (rawAssetTimeMs >= this.state.assetDurationMs) this.endSegment(); return; }
    if (this.state.ab && validAB(this.state.a, this.state.b, segmentDurationMs / 1000) && segmentOffsetMs >= this.state.b! * 1000) { this.jump(this.state.a!); return; }
    if (assetTimeMs >= end) this.endSegment();
  };
  private tick = () => { this.monitor(); if (!this.audio.paused) this.frame = requestAnimationFrame(this.tick); };
  private endSegment() {
    if (this.finishing) return;
    this.finishing = true; cancelAnimationFrame(this.frame);
    if (this.state.ab || this.state.mode === 'sentence') { this.jump(this.state.ab ? this.state.a! : 0); this.finishing = false; return; }
    const index = this.tracks.findIndex(t => t.id === this.track?.id);
    if (this.state.mode === 'list' || (this.state.mode === 'sequence' && index >= 0 && index < this.tracks.length - 1)) {
      void this.playTrack(this.tracks[(index + 1) % this.tracks.length].id);
    } else {
      this.pause();
      if (this.state.mode !== 'full') this.audio.currentTime = this.bounds().end / 1000;
      this.monitor(); this.emit({ status: 'ended' });
    }
    this.finishing = false;
  }
  private prepare(track: Track, offsetMs: number) {
    const token = ++this.token; ++this.intent; this.wantsPlay = false;
    cancelAnimationFrame(this.frame); this.cleanup(); this.audio.pause(); this.track = track;
    const reuse = this.source === track.uri && this.audio.readyState >= 1;
    this.emit({ sentenceId: this.state.mode === 'full' ? null : track.id, assetId: track.assetId ?? track.id, status: 'loading', time: 0, duration: 0, assetTimeMs: 0, assetDurationMs: 0, segmentOffsetMs: 0, segmentDurationMs: 0, a: null, b: null, ab: false, error: '' });
    let resolve!: (ready: boolean) => void;
    this.ready = new Promise<boolean>(r => { resolve = r; });
    let positioned = false, metadata = false;
    const finishSeek = () => {
      if (!metadata || positioned || this.audio.seeking) return;
      positioned = true; this.emit({ status: 'paused' }); this.monitor(); resolve(true);
    };
    const onMetadata = () => {
      if (metadata) return;
      metadata = true;
      if (!Number.isFinite(this.audio.duration) || this.audio.duration <= 0) { resolve(false); this.fail('无法读取可靠的音频时长。'); return; }
      const durationMs = Math.round(this.audio.duration * 1000), start = track.startMs ?? 0, end = track.endMs ?? durationMs;
      if (start < 0 || end <= start || end > durationMs + 1) { resolve(false); this.fail('句子时间范围超出实际音轨。'); return; }
      this.emit({ assetDurationMs: this.state.mode === 'full' ? Math.min(end, durationMs) : durationMs });
      this.audio.currentTime = (start + Math.max(0, Math.min(end - start, offsetMs))) / 1000;
      finishSeek();
    };
    const listen = (type: string, fn: () => void) => { const handler = () => { if (token === this.token) fn(); }; this.audio.addEventListener(type, handler); return () => this.audio.removeEventListener(type, handler); };
    const off = [listen('loadedmetadata', onMetadata), listen('seeked', finishSeek),
      listen('playing', () => {
        if (!positioned || !this.wantsPlay) { this.audio.pause(); return; }
        this.emit({ status: 'playing', error: '' }); cancelAnimationFrame(this.frame); this.tick();
      }), listen('pause', () => { cancelAnimationFrame(this.frame); if (!['error', 'ended', 'loading'].includes(this.state.status)) { this.monitor(); this.emit({ status: 'paused' }); } }),
      listen('timeupdate', this.monitor), listen('error', () => { resolve(false); this.fail('音频加载或解码失败，请恢复音源后重试。'); }),
      listen('ended', () => { if (positioned && this.wantsPlay) this.endSegment(); })];
    this.cleanup = () => { resolve(false); off.forEach(fn => fn()); };
    this.audio.playbackRate = this.state.speed; this.audio.preservesPitch = true;
    if (reuse) onMetadata(); else { this.source = track.uri; this.audio.src = track.uri; this.audio.load(); }
  }
  load(id: string, segmentOffsetSeconds = 0) {
    const track = this.tracks.find(t => t.id === id); if (!track || !Number.isFinite(segmentOffsetSeconds)) return;
    if (this.state.mode === 'full') this.emit({ mode: 'single' });
    this.prepare(track, segmentOffsetSeconds * 1000);
  }
  loadFull(assetPositionMs = 0) {
    if (!this.fullTrack || !Number.isFinite(assetPositionMs)) return;
    this.emit({ mode: 'full' });
    this.prepare({ id: '', assetId: this.fullTrack.assetId, uri: this.fullTrack.uri, startMs: 0, endMs: this.fullTrack.durationMs }, assetPositionMs);
  }
  async playTrack(id: string) { if (this.state.mode === 'full' || id !== this.state.sentenceId || this.state.status === 'error') this.load(id); await this.play(); }
  async play() {
    const token = this.token, intent = ++this.intent; this.wantsPlay = true;
    if (!await this.ready || token !== this.token || intent !== this.intent || !this.wantsPlay) return;
    if (this.state.status === 'ended' || (this.state.mode !== 'full' && this.state.segmentOffsetMs >= this.state.segmentDurationMs)) this.jump(0);
    try { await this.audio.play(); }
    catch (error) { if (token === this.token && intent === this.intent && this.wantsPlay && !(error instanceof DOMException && error.name === 'AbortError')) this.fail('播放被浏览器拒绝或音源不可用，请点击播放重试。'); }
  }
  toggle(id: string) {
    if (this.wantsPlay || !this.audio.paused) this.pause();
    else if (this.state.mode === 'full') void this.play();
    else void this.playTrack(id);
  }
  pause() { ++this.intent; this.wantsPlay = false; this.audio.pause(); cancelAnimationFrame(this.frame); if (['loading', 'playing'].includes(this.state.status)) this.emit({ status: 'paused' }); this.monitor(); }
  private jump(seconds: number) {
    const start = this.state.mode === 'full' ? 0 : this.bounds().start;
    this.audio.currentTime = (start + seconds * 1000) / 1000;
    this.monitor();
  }
  seek(time: number) { if (!this.state.duration || !Number.isFinite(time)) return; this.jump(Math.min(this.state.duration, Math.max(0, time))); }
  seekTrack(id: string, time: number) {
    if (!Number.isFinite(time) || !this.tracks.some(t => t.id === id)) return;
    const resume = this.wantsPlay || !this.audio.paused;
    this.setAB(null, null);
    if (this.state.mode === 'full' || id !== this.state.sentenceId || !this.state.duration || this.state.status === 'error') this.load(id, time);
    else this.seek(time);
    if (resume) void this.play();
  }
  speed(speed: number) { if (![0.75, 1, 1.25, 1.5].includes(speed)) return; this.audio.defaultPlaybackRate = speed; this.audio.playbackRate = speed; this.emit({ speed }); }
  mode(mode: MediaState['mode']) {
    if (mode === 'full') { const resume = this.wantsPlay; this.loadFull(); if (resume) void this.play(); return; }
    const wasFull = this.state.mode === 'full', id = this.state.sentenceId ?? this.tracks[0]?.id;
    this.emit({ mode }); if (wasFull && id) this.load(id);
  }
  setAB(a: number | null, b: number | null) { this.emit({ a, b, ab: false }); }
  loopAB() { if (this.state.mode !== 'full' && validAB(this.state.a, this.state.b, this.state.duration)) { this.emit({ ab: !this.state.ab }); if (this.state.ab) this.seek(this.state.a!); } }
  background() { if (this.state.mode !== 'full') this.pause(); }
  private fail(error: string) { this.pause(); this.emit({ status: 'error', error, played: this.state.played.filter(id => id !== this.state.sentenceId) }); }
  dispose() { ++this.token; ++this.intent; this.wantsPlay = false; this.cleanup(); cancelAnimationFrame(this.frame); this.audio.pause(); this.audio.removeAttribute('src'); this.audio.load(); }
}
