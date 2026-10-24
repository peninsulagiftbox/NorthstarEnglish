'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useLesson } from '@/lib/state/LessonProvider';
import { useMedia } from '@/lib/media/MediaProvider';
import { draftKey } from '@/lib/state/context';
import { request } from '@/lib/api/catalog';
import { read, write, remove } from '@/lib/persistence/db';
import { commandHeaders, deliver, enqueue, pendingCommand } from '@/lib/persistence/outbox';
import type { Command } from '@/lib/persistence/outbox';
import { Button, Message } from '@/components/ui/Primitives';
import type { ButtonProps } from '@/components/ui/Primitives';

// Loading and short requests stay guarded without dimming the whole action row.
function DictationAction({ waiting = false, onClick, ...props }: ButtonProps & { waiting?: boolean }) {
  return <Button {...props} aria-disabled={props.disabled || waiting || undefined} onClick={event => { if (waiting) { event.preventDefault(); return; } onClick?.(event); }} />;
}
type Draft = { text: string; rowVersion: number; dirty?: boolean };
type Attempt = { attemptId: string; state: string; rawText: string; standardText: string; answerExposed: boolean; reviewItemId: string; result: { correct: boolean; edits: { kind: string; expected: string; actual: string; expectedIndex: number; actualIndex: number }[] } };
type StudyCount = { sentenceId: string; practiceCount: number };
export function DictationEditor({ exposureUncertain = false }: { exposureUncertain?: boolean }) {
  const { lesson, checkpoint } = useLesson();
  const { controller } = useMedia();
  const [counts, setCounts] = useState<StudyCount[] | null>(null), [countError, setCountError] = useState('');
  const active = useRef(true), countRequest = useRef(0);
  const refreshCounts = useCallback(() => {
    const requestId = ++countRequest.current;
    return request<StudyCount[]>(`/study/stages?lessonId=${lesson.id}&versionId=${lesson.versionId}`).then(rows => {
      if (active.current && requestId === countRequest.current) { setCounts(rows); setCountError(''); }
    }).catch(() => { if (active.current && requestId === countRequest.current) setCountError('练习次数读取失败，请重试。'); });
  }, [lesson.id, lesson.versionId]);
  useEffect(() => { active.current = true; void refreshCounts(); return () => { active.current = false; }; }, [refreshCounts]);
  const count = counts?.find(row => row.sentenceId === checkpoint.sentenceId)?.practiceCount;
  return <div className="draft-editor dictation-panel">
    <Message>听写目标为第 {lesson.sentences.find(s => s.id === checkpoint.sentenceId)?.sequence} 句。先播放音频再输入；提交前隐藏答案。打开课文查看答案会标记答案已暴露。</Message>
    <div className="toolbar dictation-playback"><Button onClick={() => void controller?.playTrack(checkpoint.sentenceId)}>播放本句</Button><span className="tag" data-testid="practice-state">累计 <span data-testid="practice-count" style={{ display: 'inline-block', minWidth: '2ch', textAlign: 'center', fontVariantNumeric: 'tabular-nums' }}>{count ?? '—'}</span> 次真实练习</span></div>
    {countError && <Message error>{countError}<Button onClick={() => void refreshCounts()}>重试读取次数</Button></Message>}
    <SentenceDictationEditor key={draftKey(checkpoint)} exposureUncertain={exposureUncertain} refreshCounts={refreshCounts} />
  </div>;
}
function SentenceDictationEditor({ exposureUncertain, refreshCounts }: { exposureUncertain: boolean; refreshCounts: () => Promise<void> }) {
  const { lesson, checkpoint, update } = useLesson();
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
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [exposureUnavailable, setExposureUnavailable] = useState(false);
  const [serverDraft, setServerDraft] = useState<Draft | null>(null);
  const [pending, setPending] = useState<Command | null>(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Attempt | null>(null);
  const latest = useRef(''), revision = useRef<number | null>(null), dirty = useRef(false), blocked = useRef(false);
  const localQueue = useRef(Promise.resolve()), remoteQueue = useRef(Promise.resolve()), timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = useRef(true);
  const started = useRef(false), actionLock = useRef(false);
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
          blocked.current = true; setServerDraft(server);
        }
        setPending(command ?? null); setReady(true);
        await write('drafts', cacheKey, { text: chosen, rowVersion: server.rowVersion, dirty: dirty.current });
        if (dirty.current && !blocked.current) flush();
      } catch {
        try { const local = await read<Draft>('drafts', cacheKey).then(own => own ?? read<Draft>('drafts', key)); if (active.current) { latest.current = local?.text ?? localStorage.getItem(key) ?? ''; setText(latest.current); setReady(true); setPending(await pendingCommand(key) ?? null); } } catch { /* visible failure below */ }
        if (active.current) { setReady(true); setError('草稿同步初始化失败。可编辑并复制文本；重新载入后再同步服务端。'); }
      }
    };
    void load();
    return () => { active.current = false; if (timer.current) clearTimeout(timer.current); flush(); };
    // This component is keyed by lesson/version/target, so an async save retains its original target.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  function localSave(value: string) {
    localQueue.current = localQueue.current.catch(() => {}).then(() => write('drafts', cacheKey, { text: value, rowVersion: revision.current ?? 0, dirty: true }));
    localQueue.current.catch(() => { if (active.current) setError('本机存储失败，请复制文本；正式提交暂不可用。'); });
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
      } catch (e) {
        blocked.current = true;
        if (active.current) { setError(e instanceof Error ? e.message : '草稿同步失败');  }
        try { const other = await request<Draft>(`${path}?lessonId=${lesson.id}&versionId=${lesson.versionId}`); if (active.current) setServerDraft(other); } catch { /* original draft retained */ }
      }
    });
  };
  async function send(command: Command) {
    setBusy(true); setError(''); setNotice('');
    try {
      const response = await deliver<Attempt | { state: string }>(key, command);
      if ('attemptId' in response) await refreshCounts();
      if (!active.current) return;
      setPending(null);
      if (command.body.action === 'skip' && response.state === 'skipped') {
        controller?.pause();
        const next = lesson.sentences[lesson.sentences.findIndex(s => s.id === sentenceId) + 1];
        if (next) {
          controller?.load(next.id);
          update({ sentenceId: next.id });
          return;
        }
        setNotice('已跳过最后一句。可选择其他句子补练，或切换到精读词汇继续学习；跳过不计练习完成。');
      }
      if ('attemptId' in response) {
        try { await write('exposure', sentenceId, true); } catch { setExposureUnavailable(true); setError('听写结果已保存；本机答案暴露标记保存失败，请检查浏览器存储后再开始新的听写。'); }
        started.current = false; setResult(response);
      }
    } catch(e) { if (active.current) setError(`${e instanceof Error ? e.message : '提交失败'} 原文与事件已保留，可重试同一次提交。`); }
    finally { if (active.current) setBusy(false); }
  }
  async function submit(action?: string) {
    if (!ready || busy || pending || actionLock.current) return;
    actionLock.current = true; setBusy(true); setError('');
    try {
      await localQueue.current;
      const exposed = !!await read('exposure', sentenceId);
      const command = await enqueue(key, action ? '/study/events' : `/exercises/${sentenceId}-dictation/attempts`, action ? { ...context, action } : { ...context, text: latest.current, answerExposed: exposed, audioPlayed: media.played.includes(sentenceId) && !(media.sentenceId === sentenceId && media.status === 'error') });
      setPending(command); await send(command);
    } catch { setError('无法将提交保存到本机队列；尚未发送，请复制文本并检查浏览器存储。'); setBusy(false); }
    finally { actionLock.current = false; }
  }
  const audioReady = media.played.includes(sentenceId) && !(media.sentenceId === sentenceId && media.status === 'error');
  return <div className="dictation-draft">
    <label htmlFor="dictation-text">本句听写草稿</label><textarea id="dictation-text" rows={5} maxLength={10000} readOnly={!ready} aria-disabled={!ready || undefined} aria-busy={!ready} value={text} placeholder="输入听到的英文…" onBlur={() => flush()} onChange={event => {
      if (!ready) return;
      const value = event.target.value; latest.current = value; dirty.current = true; setText(value); setResult(null); localSave(value);
      if (value.trim() && !started.current && !pending && !busy) { started.current = true; void submit('start'); }
      if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => flush(), 500);
    }} />
    {serverDraft && <div className="draft-conflict"><h3>服务端草稿（保留本机输入）</h3><pre>{serverDraft.text || '（空）'}</pre><Button onClick={() => {
      revision.current = serverDraft.rowVersion; blocked.current = false; setServerDraft(null); setError(''); dirty.current = true; localSave(latest.current); flush();
    }}>比较后保留本机稿并同步</Button><Button onClick={() => {
      latest.current = serverDraft.text; setText(serverDraft.text); revision.current = serverDraft.rowVersion; dirty.current = false; blocked.current = false; setServerDraft(null); setError(''); void write('drafts', cacheKey, serverDraft);
    }}>采用服务端稿</Button></div>}
    {error && <Message error>{error}</Message>}
    {notice && <Message>{notice}</Message>}
    {pending && !busy && <Message>有一次待确认提交：<pre>{String(pending.body.text ?? pending.body.action)}</pre><DictationAction waiting={busy} onClick={() => { if (actionLock.current) return; actionLock.current = true; void send(pending).finally(() => { actionLock.current = false; }); }}>重试同一次提交</DictationAction><DictationAction waiting={busy} onClick={async () => { await remove('outbox', key, pending.eventId); setPending(null); setError(''); }}>结束本次重试（服务端已存记录仍保留）</DictationAction></Message>}
    <div className="toolbar dictation-actions" aria-busy={!ready || busy}><DictationAction className="primary" disabled={!text.trim() || !audioReady || exposureUncertain || exposureUnavailable} waiting={!ready || busy || !!pending} onClick={() => void submit()}>检查听写</DictationAction><DictationAction waiting={!ready || busy || !!pending} onClick={() => void submit('start')}>开始 / 恢复</DictationAction><DictationAction waiting={!ready || busy || !!pending} onClick={() => void submit('pause')}>暂停本轮</DictationAction><DictationAction waiting={!ready || busy || !!pending} onClick={() => void submit('skip')}>跳过本句</DictationAction></div>
    {!audioReady && <p className="boundary">请先成功播放本句；音源故障时不能生成有效听写。</p>}
    {result && <section className="dictation-result" aria-label="听写对照"><h3>{result.result.correct ? '听写准确' : '已练习 · 有需要复习的词'}{result.answerExposed && ' · 答案曾暴露'}</h3><div className="comparison"><div><h4>你的原文</h4><p>{result.rawText}</p></div><div><h4>标准写法</h4><p lang="en">{result.standardText}</p></div></div><p>忽略大小写与标点，按英文词序对齐；不将同义词视为准确听写。</p><ul className="token-diff">{result.result.edits.map((edit, index) => <li key={index} data-kind={edit.kind}>{edit.kind === 'equal' ? edit.actual : `${({ omit: '遗漏', insert: '插入', replace: '替换' } as Record<string,string>)[edit.kind]}：${edit.expected || '∅'} → ${edit.actual || '∅'}`}<small>标准词位 {edit.expectedIndex + 1} / 输入词位 {edit.actualIndex + 1}</small></li>)}</ul><Button onClick={() => void controller?.playTrack(sentenceId)}>回听本句</Button>{result.reviewItemId && <Link className="button" href="/review">查看复习来源 →</Link>}</section>}
  </div>;
}
