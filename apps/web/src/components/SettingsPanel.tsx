'use client';
import { useEffect, useState } from 'react';
import { getPreferences, savePreferences } from '@/lib/api/settings';
import type { Preferences } from '@/lib/api/settings';
import { Button, Card, Message } from '@/components/ui/Primitives';
const speeds = [1, 1.25, 1.5, 0.75];
export function SettingsPanel() {
  const [settings, setSettings] = useState<Preferences | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; getPreferences().then(s => { if (active) setSettings(s); }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, [retry]);
  const save = async () => { if(!settings || busy)return;setBusy(true);setError('');setNotice('');try { const result=await savePreferences(settings);setSettings({...settings,rowVersion:result.rowVersion});setNotice('偏好已保存到本地服务，刷新后保留。重新进入工作台时应用。'); } catch(e) { setError(e instanceof Error?e.message:'保存失败'); } finally {setBusy(false);} };
  return <Card><h2>本地偏好</h2>{error && <Message error>{error}</Message>}{notice && <Message>{notice}</Message>}{!settings ? <>{!error && <Message>正在读取已保存偏好…</Message>}<Button onClick={()=>{setError('');setRetry(n=>n+1);}}>重试读取偏好</Button></> : <><fieldset disabled={busy} className="preference-fields"><div className="preference-speed-row"><span>默认播放倍速</span><Button className="preference-speed" aria-label="默认播放倍速" title="点击循环切换倍速：1x → 1.25x → 1.5x → 0.75x" data-speed={settings.defaultSpeed} onClick={()=>setSettings({...settings,defaultSpeed:speeds[(speeds.indexOf(settings.defaultSpeed)+1)%speeds.length]})}>{settings.defaultSpeed}x</Button></div>{([['showTranslation','默认显示译文'],['showHints','显示键盘快捷键提示'],['shortcutEnabled','启用播放器快捷键'],['recordingEnabled','启用录音上传']] as const).map(([key,label])=><label key={key}><input type="checkbox" checked={settings[key]} onChange={e=>setSettings({...settings,[key]:e.target.checked})} /> {label}</label>)}</fieldset><p className="muted">时间固定为北京时间。默认译文用于新学习上下文；已有恢复点保留该次选择。关闭录音上传会保留本机缓冲与历史录音。</p><div className="toolbar"><Button onClick={()=>void save()} disabled={busy}>{busy?'正在保存…':'保存偏好'}</Button><Button disabled={busy} onClick={()=>{setSettings(null);setError('');setNotice('');setRetry(n=>n+1);}}>重新读取偏好</Button></div><p className="boundary">AI 未启用 · 使用本地预置讲解；无外网服务也能学习。录音仅回放与人工自评。</p></>}</Card>;
}
