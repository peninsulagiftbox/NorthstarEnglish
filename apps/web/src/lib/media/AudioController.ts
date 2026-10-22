export type Track = { id: string; uri: string };
export type MediaState = { sentenceId: string | null; status: 'idle' | 'loading' | 'playing' | 'paused' | 'ended' | 'error'; duration: number; time: number; speed: number; mode: 'single' | 'sequence' | 'sentence' | 'list'; a: number | null; b: number | null; ab: boolean; error: string; played: string[] };
export const initialMedia: MediaState = { sentenceId: null, status: 'idle', duration: 0, time: 0, speed: 1, mode: 'single', a: null, b: null, ab: false, error: '', played: [] };
export function validAB(a: number | null, b: number | null, duration: number) { return a !== null && b !== null && Number.isFinite(a) && Number.isFinite(b) && a >= 0 && a < b && b <= duration; }
export function ignoreShortcut(event: { target: EventTarget | null; isComposing: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean; repeat: boolean }) {
  return event.isComposing || event.ctrlKey || event.metaKey || event.altKey || event.repeat || (event.target instanceof Element && !!event.target.closest('input,textarea,select,button,a,[contenteditable="true"],[role="slider"],[role="tab"]'));
}
/** One element, one local file timeline. Tokens invalidate pending play requests. */
export class AudioController {
  readonly audio: HTMLAudioElement;
  state: MediaState = initialMedia;
  private token = 0;
  private cleanup = () => {};
  private frame = 0;
  private tracks: Track[];
  private change: (state: MediaState) => void;
  constructor(tracks: Track[], change: (state: MediaState) => void, audio?: HTMLAudioElement) {
    this.tracks = tracks; this.change = change;
    this.audio = audio ?? new Audio(); this.audio.preload = 'metadata';
  }
  private emit(patch: Partial<MediaState>) { this.state = { ...this.state, ...patch }; this.change(this.state); }
  private monitor = () => {
    if (this.state.ab && validAB(this.state.a, this.state.b, this.state.duration) && this.audio.currentTime >= this.state.b!) this.audio.currentTime = this.state.a!;
    this.emit({ time: this.audio.currentTime });
  };
  private tick = () => { this.monitor(); if (!this.audio.paused) this.frame = requestAnimationFrame(this.tick); };
  load(id: string, time = 0) {
    const track = this.tracks.find(t => t.id === id); if (!track) return;
    const token = ++this.token;
    cancelAnimationFrame(this.frame); this.cleanup(); this.audio.pause();
    this.emit({ sentenceId: id, status: 'loading', time: 0, duration: 0, a: null, b: null, ab: false, error: '' });
    const listen = (type: string, fn: () => void) => { const handler = () => { if (token === this.token) fn(); }; this.audio.addEventListener(type, handler); return () => this.audio.removeEventListener(type, handler); };
    const off = [listen('loadedmetadata', () => {
      if (!Number.isFinite(this.audio.duration) || this.audio.duration <= 0) { this.fail('无法读取可靠的音频时长。'); return; }
      this.audio.currentTime = Math.min(Math.max(0, time), this.audio.duration);
      this.emit({ duration: this.audio.duration, time: this.audio.currentTime, status: this.audio.paused ? 'paused' : 'playing' });
    }), listen('playing', () => { this.emit({ status: 'playing', error: '', played: [...new Set([...this.state.played, id])] }); cancelAnimationFrame(this.frame); this.tick(); }),
    listen('pause', () => { cancelAnimationFrame(this.frame); if (this.state.status !== 'error' && this.state.status !== 'ended') this.emit({ status: 'paused', time: this.audio.currentTime }); }),
    listen('timeupdate', this.monitor), listen('error', () => this.fail('音频加载或解码失败，请检查本地音源后重试。')),
    listen('ended', () => {
      cancelAnimationFrame(this.frame);
      if (this.state.ab || this.state.mode === 'sentence') { this.seek(this.state.ab ? this.state.a! : 0); void this.play(); return; }
      const index = this.tracks.findIndex(t => t.id === id);
      if (this.state.mode === 'list' || (this.state.mode === 'sequence' && index < this.tracks.length - 1)) { void this.playTrack(this.tracks[(index + 1) % this.tracks.length].id); }
      else this.emit({ status: 'ended', time: this.audio.currentTime });
    })];
    this.cleanup = () => off.forEach(fn => fn());
    this.audio.src = track.uri; this.audio.playbackRate = this.state.speed; this.audio.preservesPitch = true; this.audio.load();
  }
  async playTrack(id: string) { if (id !== this.state.sentenceId || this.state.status === 'error') this.load(id); await this.play(); }
  async play() {
    const token = this.token;
    try { await this.audio.play(); } catch (e) { if (token === this.token && !(e instanceof DOMException && e.name === 'AbortError' && this.audio.paused)) this.fail('播放被浏览器拒绝或音源不可用，请点击播放重试。'); }
  }
  toggle(id: string) { if (this.audio.paused) void this.playTrack(id); else this.pause(); }
  pause() { this.audio.pause(); if (['loading', 'playing'].includes(this.state.status)) this.emit({ status: 'paused', time: this.audio.currentTime }); }
  seek(time: number) { if (!this.state.duration || !Number.isFinite(time)) return; this.audio.currentTime = Math.min(this.state.duration, Math.max(0, time)); this.monitor(); }
  /** Keep pause/play intent and pass cross-file offsets to loadedmetadata, never seek the old source. */
  seekTrack(id: string, time: number) {
    if (!Number.isFinite(time) || !this.tracks.some(t => t.id === id)) return;
    const resume = !this.audio.paused;
    this.setAB(null, null);
    if (id !== this.state.sentenceId || !this.state.duration || this.state.status === 'error') this.load(id, time);
    else this.seek(time);
    if (resume) void this.play();
  }
  speed(speed: number) { if (![0.75, 1, 1.25, 1.5].includes(speed)) return; this.audio.playbackRate = speed; this.emit({ speed }); }
  mode(mode: MediaState['mode']) { this.emit({ mode }); }
  setAB(a: number | null, b: number | null) { this.emit({ a, b, ab: false }); }
  loopAB() { if (validAB(this.state.a, this.state.b, this.state.duration)) { this.emit({ ab: !this.state.ab }); if (this.state.ab) this.seek(this.state.a!); } }
  private fail(error: string) { this.audio.pause(); cancelAnimationFrame(this.frame); this.emit({ status: 'error', error, played: this.state.played.filter(id => id !== this.state.sentenceId) }); }
  dispose() { ++this.token; this.cleanup(); cancelAnimationFrame(this.frame); this.audio.pause(); this.audio.removeAttribute('src'); this.audio.load(); }
}
