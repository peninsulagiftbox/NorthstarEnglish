'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useLesson } from '@/lib/state/LessonProvider';
import { useMedia } from '@/lib/media/MediaProvider';
import { draftKey } from '@/lib/state/context';
import { request } from '@/lib/api/catalog';
import { read, write, remove } from '@/lib/persistence/db';
import { commandHeaders, deliver, enqueue, pendingCommand } from '@/lib/persistence/outbox';
import type { Command } from '@/lib/persistence/outbox';
import { Button, Message } from '@/components/ui/Primitives';
type Draft = { text: string; rowVersion: number; dirty?: boolean };
type Attempt = { attemptId: string; state: string; rawText: string; standardText: string; answerExposed: boolean; reviewItemId: string; result: { correct: boolean; edits: { kind: string; expected: string; actual: string; expectedIndex: number; actualIndex: number }[] } };
const stateLabels: Record<string, string> = { not_started: '未开始', in_progress: '正在尝试', practiced: '已练习', skipped: '已跳过', paused: '已暂停' };
export function DictationEditor({ exposureUncertain = false }: { exposureUncertain?: boolean }) {
  const { lesson, checkpoint } = useLesson();
  const { controller, media } = useMedia();
  const key = draftKey(checkpoint), sentenceId = checkpoint.sentenceId;
  const [tabId] = useState(() => {
    try { const existing = sessionStorage.getItem('northstar:tab-id'); if (existing) return existing; const id = crypto.randomUUID(); sessionStorage.setItem('northstar:tab-id', id); return id; }
    catch { return 'storage-unavailable'; }
  });
  const cacheKey = `${key}:${tabId}`;
  const context = { lessonId: lesson.id, versionId: lesson.versionId, sentenceId };
  const path = `/drafts/${encodeURIComponent(sentenceId)}`;
  const [text, setText] = useState('');
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState('正在读取草稿…');
  const [error, setError] = useState('');
  const [exposureUnavailable, setExposureUnavailable] = useState(false);
  const [serverDraft, setServerDraft] = useState<Draft | null>(null);
  const [pending, setPending] = useState<Command | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Attempt | null>(null);
  const [stage, setStage] = useState<{ state: string; practiceCount: number } | null>(null);
  const latest = useRef(''), revision = useRef<number | null>(null), dirty = useRef(false), blocked = useRef(false);
  const localQueue = useRef(Promise.resolve()), remoteQueue = useRef(Promise.resolve()), timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);
  const started = useRef(false);
  const refreshStage = () => request<{ sentenceId: string; state: string; practiceCount: number }[]>(`/study/stages?lessonId=${lesson.id}&versionId=${lesson.versionId}`).then(rows => { if (active.current) setStage(rows.find(r => r.sentenceId === sentenceId) ?? null); }).catch(() => { if (active.current) setError('练习状态读取失败；不显示未经确认的完成状态。'); });
  useEffect(() => {
    active.current = true;
    const load = async () => {
      try {
        const [local, server, command] = await Promise.all([read<Draft>('drafts', cacheKey).then(own => own ?? read<Draft>('drafts', key)), request<Draft>(`${path}?lessonId=${lesson.id}&versionId=${lesson.versionId}`), pendingCommand(key)]);
        if (!active.current) return;
        const legacy = localStorage.getItem(key) ?? '';
        const chosen = local?.dirty ? local.text : (server.rowVersion ? server.text : local?.text ?? legacy);
        latest.current = chosen; setText(chosen); revision.current = server.rowVersion;
        dirty.current = chosen !== server.text;
        if (local?.dirty && local.rowVersion !== server.rowVersion && local.text !== server.text) {
          blocked.current = true; setServerDraft(server); setStatus('草稿冲突：两份文本均已保留，请手动比较。');
        } else setStatus(dirty.current ? '已读取本机草稿 · 等待同步' : server.rowVersion ? '草稿已保存到服务端' : '草稿为空 · 尚未保存');
        setPending(command ?? null); setReady(true);
        await write('drafts', cacheKey, { text: chosen, rowVersion: server.rowVersion, dirty: dirty.current });
        if (dirty.current && !blocked.current) flush();
      } catch {
        try { const local = await read<Draft>('drafts', cacheKey).then(own => own ?? read<Draft>('drafts', key)); if (active.current) { latest.current = local?.text ?? localStorage.getItem(key) ?? ''; setText(latest.current); setReady(true); setPending(await pendingCommand(key) ?? null); } } catch { /* visible failure below */ }
        if (active.current) { setReady(true); setError('草稿同步初始化失败。可编辑并复制文本；重新载入后再同步服务端。'); }
      }
    };
    void load(); void refreshStage();
    return () => { active.current = false; if (timer.current) clearTimeout(timer.current); flush(); };
    // This component is keyed by lesson/version/target, so an async save retains its original target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function localSave(value: string) {
    localQueue.current = localQueue.current.catch(() => {}).then(() => write('drafts', cacheKey, { text: value, rowVersion: revision.current ?? 0, dirty: true }));
    localQueue.current.then(() => { if (active.current && latest.current === value && !blocked.current) setStatus('已保存到本机 · 等待服务端同步'); }).catch(() => { if (active.current) setError('本机存储失败，请复制文本；正式提交暂不可用。'); });
  }
  function flush() {
    remoteQueue.current = remoteQueue.current.catch(() => {}).then(async () => {
      if (!dirty.current || revision.current === null || blocked.current) return;
      const value = latest.current;
      try {
        await localQueue.current;
        const response = await request<{ rowVersion: number }>(path, { method: 'PUT', headers: { ...commandHeaders, 'If-Match': `"${revision.current}"` }, body: JSON.stringify({ ...context, text: value }) });
        revision.current = response.rowVersion;
        dirty.current = latest.current !== value;
        // Persist latest input, never overwrite keystrokes typed while the response was in flight.
        await localQueue.current;
        await write('drafts', cacheKey, { text: latest.current, rowVersion: revision.current, dirty: dirty.current });
        if (active.current) setStatus(dirty.current ? '已保存到本机 · 新输入等待同步' : '草稿已保存到服务端');
      } catch (e) {
        blocked.current = true;
        if (active.current) { setError(e instanceof Error ? e.message : '草稿同步失败'); setStatus('保留本机草稿 · 同步已暂停'); }
        try { const other = await request<Draft>(`${path}?lessonId=${lesson.id}&versionId=${lesson.versionId}`); if (active.current) setServerDraft(other); } catch { /* original draft retained */ }
      }
    });
  };
  async function send(command: Command) {
    setBusy(true); setError('');
    try {
      const response = await deliver<Attempt | { state: string }>(key, command);
      if (!active.current) return;
      setPending(null);
      if ('attemptId' in response) {
        try { await write('exposure', sentenceId, true); } catch { setExposureUnavailable(true); setError('听写结果已保存；本机答案暴露标记保存失败，请检查浏览器存储后再开始新的听写。'); }
        started.current = false; setResult(response);
      }
      await refreshStage();
    } catch(e) { if (active.current) setError(`${e instanceof Error ? e.message : '提交失败'} 原文与事件已保留，可重试同一次提交。`); }
    finally { if (active.current) setBusy(false); }
  }
  async function submit(action?: string) {
    if (busy || pending) return;
    setBusy(true); setError('');
    try {
      await localQueue.current;
      const exposed = !!await read('exposure', sentenceId);
      const command = await enqueue(key, action ? '/study/events' : `/exercises/${sentenceId}-dictation/attempts`, action ? { ...context, action } : { ...context, text: latest.current, answerExposed: exposed, audioPlayed: media.played.includes(sentenceId) && !(media.sentenceId === sentenceId && media.status === 'error') });
      setPending(command); await send(command);
    } catch { setError('无法将提交保存到本机队列；尚未发送，请复制文本并检查浏览器存储。'); setBusy(false); }
  }
  const audioReady = media.played.includes(sentenceId) && !(media.sentenceId === sentenceId && media.status === 'error');
  return <div className="draft-editor"><Message>听写目标为第 {lesson.sentences.find(s => s.id === sentenceId)?.sequence} 句。先播放音频再输入；提交前隐藏答案。打开课文查看答案会标记答案已暴露。</Message>
    <div className="toolbar dictation-playback"><Button onClick={() => void controller?.playTrack(sentenceId)}>播放本句</Button><span className="tag" data-testid="practice-state">{stage ? `${stateLabels[stage.state]} · 累计 ${stage.practiceCount} 次真实练习` : '练习状态待确认'}</span></div>
    <label htmlFor="dictation-text">本句听写草稿</label><textarea id="dictation-text" rows={5} maxLength={10000} disabled={!ready} value={text} placeholder="输入听到的英文…" onBlur={() => flush()} onChange={event => {
      const value = event.target.value; latest.current = value; dirty.current = true; setText(value); setResult(null); localSave(value);
      if (value.trim() && !started.current && !pending && !busy) { started.current = true; void submit('start'); }
      if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => flush(), 500);
    }} /><p role="status" className="muted draft-status">{status}</p>
    {serverDraft && <div className="draft-conflict"><h3>服务端草稿（保留本机输入）</h3><pre>{serverDraft.text || '（空）'}</pre><Button onClick={() => {
      revision.current = serverDraft.rowVersion; blocked.current = false; setServerDraft(null); setError(''); dirty.current = true; localSave(latest.current); flush();
    }}>比较后保留本机稿并同步</Button><Button onClick={() => {
      latest.current = serverDraft.text; setText(serverDraft.text); revision.current = serverDraft.rowVersion; dirty.current = false; blocked.current = false; setServerDraft(null); setError(''); void write('drafts', cacheKey, serverDraft); setStatus('已采用服务端草稿');
    }}>采用服务端稿</Button></div>}
    {error && <Message error>{error}</Message>}
    {pending ? <Message>有一次待确认提交：<pre>{String(pending.body.text ?? pending.body.action)}</pre><Button disabled={busy} onClick={() => void send(pending)}>重试同一次提交</Button><Button disabled={busy} onClick={async () => { await remove('outbox', key, pending.eventId); setPending(null); setError(''); }}>结束本次重试（服务端已存记录仍保留）</Button></Message> : <div className="toolbar"><Button className="primary" disabled={!ready || busy || !text.trim() || !audioReady || exposureUncertain || exposureUnavailable} onClick={() => void submit()}>检查听写</Button><Button disabled={!ready || busy} onClick={() => void submit('start')}>开始 / 恢复</Button><Button disabled={!ready || busy} onClick={() => void submit('pause')}>暂停本轮</Button><Button disabled={!ready || busy} onClick={() => void submit('skip')}>跳过本句</Button></div>}
    {!audioReady && <p className="boundary">请先成功播放本句；音源故障时不能生成有效听写。</p>}
    {result && <section className="dictation-result" aria-label="听写对照"><h3>{result.result.correct ? '听写准确' : '已练习 · 有需要复习的词'}{result.answerExposed && ' · 答案曾暴露'}</h3><div className="comparison"><div><h4>你的原文</h4><p>{result.rawText}</p></div><div><h4>标准写法</h4><p lang="en">{result.standardText}</p></div></div><p>忽略大小写与标点，按英文词序对齐；不将同义词视为准确听写。</p><ul className="token-diff">{result.result.edits.map((edit, index) => <li key={index} data-kind={edit.kind}>{edit.kind === 'equal' ? edit.actual : `${({ omit: '遗漏', insert: '插入', replace: '替换' } as Record<string,string>)[edit.kind]}：${edit.expected || '∅'} → ${edit.actual || '∅'}`}<small>标准词位 {edit.expectedIndex + 1} / 输入词位 {edit.actualIndex + 1}</small></li>)}</ul><Button onClick={() => void controller?.playTrack(sentenceId)}>回听本句</Button>{result.reviewItemId && <Link className="button" href="/review">查看复习来源 →</Link>}</section>}
  </div>;
}
