'use client';
import { useEffect, useState } from 'react';
import { getConceptReviews } from '@/lib/api/conceptReviews';
import { pendingCommand } from '@/lib/persistence/outbox';
import { ConceptQueuePager, emptyQueue } from '@/lib/review/conceptQueue';
import { Button, Card, EmptyState, Message } from '@/components/ui/Primitives';
import { ConceptReviewCardView } from './ConceptReviewCard';

export function ConceptReviewQueue() {
  const [state, setState] = useState(emptyQueue), [all, setAll] = useState(false);
  const [pager] = useState(() => new ConceptQueuePager(cursor => getConceptReviews(true, cursor), id => pendingCommand(`northstar:concept-review:${id}`), setState));
  useEffect(() => { void pager.reset(false); return () => pager.dispose(); }, [pager]);
  async function reload() { await pager.reset(all); }
  function switchMode(nextAll: boolean) { setAll(nextAll); void pager.reset(nextAll); }
  const { items, nextCursor, loading, error } = state;
  const dueCount = items?.filter(item => item.due).length ?? 0;
  return <section>
    <p className="eyebrow">跨课程概念卡</p>
    <p className="boundary">概念卡按概念与义项合并多课程错误来源；调度同为 simple_v1：还不会 1 分钟；记住后按连续自评成功次数安排 1、2、4、8、16、32 天（上限）。人工自评不代表客观掌握。</p>
    <div className="toolbar review-queue-actions">
      <Button aria-pressed={!all} onClick={() => switchMode(false)}>概念卡到期复习（已加载 {dueCount}）</Button>
      <Button aria-pressed={all} onClick={() => switchMode(true)}>全部概念卡</Button>
      <Button onClick={() => void reload()}>刷新概念卡</Button>
    </div>
    {error && <Message error>{error}<Button onClick={() => void pager.retry()}>重新加载</Button></Message>}
    {loading && <Message>{items ? '正在加载更多…' : '正在读取概念复习计划…'}</Message>}
    {items && !items.length && !nextCursor && !loading && !error && <Card><EmptyState title={all ? '还没有概念复习任务' : '当前没有到期的概念卡'}>
      <p>跨课程错误会汇集到同一张概念卡；课程中的真实错误作答会自动加入来源。</p>
    </EmptyState></Card>}
    {items?.map(item => <ConceptReviewCardView key={`${item.id}:${item.rowVersion}`} item={item} reload={reload} />)}
    {items && nextCursor && <div className="toolbar">
      <Button disabled={loading} onClick={() => void pager.more()}>加载更多概念卡</Button>
      <span className="muted">已加载 {items.length} 张{all ? '' : '到期或待确认'}概念卡，尚有分页未读取。</span>
    </div>}
    {items && !nextCursor && !loading && <p className="muted">{all ? '已加载全部' : '已读取全部分页，显示'} {items.length} 张概念卡，其中到期 {dueCount} 张。</p>}
  </section>;
}
