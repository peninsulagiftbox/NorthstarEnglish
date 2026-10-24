'use client';
import { useEffect, useRef, useState } from 'react';
import type { ButtonProps } from '@/components/ui/Primitives';
import { useLesson } from '@/lib/state/LessonProvider';
import { useMedia } from '@/lib/media/MediaProvider';
import { SentenceRecorder } from '@/lib/media/recorder';
import type { RecorderState } from '@/lib/media/recorder';
import { formatBeijingTime, utcTimestamp } from '@/lib/formatTime';
import { isBlind } from '@/lib/state/context';
import { request } from '@/lib/api/catalog';
import { postPractice, stateLabel } from '@/lib/api/practice';
import type { RecordingData } from '@/lib/api/practice';
import { read, write, remove } from '@/lib/persistence/db';
import { enqueue, pendingCommand, deliver } from '@/lib/persistence/outbox';
import type { Command } from '@/lib/persistence/outbox';
import { Button, Message, Modal, Toast } from '@/components/ui/Primitives';

/** Transient requests stay keyboard guarded without dimming every control. */
function RecorderAction({ waiting = false, onClick, ...props }: ButtonProps & { waiting?: boolean }) {
  return <Button {...props} aria-disabled={props.disabled || waiting || undefined} onClick={event => { if (waiting) { event.preventDefault(); return; } onClick?.(event); }} />;
}

