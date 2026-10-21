'use client';
import { useLesson } from '@/lib/state/LessonProvider';
import { isBlind } from '@/lib/state/context';
import { Button } from '@/components/ui/Primitives';
export function PlayerBar() {
  const { lesson, checkpoint } = useLesson();
  const sentence = lesson.sentences.find(s => s.id === checkpoint.sentenceId)!;
  return <section className="player-bar" aria-label="音频播放器容器"><div className="player-buttons"><Button disabled aria-label="上一句，下一阶段开发">◂</Button><Button className="play-button" disabled aria-label="播放，下一阶段开发">▶</Button><Button disabled aria-label="下一句，下一阶段开发">▸</Button></div><div className="player-track"><strong>{isBlind(checkpoint) ? `句子 ${sentence.sequence} · 原文已隐藏` : `${sentence.speaker} · ${sentence.text}`}</strong><div className="track-placeholder" /><small>音频播放 · Phase 04 开发</small></div><span className="player-caption">播放器容器 · 尚未启用</span></section>;
}
