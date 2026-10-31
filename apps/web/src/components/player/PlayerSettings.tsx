'use client';
import { useEffect, useRef, useState } from 'react';
import { AudioController, validAB } from '@/lib/media/AudioController';
import type { MediaState } from '@/lib/media/AudioController';
import { Button } from '@/components/ui/Primitives';

type Props = { media: MediaState; controller: AudioController | null; sentence: { id: string; sequence: number }; sentenceCount: number; hasWordTimings: boolean; onMove: (offset: number) => void; onClose: () => void };
const options: { value: MediaState['mode']; label: string; hint: string }[] = [
  { value: 'single', label: '单句停止', hint: '播完当前句后暂停' },
  { value: 'sequence', label: '顺序连播', hint: '从当前句依次播放至课末' },
  { value: 'sentence', label: '单句循环', hint: '重复播放当前句' },
  { value: 'list', label: '列表循环', hint: '整课播完后从第一句继续' },
];
const statusLabels = { idle: '尚未加载', loading: '正在加载', playing: '正在播放', paused: '已暂停', ended: '播放结束', error: '音频不可用' };
export function PlayerSettings({ media, controller, sentence, sentenceCount, hasWordTimings, onMove, onClose }: Props) {
  const [abOpen, setAbOpen] = useState(media.a !== null || media.b !== null);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    close.current?.focus({ preventScroll: true });
    return () => previous?.focus({ preventScroll: true });
  }, []);
  const ready = media.mode !== 'full' && media.sentenceId === sentence.id && media.duration > 0 && !['loading', 'error'].includes(media.status);
  const valid = ready && validAB(media.a, media.b, media.duration);
  const hint = media.ab ? media.status === 'playing' ? '正在循环播放所选区间' : 'A–B 已开启，点击底部播放即可复读。' : media.a === null ? '在底部进度条定位起点，然后设置 A。' : media.b === null ? '起点已设置，向后定位并设置 B。' : !valid ? '终点需晚于起点，请向后定位并重新设置 B。' : `已选 ${(media.b! - media.a!).toFixed(2)} 秒，可开启循环。`;
  return <section id="player-settings" className="player-settings" aria-label="播放设置面板">
    <header className="settings-header"><div><h3>播放设置</h3><p>第 {String(sentence.sequence).padStart(2, '0')} 句 <span aria-hidden="true">·</span> {statusLabels[media.status]}</p></div><button ref={close} type="button" className="settings-close" aria-label="关闭" title="关闭播放设置" onClick={onClose}>×</button></header>
    <div className="settings-body">
      <div className="settings-playback"><div className="settings-field-heading"><h4 id="playback-mode-label">播放模式</h4><span>{options.find(o => o.value === media.mode)?.hint}</span></div>
        <select aria-label="播放模式" value={media.mode} disabled={!controller} onChange={event => controller?.mode(event.target.value as MediaState['mode'])}>{[...options, ...(controller?.fullTrack ? [{ value: 'full' as const, label: '整课音轨', hint: '保留片头和句间静音' }] : [])].map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
        <nav className="settings-sentence-nav" aria-label="切换播放句子"><Button aria-label="上一句" disabled={!controller || sentence.sequence <= 1} onClick={() => onMove(-1)}>‹ 上一句</Button><span>{String(sentence.sequence).padStart(2, '0')} <span aria-hidden="true">/</span> {String(sentenceCount).padStart(2, '0')}</span><Button aria-label="下一句" disabled={!controller || sentence.sequence >= sentenceCount} onClick={() => onMove(1)}>下一句 ›</Button></nav>
      </div>
      {media.error && <div className="settings-audio-error" role="alert"><p>{media.error}</p><Button onClick={() => void controller?.playTrack(sentence.id)}>重试播放</Button></div>}
      <section className="ab-panel" aria-label="句内 A-B 复读"><button type="button" className="ab-disclosure" aria-label="A–B" aria-expanded={abOpen} aria-controls="ab-editor" onClick={() => setAbOpen(!abOpen)}><span><strong>A–B 区间复读</strong><small>只重复播放本句中的一段</small></span><span className={`ab-state ${media.ab ? 'running' : ''}`}>{media.ab ? media.status === 'playing' ? '循环中' : '已开启' : valid ? '已设置' : '未设置'}</span><span className="settings-chevron" aria-hidden="true">{abOpen ? '⌃' : '⌄'}</span></button>
        {abOpen && <div id="ab-editor" className="ab-editor">
          {!ready ? <div className="ab-empty"><strong>{media.status === 'loading' ? '正在加载当前句…' : media.error ? '音频恢复后可设置区间' : '先加载当前句音频'}</strong><p>加载后，在底部进度条定位并设置起点和终点。</p>{!media.error && <Button className="settings-load" disabled={!controller || media.status === 'loading'} onClick={() => controller?.load(sentence.id)}>{media.status === 'loading' ? '加载中…' : '加载本句'}</Button>}</div> : <>
            <div className="ab-position"><span>当前位置</span><output>{media.time.toFixed(2)} <small>秒</small></output></div>
            <div className="ab-points">{(['a', 'b'] as const).map(point => <div className="ab-point" key={point}><label htmlFor={`ab-${point}-time`}><span className="ab-letter">{point.toUpperCase()}</span>{point === 'a' ? '起点' : '终点'}</label><output id={`ab-${point}-time`} className={media[point] === null ? 'unset' : ''}>{media[point]?.toFixed(2) ?? '—'}{media[point] !== null && <small> 秒</small>}</output><Button aria-label={`设 ${point.toUpperCase()} = 当前时间`} disabled={point === 'b' && (media.a === null || media.time <= media.a)} onClick={() => controller?.setAB(point === 'a' ? media.time : media.a, point === 'b' ? media.time : media.b)}>设为当前位置</Button></div>)}</div>
            <p className={`ab-hint ${media.a !== null && media.b !== null && !valid ? 'invalid' : ''}`} role="status">{hint}</p>
            <div className="ab-actions"><Button className="settings-primary" disabled={!valid} aria-pressed={media.ab} onClick={() => controller?.loopAB()}>{media.ab ? '停止 A–B 循环' : '开启 A–B 循环'}</Button><Button className="settings-clear" disabled={media.a === null && media.b === null} onClick={() => controller?.setAB(null, null)}>清除区间</Button></div>
          </>}
        </div>}
      </section>
      <details className="settings-help"><summary>时间点与复读说明</summary><div><p className="settings-legend"><span><i className="legend-word" /> 单词起点</span><span><i className="legend-sentence" /> 音频起点</span><span><i className="legend-sentence" /> 句末发音结束</span><span><i className="legend-end">终</i> 音频终点</span></p><p>{hasWordTimings ? '单词时间点由合成语音自动提供，尚未经人工逐词校正。' : '当前版本没有单词时间点，仅显示本句起点。'}</p><p>句末大点位于句末标点前最后一个单词的发音结束处。</p><p>A–B 仅在当前句内循环；切到后台时逐句播放暂停，返回前台后点击恢复。</p></div></details>
    </div>
  </section>;
}
