'use client';
import { useEffect, useRef, useState } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { request } from '@/lib/api/catalog';
import { writingData, postPractice, stateLabel } from '@/lib/api/practice';
import type { WritingData, Revision } from '@/lib/api/practice';
import { ApiError } from '@/lib/api/client';
import { read, write, remove } from '@/lib/persistence/db';
import { commandHeaders, pendingCommand, enqueue, deliver } from '@/lib/persistence/outbox';
import type { Command } from '@/lib/persistence/outbox';
import { Button, Message, Modal } from '@/components/ui/Primitives';
import { RevisionDiff } from './RevisionDiff';
import { RevisionHistory } from './RevisionHistory';

type LocalDraft = { text: string; rowVersion: number; parent: string | null };
export function WritingEditor() {
  const { lesson } = useLesson();
  const context = { lessonId: lesson.id, versionId: lesson.versionId };
  const key = `writing:${lesson.versionId}`;
  const [data, setData] = useState<WritingData | null>(null), [text, setText] = useState(''), [parent, setParent] = useState<string | null>(null);
  const [status, setStatus] = useState('正在读取草稿…'), [error, setError] = useState(''), [busy, setBusy] = useState(false), [pending, setPending] = useState<Command | null>(null);
  const [selected, setSelected] = useState(''), [confirm, setConfirm] = useState<Revision | null>(null), [serverConflict, setServerConflict] = useState<WritingData | null>(null);
  const revision = useRef(0), current = useRef(''), parentRef = useRef<string | null>(null), active = useRef(true), lock = useRef(false), dirty = useRef(false);
  useEffect(() => {
    active.current = true;
    void Promise.all([writingData(lesson.id, lesson.versionId), read<LocalDraft>('drafts', key), pendingCommand(key)]).then(([remote, local, cmd]) => {
      if (!active.current) return;
      setData(remote); revision.current = local?.rowVersion ?? remote.draft.rowVersion; current.current = local?.text ?? remote.draft.text; parentRef.current = local?.parent ?? null;
      setText(current.current); setParent(parentRef.current); setPending(cmd ?? null); setSelected(remote.revisions.at(-1)?.id ?? '');
      dirty.current = !!local && local.text !== remote.draft.text;
      if (local && local.rowVersion !== remote.draft.rowVersion && local.text !== remote.draft.text) { setServerConflict(remote); setError('本机与服务端草稿版本不同，请比较并选择。'); }
      else { revision.current = remote.draft.rowVersion; setStatus(cmd ? '有待确认版本，请重试原提交。' : '草稿已恢复'); }
    }).catch(e => { if (active.current) setError(e.message); });
    return () => { active.current = false; };
  }, [lesson.id, lesson.versionId, key]);
  async function persist(value: string) {
    current.current = value; dirty.current = true; setText(value); setStatus('本机保存中…');
    try { await write('drafts', key, { text: value, rowVersion: revision.current, parent: parentRef.current }); if (active.current) setStatus('已保留本机草稿，等待同步'); }
    catch { if (active.current) setError('本机存储失败，请复制草稿后再离开。'); }
  }
  async function syncDraft() {
    const snapshot = current.current;
    const result = await request<{ rowVersion: number }>('/writing/draft', { method: 'PUT', headers: commandHeaders, body: JSON.stringify({ ...context, text: snapshot, rowVersion: revision.current }) });
    revision.current = result.rowVersion;
    // Preserve edits made while the request was in flight.
    dirty.current = current.current !== snapshot;
    await write('drafts', key, { text: current.current, rowVersion: revision.current, parent: parentRef.current });
    if (active.current) setStatus(dirty.current ? '正在同步新修改…' : '草稿已同步本地服务');
    return result.rowVersion;
  }
  useEffect(() => {
    if (!data || !dirty.current || busy || pending || serverConflict || error) return;
    const timer = setTimeout(() => {
      if (lock.current) return; lock.current = true;
      void syncDraft().catch(async e => { if (active.current) { setError(e.message); try { setServerConflict(await writingData(lesson.id, lesson.versionId)); } catch {} } }).finally(() => { lock.current = false; });
    }, 650);
    return () => clearTimeout(timer);
    // The timer follows editable snapshots; server revision is held in a ref.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, data, busy, pending, serverConflict, error, status]);
  async function saveVersion() {
    if (lock.current) return; lock.current = true; setBusy(true); setError('');
    let cmd = pending;
    try {
      if (!cmd) { const version = await syncDraft(); cmd = await enqueue(key, '/writing/revisions', { ...context, text: current.current, draftVersion: version, parentRevisionId: parentRef.current }); setPending(cmd); }
      await deliver(key, cmd); if (!active.current) return; setPending(null);
      const remote = await writingData(lesson.id, lesson.versionId);
      if (!active.current) return;
      setData(remote); setSelected(remote.revisions.at(-1)?.id ?? '');
      setStatus('新版本已保存，历史内容保持不变');
      // Only clear the submitted snapshot; another page may already have a newer draft.
      if (current.current === cmd.body.text && remote.draft.text === cmd.body.text && remote.draft.rowVersion === cmd.body.draftVersion) {
        try {
          const cleared = await request<{ rowVersion: number }>('/writing/draft', { method: 'PUT', headers: commandHeaders, body: JSON.stringify({ ...context, text: '', rowVersion: remote.draft.rowVersion }) });
          if (!active.current) return;
          await write('drafts', key, { text: '', rowVersion: cleared.rowVersion, parent: null });
          revision.current = cleared.rowVersion; current.current = ''; parentRef.current = null; dirty.current = false;
          if (active.current) {
            setText(''); setParent(null);
            setData({ ...remote, draft: { text: '', rowVersion: cleared.rowVersion } });
            setStatus('新版本已保存，输入已清空；历史内容保持不变');
          }
        } catch (e) {
          if (active.current) setError(`新版本已保存，但草稿未能完整清空；原文保留。${e instanceof Error ? e.message : '请重新读取草稿。'}`);
        }
      } else setStatus('新版本已保存；草稿已有其他修改，保留当前输入');
    } catch (e) {
      if (e instanceof ApiError && e.status === 412 && cmd) {
        // An explicit conflict proves this command was rejected, so it can be rebuilt after comparison.
        await remove('outbox', key, cmd.eventId);
        if (active.current) { setPending(null); try { setServerConflict(await writingData(lesson.id, lesson.versionId)); } catch {} }
      }
      if (active.current) setError(e instanceof Error ? e.message : '保存失败，请重试原提交。');
    }
    finally { lock.current = false; if (active.current) setBusy(false); }
  }
  async function action(action: string) { if (lock.current) return; lock.current = true; setBusy(true); try { const result = await postPractice<{ state: string }>('/practice/events', { ...context, kind: 'writing', action, eventId: crypto.randomUUID() }); setData(d => d ? { ...d, state: result.state } : d); } catch (e) { setError((e as Error).message); } finally { lock.current = false; setBusy(false); } }
  const sentences = text.trim().split(/[.!?]+/).filter(s => s.trim()).length;
  return <div className="writing-editor">{error && <Message error>{error}</Message>}{!data ? <><Message>{error ? '草稿读取失败；未载入前不能编辑。' : status}</Message><Button onClick={() => window.location.reload()}>重新读取</Button></> : <>
    <p className="writing-prompt" lang="en">{data.prompt}</p><p className="muted">来源句：5、6、9 · {stateLabel[data.state]} · {data.revisions.length} 个正式版本</p>
    <label htmlFor="writing-text">写作草稿 <small>自动保存；与正式版本分离</small></label><textarea id="writing-text" rows={7} maxLength={10000} value={text} disabled={busy || !!pending} onChange={e => void persist(e.target.value)} />
    <p role="status" className="muted">{status}{parent ? ' · 回载历史后再次保存将生成新版本' : ''}</p>
    {serverConflict && <section className="message"><h3>服务端草稿</h3><p className="preserve-lines">{serverConflict.draft.text || '（空）'}</p><Button disabled={busy || !!pending} onClick={() => { revision.current = serverConflict.draft.rowVersion; setServerConflict(null); setError(''); void persist(current.current); }}>保留本机内容并重新同步</Button><Button disabled={busy || !!pending} onClick={() => { revision.current = serverConflict.draft.rowVersion; setServerConflict(null); setError(''); void persist(serverConflict.draft.text); }}>使用服务端内容</Button></section>}
    <p className="boundary">基础规则提示 · 非 AI 语法校对：约 {sentences} 句（目标 2–3 句）；{['please', 'beside', 'I can'].map(t => `${t} ${text.toLowerCase().includes(t.toLowerCase()) ? '已尝试' : '未出现'}`).join(' / ')}。不判断语法、自然度或能力。</p>
    <div className="toolbar"><Button className="primary" disabled={busy || !!serverConflict || (!pending && !text.trim())} onClick={() => void saveVersion()}>{pending ? '重试待确认版本' : busy ? '保存中…' : '保存新版本'}</Button><Button disabled={busy || !!pending} onClick={() => void action('pause')}>暂停写作</Button><Button disabled={busy || !!pending} onClick={() => void action('skip')}>暂时跳过写作</Button>{error && !serverConflict && <Button onClick={() => { setError(''); setStatus('准备重试同步'); }}>重试同步草稿</Button>}</div>
    <RevisionHistory revisions={data.revisions} selected={selected} onSelect={setSelected} disabled={busy || !!pending} onLoad={setConfirm} />
    {selected && <RevisionDiff before={data.revisions.find(r => r.id === selected)?.text ?? ''} after={text} />}
    <p className="boundary">历史版本不可覆盖或删除；回载仅替换草稿，需再次保存生成新版本。</p>
    {confirm && <Modal title="替换当前草稿？" onClose={() => setConfirm(null)} actions={<><Button data-modal-initial-focus onClick={() => setConfirm(null)}>取消</Button><Button variant="primary" onClick={() => { parentRef.current = confirm.id; setParent(confirm.id); void persist(confirm.text); setConfirm(null); }}>确认回载</Button></>}><p>将用 V{confirm.versionNo} 替换当前草稿。已有正式版本保持不变。</p></Modal>}
  </>}</div>;
}
