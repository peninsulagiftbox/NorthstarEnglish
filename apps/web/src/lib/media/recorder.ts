export type RecorderState = 'idle' | 'requesting_permission' | 'recording' | 'processing' | 'ready' | 'failed' | 'denied';
/** One capture owns its stream. dispose also handles a permission prompt resolving late. */
export class SentenceRecorder {
  private stream: MediaStream | null = null;
  private recorder: MediaRecorder | null = null;
  private disposed = false;
  private started = 0;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private state: (value: RecorderState, message?: string) => void;
  private saved: (blob: Blob, durationMs: number) => Promise<void>;
  constructor(state: (value: RecorderState, message?: string) => void, saved: (blob: Blob, durationMs: number) => Promise<void>) { this.state = state; this.saved = saved; }
  async start() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') { this.state('failed', '浏览器不支持录音；请使用 localhost 上的现代浏览器，或跳过。'); return; }
    this.state('requesting_permission');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (this.disposed) { stream.getTracks().forEach(t => t.stop()); return; }
      this.stream = stream;
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus'].find(mime => MediaRecorder.isTypeSupported(mime));
      if (!mimeType) throw new Error('没有受支持的录音格式。');
      const recorder = new MediaRecorder(stream, { mimeType }); this.recorder = recorder;
      const chunks: Blob[] = [];
      let broken = false;
      recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      recorder.onerror = () => { broken = true; this.release(); if (!this.disposed) this.state('failed', '录制失败，请检查设备后重试。'); };
      stream.getTracks().forEach(t => { t.onended = () => { broken = true; this.stop(); if (!this.disposed) this.state('failed', '麦克风已断开，请重试或跳过。'); }; });
      recorder.onstop = async () => {
        const duration = Math.min(120000, Math.round(performance.now() - this.started)); this.release();
        if (this.disposed || broken) return;
        if (duration < 250 || !chunks.length) { this.state('failed', '录音过短，请至少录制片刻再停止。'); return; }
        this.state('processing');
        try { await this.saved(new Blob(chunks, { type: recorder.mimeType }), duration); if (!this.disposed) this.state('ready'); }
        catch (error) { if (!this.disposed) this.state('failed', error instanceof Error ? error.message : '录音保存失败。'); }
      };
      this.started = performance.now(); recorder.start(); this.timer = setTimeout(() => this.stop(), 120000); this.state('recording');
    } catch (error) {
      this.release(); if (!this.disposed) this.state(error instanceof DOMException && error.name === 'NotAllowedError' ? 'denied' : 'failed', error instanceof DOMException && error.name === 'NotAllowedError' ? '麦克风权限被拒绝。可在浏览器设置中允许后重试，或暂时跳过。' : error instanceof DOMException && error.name === 'NotFoundError' ? '未找到麦克风设备，请连接设备后重试或跳过。' : error instanceof DOMException && error.name === 'NotReadableError' ? '麦克风无法读取，可能正被其他应用占用，请检查后重试。' : error instanceof Error ? error.message : '无法使用麦克风，请检查设备和安全上下文后重试。');
    }
  }
  stop() { if (this.recorder?.state === 'recording') this.recorder.stop(); }
  private release() { clearTimeout(this.timer); this.stream?.getTracks().forEach(t => { t.onended = null; t.stop(); }); this.stream = null; }
  dispose() { this.disposed = true; this.stop(); this.release(); }
}
