'use client';
import { useState } from 'react';
import { request } from '@/lib/api/catalog';
import { Button, Card, Message } from './ui/Primitives';
type Preview = { valid: boolean; tableCounts: Record<string,number>; warning: string; sha256: string };
export function DataTransferPanel() {
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [notice,setNotice]=useState('');
  const [preview,setPreview]=useState<Preview|null>(null);
  const download=async()=>{setBusy(true);setError('');setNotice('');try{const value=await request('/data/export');const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`northstar-${new Date().toISOString().replaceAll(':','-')}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setNotice('JSON 已生成并交给浏览器下载；请核对文件。录音文件需另行运行备份脚本。');}catch(e){setError(e instanceof Error?e.message:'导出失败');}finally{setBusy(false);}};
  return <Card className="data-transfer-card"><div className="section-heading data-transfer-header"><h2>数据导出与恢复预检</h2></div><p>导出包含服务端学习记录、作文版本、课程进度、复习信息与内容版本。含个人原始作答，请妥善保管。</p><p className="boundary">不包含尚未同步的浏览器草稿、待发送事件、录音二进制、数据库密码或模型密钥。完整媒体备份请使用 scripts/backup.sh。</p>{error && <Message error>{error}</Message>}{notice && <Message>{notice}</Message>}<div className="settings-card-footer data-transfer-actions"><label className="data-transfer-file">选择 JSON 进行只读预检 <input aria-label="选择恢复 JSON" type="file" accept="application/json,.json" disabled={busy} onChange={async e=>{const file=e.target.files?.[0];e.target.value='';setPreview(null);setError('');setNotice('');if(!file)return;if(file.size>32*1024*1024){setError('文件超过 32 MiB，未读取。');return;}setBusy(true);try{const body=JSON.parse(await file.text());setPreview(await request<Preview>('/data/import-preview',{method:'POST',headers:{'Content-Type':'application/json','X-Northstar-Request':'local-workspace'},body:JSON.stringify(body)}));}catch(e){setError(e instanceof Error?e.message:'预检失败');}finally{setBusy(false);}}} /></label><Button disabled={busy} onClick={()=>void download()}>{busy?'正在处理…':'导出学习 JSON'}</Button></div>{preview && <div role="status"><h3>格式预检通过 · 尚未恢复</h3><p>{preview.warning}</p><p>共 {Object.keys(preview.tableCounts).length} 张表，{Object.values(preview.tableCounts).reduce((a,b)=>a+b,0)} 条记录。</p><p>下一步：先导出当前数据备份，再按 docs/BACKUP_RESTORE.md 使用 scripts/restore.sh，明确指定全新隔离目标。界面不会覆盖当前库。</p></div>}</Card>;
}
