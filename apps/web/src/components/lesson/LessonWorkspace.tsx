'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useLesson } from '@/lib/state/LessonProvider';
import { draftKey, isBlind, lessonVersionHref, tabs } from '@/lib/state/context';
import { Button, Card, EmptyState, Message, Modal } from '@/components/ui/Primitives';
import { MediaProvider, useMedia } from '@/lib/media/MediaProvider';
import { VocabularyPanel } from '@/components/exercises/VocabularyPanel';
import { RecorderPanel } from '@/components/exercises/RecorderPanel';
import { WritingEditor } from '@/components/exercises/WritingEditor';
import { DictationEditor } from '@/components/exercises/DictationEditor';
import { write } from '@/lib/persistence/db';
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
  const { captureBusy } = useMedia();
  return <div className="tabs" role="tablist" aria-label="学习任务">{tabs.map(([id, label], i) => <button key={id} disabled={captureBusy} role="tab" id={`tab-${id}`} aria-controls="lesson-panel" aria-selected={checkpoint.tab === id} tabIndex={checkpoint.tab === id ? 0 : -1} onClick={() => update({ tab: id })} onKeyDown={event => {
    if (captureBusy) return;
    const next = event.key === 'ArrowRight' ? (i + 1) % tabs.length : event.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
    if (next !== null) { event.preventDefault(); update({ tab: tabs[next][0] }); document.getElementById(`tab-${tabs[next][0]}`)?.focus(); }
  }}>{label}</button>)}</div>;
}
export function SentenceList() {
  const { lesson, checkpoint, update } = useLesson();
  useEffect(() => { document.querySelector<HTMLButtonElement>('.sentence.selected')?.scrollIntoView({ block: 'nearest' }); }, [checkpoint.sentenceId]);
  const blind = isBlind(checkpoint);
  const { controller } = useMedia();
  return <ol className="sentence-list">{lesson.sentences.map(sentence => <li key={sentence.id}><button className={`sentence ${checkpoint.sentenceId === sentence.id ? 'selected' : ''}`} aria-label={`选择并播放句子 ${sentence.sequence}`} aria-pressed={checkpoint.sentenceId === sentence.id} disabled={!controller} onClick={() => { update({ sentenceId: sentence.id }); controller?.load(sentence.id); void controller?.play(); }}>
    <span className="sentence-index" aria-hidden="true">{String(sentence.sequence).padStart(2, '0')}</span><span><small>{sentence.speaker} · {String(sentence.sequence).padStart(3, '0')}</small><span className="sentence-text" lang={blind ? undefined : 'en'}>{blind ? `句子 ${sentence.sequence} · 原文已隐藏` : sentence.text}</span>{!blind && checkpoint.showTranslation && <span className="translation">{sentence.translation}</span>}</span>
  </button></li>)}</ol>;
}
export function LessonWorkspace() { return <MediaProvider><WorkspaceContent /></MediaProvider>; }
function WorkspaceContent() {
  const { lesson, checkpoint, update, sync, syncError } = useLesson();
  const { captureBusy } = useMedia();
  const [drawer, setDrawer] = useState(false);
  const [notice, setNotice] = useState(false);
  const blind = isBlind(checkpoint);
  const key = draftKey(checkpoint);
  const [exposureError, setExposureError] = useState(false);
  useEffect(() => {
    if (blind) return;
    const exposed = checkpoint.tab === 'text' ? lesson.sentences : lesson.sentences.filter(s => s.id === checkpoint.sentenceId);
    Promise.all(exposed.map(s => write('exposure', s.id, true))).catch(() => setExposureError(true));
  }, [blind, checkpoint.tab, checkpoint.sentenceId, lesson]);
  return <div className="lesson-workspace"><header className="lesson-header"><p className="eyebrow">ORIGINAL DEMONSTRATION · DEMO 01</p><h1>{lesson.title}</h1><div className="section-heading"><p className="muted">原创体验课 · {lesson.sentences.length} 句 · {lesson.versionId.endsWith('-v2') ? '英式 Edge 配音 v2' : '原型配音 v1'} · 日常交流 / 礼貌请求</p><Button onClick={() => setNotice(true)}>内容来源</Button></div></header>
    <LessonTabs /><div className="workspace-grid"><Card className="lesson-card"><div role="tabpanel" id="lesson-panel" aria-labelledby={`tab-${checkpoint.tab}`}>
      <div className="section-heading"><div><h2>{tabs.find(t => t[0] === checkpoint.tab)?.[1]}{checkpoint.tab === 'text' ? ' · 完整对话' : ''}</h2><p className="muted">{checkpoint.tab === 'text' ? '点击句子即可选中、播放原句并查看讲解。' : checkpoint.tab === 'vocabulary' ? '点词卡定位原句；提交阅读答案后查看证据与反馈。' : checkpoint.tab === 'speaking' ? '先听本句示范，再录制、回放并人工自评。' : checkpoint.tab === 'writing' ? '保留草稿，保存独立版本，再比较和修改。' : '选择目标句，保留逐句草稿；浏览与播放不计练习完成。'}</p></div><div className="toolbar"><Button aria-pressed={!checkpoint.showTranslation} onClick={() => update({ showTranslation: !checkpoint.showTranslation })}>{checkpoint.showTranslation ? '隐藏译文' : '显示译文'}</Button><Button aria-pressed={!checkpoint.showEnglish} onClick={() => update({ showEnglish: !checkpoint.showEnglish })}>{checkpoint.showEnglish ? '盲听模式' : '显示英文'}</Button></div></div>
      {checkpoint.tab === 'text' ? <SentenceList /> : <><div className="sentence-picker" aria-label="选择句子">{lesson.sentences.map(s => <Button key={s.id} disabled={captureBusy} aria-label={`选择句子 ${s.sequence}`} aria-pressed={checkpoint.sentenceId === s.id} onClick={() => update({ sentenceId: s.id })}>{String(s.sequence).padStart(2, '0')}</Button>)}</div>
      {checkpoint.tab === 'vocabulary' && <VocabularyPanel key={lesson.versionId} />}
      {checkpoint.tab === 'dictation' && <DictationEditor key={key} exposureUncertain={exposureError} />}
      {checkpoint.tab === 'writing' && <WritingEditor key={lesson.versionId} />}
      {checkpoint.tab === 'speaking' && <RecorderPanel key={key} />}
      {checkpoint.tab === 'quiz' && <EmptyState title="下一阶段开发"><p>真实测验提交与复习将在 Phase 07 开放。</p></EmptyState>}</>}
    </div></Card><aside className="surface tutor-desktop" aria-label="句子助教"><TutorPanel /></aside></div>
    <div className={`sync-status ${syncError ? 'error' : ''}`} role="status">{sync}{syncError && <Button onClick={() => window.location.reload()}>重新载入同步</Button>}</div>
    <Button className="tutor-toggle" onClick={() => setDrawer(true)}>打开句子助教</Button>
    <fieldset className="player-capture-guard" disabled={captureBusy} inert={captureBusy}><PlayerBar /></fieldset>
    {drawer && <Modal drawer title="句子助教" onClose={() => setDrawer(false)}><TutorPanel /></Modal>}
    {notice && <Modal title="原创 Demo · 内容来源" onClose={() => setNotice(false)} actions={<Button variant="primary" data-modal-initial-focus onClick={() => setNotice(false)}>知道了</Button>}><p>文本与讲解来自冻结的原创 Demo 01 版本包。{lesson.audioLabel ?? '原型配音的生成工具和音色尚未查明。'} 合成语音及素材正式发布授权仍待审核。</p><p>当前范围为本地功能测试，尚不具备正式发布条件。</p><p>当前版本：{lesson.versionId}。新版本不会覆盖旧版草稿和练习。</p><p><Link className="button" href={lessonVersionHref(checkpoint, 'demo-01-v2')} onClick={() => setNotice(false)}>英式 Edge 配音 v2</Link> <Link className="button" href={lessonVersionHref(checkpoint, 'demo-01-v1')} onClick={() => setNotice(false)}>原型配音 v1</Link></p></Modal>}
    {exposureError && <Message error>答案暴露状态无法保存。请检查浏览器存储；当前不保证独立听写统计。</Message>}
  </div>;
}