type Buffered = { eventId: string; blob: Blob; durationMs: number; createdAt: string };
const labels: Record<RecorderState, string> = { idle: '待录音', requesting_permission: '等待麦克风许可', recording: '正在录音（最长 2 分钟）', processing: '正在保存录音', ready: '录音已保存', failed: '录音处理失败', denied: '麦克风权限被拒绝' };
export function RecorderPanel() {
  const { preferences, lesson, checkpoint } = useLesson();
  const { controller, setCaptureBusy } = useMedia();
  const context = { lessonId: lesson.id, versionId: lesson.versionId, sentenceId: checkpoint.sentenceId };
  const key = `recording:${lesson.versionId}:${checkpoint.sentenceId}`;
  const [state, setState] = useState<RecorderState>('idle'), [data, setData] = useState<RecordingData | null>(null), [error, setError] = useState('');
  const [buffer, setBuffer] = useState<Buffered | null>(null), [busy, setBusy] = useState(false), [deleting, setDeleting] = useState<string | null>(null), [pending, setPending] = useState<Command | null>(null), [discard, setDiscard] = useState(false);
  const recorder = useRef<SentenceRecorder | null>(null), active = useRef(true), lock = useRef(false);
  const players = useRef(new Map<string, HTMLAudioElement>()), observed = useRef(new Map<string, number>()), lastPosition = useRef(new Map<string, number>());
  const counted = useRef(new Set<string>()), lastPlayback = useRef(new Map<string, string>());
  const [ratingStatus, setRatingStatus] = useState('');
  useEffect(() => { if (!ratingStatus) return; const timer = setTimeout(() => setRatingStatus(''), 4000); return () => clearTimeout(timer); }, [ratingStatus]);
  const list = () => request<RecordingData>(`/recordings?${new URLSearchParams(context)}`);
  useEffect(() => {
    active.current = true;
    void Promise.all([list(), read<Buffered>('drafts', key), pendingCommand(key)]).then(([remote, local, cmd]) => { if (active.current) { setData(remote); setBuffer(local ?? null); setPending(cmd ?? null); } }).catch(e => { if (active.current) setError(e.message); });
    const playing = players.current;
    return () => { active.current = false; recorder.current?.dispose(); setCaptureBusy(false); playing.forEach(audio => { audio.pause(); audio.removeAttribute('src'); audio.load(); }); };
    // Each mounted panel owns one immutable sentence target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, setCaptureBusy]);
  async function upload(value: Buffered) {
    const base64 = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve((reader.result as string).split(',')[1]); reader.onerror = () => reject(new Error('无法读取本机录音')); reader.readAsDataURL(value.blob); });
    await postPractice('/recordings', { ...context, eventId: value.eventId, createdAt: value.createdAt, durationMs: value.durationMs, mimeType: value.blob.type, audioBase64: base64 });
    await remove('drafts', key, value.eventId);
    if (active.current) { setBuffer(null); setData(await list()); }
  }
  async function start() {
    if (lock.current) return; lock.current = true; setError('');
    controller?.pause(); players.current.forEach(a => a.pause()); setCaptureBusy(true);
    recorder.current?.dispose();
    recorder.current = new SentenceRecorder((next, message) => { if (active.current) { setState(next); if (message) setError(message); } if (!['requesting_permission', 'recording', 'processing'].includes(next)) { lock.current = false; setCaptureBusy(false); } }, async (blob, durationMs) => {
      const value = { eventId: crypto.randomUUID(), blob, durationMs, createdAt: new Date().toISOString() };
      // Keep even a quota-failed capture in memory so it can be downloaded.
      if (active.current) setBuffer(value);
      await write('drafts', key, value, true);
      await upload(value);
    });
    void recorder.current.start();
  }
  async function retryUpload() { if (!buffer || lock.current) return; lock.current = true; setBusy(true); setError(''); try { await write('drafts', key, buffer); await upload(buffer); setState('ready'); } catch(e) { setError((e as Error).message); } finally { lock.current = false; setBusy(false); } }
  async function command(path: string, payload: Record<string, unknown>) {
    if (lock.current) return; lock.current = true; setBusy(true); setError('');
    try { const cmd = pending ?? await enqueue(key, path, payload); setPending(cmd); await deliver(key, cmd); if (cmd.path.endsWith('/playbacks')) lastPlayback.current.set(cmd.path.split('/')[2], cmd.eventId); if (cmd.path.endsWith('/ratings') && active.current) setRatingStatus('人工自评已保存，不增加回放次数。'); if (active.current) { setPending(null); setDeleting(null); setData(await list()); } }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { lock.current = false; if (active.current) setBusy(false); }
  }
  function observe(id: string, durationMs: number, audio: HTMLAudioElement) {
    const now = audio.currentTime, previous = lastPosition.current.get(id);
    if (!audio.seeking && !audio.paused && previous !== undefined && now > previous && now - previous < 1) observed.current.set(id, (observed.current.get(id) ?? 0) + (now - previous) * 1000);
    lastPosition.current.set(id, now);
    const duration = Math.floor(observed.current.get(id) ?? 0);
    if (duration >= 250 && !counted.current.has(id) && !lock.current && !pending) {
      counted.current.add(id);
      void command(`/recordings/${id}/playbacks`, { ...context, observedMs: Math.min(durationMs, duration), selfRating: 'replay_only' });
    }
  }
  const capturing = ['requesting_permission', 'recording', 'processing'].includes(state);
  return <div className="recorder-panel"><p className="boundary">录音回放 / 人工自评 · 未接入 ASR 或专业发音评测。私人录音保存在本机服务目录，未加密；上传失败先缓冲到此浏览器。离开录制中的页面会取消本次未停止录音。</p>
    {preferences?.recordingEnabled === false && <Message>录音上传已关闭，可在设置中启用。历史录音仍可回放。</Message>}<section className="speaking-target"><h3>跟读目标 · 第 {lesson.sentences.find(s => s.id === checkpoint.sentenceId)!.sequence} 句</h3><p lang={isBlind(checkpoint) ? undefined : 'en'}>{isBlind(checkpoint) ? '原文已隐藏，可先听示范或开启英文。' : lesson.sentences.find(s => s.id === checkpoint.sentenceId)!.text}</p></section>
    <Message>{labels[state]} · 本句：{data ? stateLabel[data.state] : '正在读取记录…'}</Message>{error && <Message error>{error}</Message>}
    <div className="toolbar"><RecorderAction disabled={capturing} waiting={busy} onClick={() => { players.current.forEach(a => a.pause()); void controller?.playTrack(checkpoint.sentenceId); }}>听本句示范</RecorderAction><RecorderAction className="primary" disabled={preferences?.recordingEnabled === false || capturing || !!buffer} waiting={busy || !!pending || !data} onClick={() => void start()}>开始新录音</RecorderAction><RecorderAction disabled={state !== 'recording'} onClick={() => recorder.current?.stop()}>停止并保存</RecorderAction><RecorderAction disabled={capturing} waiting={busy || !!pending} onClick={() => void command('/practice/events', { ...context, kind: 'speaking', action: 'pause' })}>暂停跟读</RecorderAction><RecorderAction disabled={capturing} waiting={busy || !!pending} onClick={() => void command('/practice/events', { ...context, kind: 'speaking', action: 'skip' })}>暂时跳过跟读</RecorderAction></div>
    {buffer && <section className="message"><p>有待上传录音 · {(buffer.durationMs / 1000).toFixed(1)} 秒。成功保存前不计练习证据。</p><RecorderAction disabled={capturing} waiting={busy} onClick={() => void retryUpload()}>重试上传原录音</RecorderAction><RecorderAction onClick={() => { const url = URL.createObjectURL(buffer.blob), a = document.createElement('a'); a.href = url; a.download = `recording.${buffer.blob.type.includes('mp4') ? 'mp4' : buffer.blob.type.includes('ogg') ? 'ogg' : 'webm'}`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }}>下载未上传录音</RecorderAction><RecorderAction disabled={capturing} waiting={busy} onClick={() => setDiscard(true)}>丢弃本机上传缓冲</RecorderAction></section>}
    {ratingStatus && <Toast>{ratingStatus}</Toast>}
    {pending && !busy && <RecorderAction disabled={capturing} onClick={() => void command(pending.path, pending.body)}>重试待确认操作</RecorderAction>}
    {!data && <RecorderAction onClick={() => window.location.reload()}>重新读取</RecorderAction>}
    {data && (data.recordings.length ? <ul className="recording-list">{data.recordings.map(r => <li key={r.id}><div className="section-heading"><strong><time dateTime={utcTimestamp(r.createdAt)} title="北京时间">{formatBeijingTime(r.createdAt)}</time></strong><span>{(r.durationMs / 1000).toFixed(1)} 秒 · {r.mimeType} · 已回放 {r.playbackCount} 次</span></div>{r.status === 'ready' ? <><audio controls preload="metadata" ref={node => { if (node) players.current.set(r.id, node); else players.current.delete(r.id); }} src={`/api/v1/recordings/${r.id}/audio`} onSeeking={() => lastPosition.current.delete(r.id)} onPlay={e => { counted.current.delete(r.id); observed.current.set(r.id, 0); lastPosition.current.set(r.id, e.currentTarget.currentTime); if (capturing) { e.currentTarget.pause(); return; } controller?.pause(); players.current.forEach((a, id) => { if (id !== r.id) a.pause(); }); }} onTimeUpdate={e => observe(r.id, r.durationMs, e.currentTarget)} onError={() => setError('录音文件无法回放，请检查本地文件或重新录制。')} />
      <p className="muted">实际播放满 250ms 后自动记录一次；暂停后继续播放或重新播放，会在再次回听后计次。人工自评不增加次数。</p><div className="toolbar recording-ratings">{[['try_again', '人工自评：还想再练'], ['satisfied', '人工自评：本次满意']].map(([rating, label]) => <RecorderAction key={rating} disabled={capturing} waiting={busy || !!pending} onClick={() => { const playbackEventId = lastPlayback.current.get(r.id); if (!playbackEventId) { setError('请先实际回放本句录音，待自动记录成功后再自评。'); return; } void command(`/recordings/${r.id}/ratings`, { ...context, playbackEventId, selfRating: rating }); }}>{label}</RecorderAction>)}</div></> : <Message error>文件不可用（{r.status}），不计当前可用录音；历史证据仍保留。</Message>}<div className="recording-delete"><RecorderAction disabled={capturing} waiting={busy || !!pending} onClick={() => setDeleting(r.id)}>删除这段录音</RecorderAction></div></li>)}</ul> : <p className="empty-state">本句尚无已保存录音。拒绝权限或跳过不会计为完成。</p>)}
    {discard && <Modal title="丢弃上传缓冲？" tone="danger" onClose={() => setDiscard(false)} actions={<><Button data-modal-initial-focus onClick={() => setDiscard(false)}>取消</Button><RecorderAction variant="danger" waiting={busy} onClick={() => { void remove('drafts', key, buffer?.eventId).then(() => { setBuffer(null); setDiscard(false); setError(''); }).catch(e => setError(e.message)); }}>丢弃缓冲</RecorderAction></>}><p>仅删除此浏览器中的待上传录音。丢失回执时服务端可能已保存，可在列表中检查；此操作不会删除服务端录音。请先下载需要保留的副本。</p></Modal>}
    {deleting && <Modal title="删除这段私人录音？" tone="danger" dismissible={!busy} onClose={() => setDeleting(null)} actions={<><Button data-modal-initial-focus disabled={busy} onClick={() => setDeleting(null)}>取消</Button><RecorderAction variant="danger" waiting={busy || !!pending} onClick={() => void command(`/recordings/${deleting}/delete`, { confirmed: true })}>{busy ? '正在删除…' : '删除录音'}</RecorderAction></>}><p>删除后将无法再次播放这段录音。删除标记与已有的回放证据仍会保留。</p><p className="modal-warning">此操作无法撤销，请确认已保存需要的副本。</p>{error && <Message error>{error}</Message>}</Modal>}
  </div>;
}
