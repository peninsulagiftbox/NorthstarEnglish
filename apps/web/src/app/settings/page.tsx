import { HealthPanel } from '@/components/HealthPanel';
import { SettingsPanel } from '@/components/SettingsPanel';
export default function Settings() { return <><p className="eyebrow">LOCAL WORKSPACE</p><h1>个人设置</h1><p className="intro">查看本地偏好与运行状态。学习不依赖外部 AI 服务。</p><div className="content-grid"><SettingsPanel /><HealthPanel /></div></>; }
