import { formatBeijingTime, utcTimestamp } from '@/lib/formatTime';
import type { Revision } from '@/lib/api/practice';
import { Button } from '@/components/ui/Primitives';
export function RevisionHistory({ revisions, selected, onSelect, onLoad, disabled }: { revisions: Revision[]; selected: string; onSelect: (id: string) => void; onLoad: (revision: Revision) => void; disabled: boolean }) {
  return <section><h3>不可变版本历史</h3>{!revisions.length ? <p className="muted">尚无正式版本。保存非空版本后才计入写作练习。</p> : <><label>比较版本 <select aria-label="比较版本" value={selected} onChange={e => onSelect(e.target.value)}><option value="">选择版本</option>{revisions.map(r => <option key={r.id} value={r.id}>V{r.versionNo} · {formatBeijingTime(r.createdAt)}</option>)}</select></label><ol className="revision-list">{revisions.map(r => <li key={r.id}><div><strong>V{r.versionNo}</strong> <time dateTime={utcTimestamp(r.createdAt)} title="北京时间">{formatBeijingTime(r.createdAt)}</time><p lang="en">{r.text}</p></div><Button disabled={disabled} onClick={() => onLoad(r)}>回载 V{r.versionNo} 到草稿</Button></li>)}</ol></>}</section>;
}
