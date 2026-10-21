'use client';
import { useState } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { draftKey, isBlind, tabs } from '@/lib/state/context';
import { Button, Card, EmptyState, Message, Modal, Toast } from '@/components/ui/Primitives';
import { PlayerBar } from '@/components/player/PlayerBar';

export function TutorPanel() {
  const { lesson, checkpoint } = useLesson();
  const sentence = lesson.sentences.find(s => s.id === checkpoint.sentenceId)!;
  return <div className="tutor-content"><div className="tutor-heading"><span className="tutor-mark" aria-hidden="true">✦</span><div><h2>句子助教</h2><small>本地预置讲解 · 未接入 AI</small></div></div>
    <div className="tutor-current"><small>当前聚焦 · Sentence {String(sentence.sequence).padStart(2, '0')}</small>{isBlind(checkpoint) ? <p>目标文本已隐藏</p> : <p lang="en">{sentence.text}</p>}</div>
    {isBlind(checkpoint) ? <Message>盲听保护中：原文、译文、知识点与讲解均已隐藏。可切回课文并开启英文查看。</Message> : <><div className="tutor-explanation"><h3>✧ 本句知识点</h3><p>{sentence.explanation}</p><span className="tag" lang="en">{sentence.focus}</span></div><p className="boundary">讲解来自本课版本包，随选句更新。开放提问将在后续阶段接入。</p></>}
  </div>;
}
export function LessonTabs() {
  const { checkpoint, update } = useLesson();
  return <div className="tabs" role="tablist" aria-label="学习任务">{tabs.map(([id, label], i) => <button key={id} role="tab" id={`tab-${id}`} aria-controls="lesson-panel" aria-selected={checkpoint.tab === id} tabIndex={checkpoint.tab === id ? 0 : -1} onClick={() => update({ tab: id })} onKeyDown={event => {
    const next = event.key === 'ArrowRight' ? (i + 1) % tabs.length : event.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
    if (next !== null) { event.preventDefault(); update({ tab: tabs[next][0] }); document.getElementById(`tab-${tabs[next][0]}`)?.focus(); }
  }}>{label}</button>)}</div>;
}
export function SentenceList() {
  const { lesson, checkpoint, update } = useLesson();
  const blind = isBlind(checkpoint);
  return <ol className="sentence-list">{lesson.sentences.map(sentence => <li key={sentence.id}><button className={`sentence ${checkpoint.sentenceId === sentence.id ? 'selected' : ''}`} aria-pressed={checkpoint.sentenceId === sentence.id} onClick={() => update({ sentenceId: sentence.id })}>
    <span className="sentence-index" aria-hidden="true">{String(sentence.sequence).padStart(2, '0')}</span><span><small>{sentence.speaker} · {String(sentence.sequence).padStart(3, '0')}</small><span className="sentence-text" lang={blind ? undefined : 'en'}>{blind ? `句子 ${sentence.sequence} · 原文已隐藏` : sentence.text}</span>{!blind && checkpoint.showTranslation && <span className="translation">{sentence.translation}</span>}</span>
  </button></li>)}</ol>;
}
function DraftEditor({ storageKey, writing }: { storageKey: string; writing: boolean }) {
  const [initial] = useState(() => { try { return { text: localStorage.getItem(storageKey) ?? '', error: false }; } catch { return { text: '', error: true }; } });
  const [text, setText] = useState(initial.text);
  const [failed, setFailed] = useState(initial.error);
  return <div className="draft-editor"><label htmlFor="draft-text">{writing ? '写作草稿' : '本句听写草稿'} <small>仅本机草稿 · 未正式提交</small></label><textarea id="draft-text" value={text} maxLength={10000} rows={writing ? 8 : 5} placeholder={writing ? 'Write two or three sentences about helping in a garden…' : '输入你想保留的英文草稿…'} onChange={e => {
    setText(e.target.value); try { localStorage.setItem(storageKey, e.target.value); setFailed(false); } catch { setFailed(true); }
  }} />{failed ? <Message error>本机草稿存储不可用，离开页面前请自行复制文本。</Message> : <p className="muted draft-status" role="status">草稿保留在此浏览器；不生成作答记录、反馈或完成状态。</p>}
    <Button disabled>正式提交 · 下一阶段开发</Button></div>;
}
export function LessonWorkspace() {
  const { lesson, checkpoint, update, sync, syncError } = useLesson();
  const [drawer, setDrawer] = useState(false);
  const [notice, setNotice] = useState(false);
  const blind = isBlind(checkpoint);
  const key = draftKey(checkpoint);
  return <div className="lesson-workspace"><header className="lesson-header"><p className="eyebrow">ORIGINAL DEMONSTRATION · DEMO 01</p><h1>{lesson.title}</h1><div className="section-heading"><p className="muted">原创体验课 · {lesson.sentences.length} 句 · 日常交流 / 礼貌请求 / 位置表达</p><Button onClick={() => setNotice(true)}>内容来源</Button></div></header>
    <LessonTabs /><div className="workspace-grid"><Card className="lesson-card"><div role="tabpanel" id="lesson-panel" aria-labelledby={`tab-${checkpoint.tab}`}>
      <div className="section-heading"><div><h2>{tabs.find(t => t[0] === checkpoint.tab)?.[1]}{checkpoint.tab === 'text' ? ' · 完整对话' : ''}</h2><p className="muted">{checkpoint.tab === 'text' ? '点击句子查看讲解，当前仅浏览，不自动播放。' : '保留当前句子与文本草稿；训练功能将在后续阶段开放。'}</p></div><div className="toolbar"><Button aria-pressed={!checkpoint.showTranslation} onClick={() => update({ showTranslation: !checkpoint.showTranslation })}>{checkpoint.showTranslation ? '隐藏译文' : '显示译文'}</Button><Button aria-pressed={!checkpoint.showEnglish} onClick={() => update({ showEnglish: !checkpoint.showEnglish })}>{checkpoint.showEnglish ? '盲听模式' : '显示英文'}</Button></div></div>
      {checkpoint.tab === 'text' ? <SentenceList /> : <><div className="sentence-picker" aria-label="选择句子">{lesson.sentences.map(s => <Button key={s.id} aria-label={`选择句子 ${s.sequence}`} aria-pressed={checkpoint.sentenceId === s.id} onClick={() => update({ sentenceId: s.id })}>{String(s.sequence).padStart(2, '0')}</Button>)}</div>
      {checkpoint.tab === 'dictation' && <><Message>听写目标文本已保护；音频播放、检查听写与错误反馈将在 Phase 04 开发。</Message><DraftEditor key={key} storageKey={key} writing={false} /></>}
      {checkpoint.tab === 'writing' && <><p className="writing-prompt">写 2–3 句关于在社区花园帮忙的话，尝试使用 please、beside 和 I can。</p><DraftEditor key={key} storageKey={key} writing /></>}
      {['vocabulary', 'speaking', 'quiz'].includes(checkpoint.tab) && <EmptyState title="下一阶段开发"><p>{checkpoint.tab === 'vocabulary' ? '精读词汇、证据题与收藏将在 Phase 05 开放。' : checkpoint.tab === 'speaking' ? '录音回放 / 人工自评将在 Phase 06 开放；未接入 ASR 或专业语音评测。' : '真实测验提交与复习将在 Phase 07 开放。'}</p><p>当前可选句并查看{blind ? '受保护的助教面板' : '本地预置讲解'}。</p></EmptyState>}</>}
    </div></Card><aside className="surface tutor-desktop" aria-label="句子助教"><TutorPanel /></aside></div>
    <div className={`sync-status ${syncError ? 'error' : ''}`} role="status">{sync}{syncError && <Button onClick={() => window.location.reload()}>重新载入同步</Button>}</div>
    <Button className="tutor-toggle" onClick={() => setDrawer(true)}>打开句子助教</Button>
    <PlayerBar />
    {drawer && <Modal drawer title="句子助教" onClose={() => setDrawer(false)}><TutorPanel /></Modal>}
    {notice && <Modal title="原创 Demo · 内容来源" onClose={() => setNotice(false)}><p>文本与讲解来自冻结的原创 Demo 01 版本包；合成音频的工具、声音与授权证明仍待审核。</p><p>当前范围为本地功能测试，尚不具备正式发布条件。</p><Button onClick={() => { setNotice(false); }}>知道了</Button></Modal>}
    {checkpoint.tab === 'dictation' && <Toast>盲听保护已开启 · 正式听写将在 Phase 04 开放</Toast>}
  </div>;
}
