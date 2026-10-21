'use client';
import { useEffect, useState } from 'react';
import { request } from '@/lib/api/catalog';
import { Button, Card, Message } from '@/components/ui/Primitives';
type Settings = { timezone: string; defaultSpeed: number; showTranslation: boolean; showHints: boolean };
export function SettingsPanel() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => { let active = true; request<Settings>('/settings').then(s => { if (active) setSettings(s); }).catch(() => { if (active) setFailed(true); }); return () => { active = false; }; }, [retry]);
  return <Card><h2>本地偏好</h2>{failed ? <><Message error>偏好读取失败。</Message><Button onClick={() => { setFailed(false); setRetry(n => n + 1); }}>重试读取偏好</Button></> : !settings ? <Message>正在读取已保存偏好…</Message> : <><dl className="service-list"><div><dt>时区</dt><dd>{settings.timezone}</dd></div><div><dt>默认速度</dt><dd>{settings.defaultSpeed}×</dd></div><div><dt>默认译文</dt><dd>{settings.showTranslation ? '显示' : '隐藏'}</dd></div><div><dt>预置提示</dt><dd>{settings.showHints ? '显示' : '隐藏'}</dd></div></dl><p className="boundary">以上为 API 中的当前配置；完整设置编辑在 Phase 08 开放。工作台内可切换英文与译文，偏好随浏览位置保存。</p></>}</Card>;
}
