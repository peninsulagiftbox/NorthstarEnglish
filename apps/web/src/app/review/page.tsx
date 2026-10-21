import Link from 'next/link';
import { Card, EmptyState } from '@/components/ui/Primitives';
export default function Review() { return <><p className="eyebrow">RECALL & REVIEW</p><h1>智能复习</h1><p className="intro">从真实练习中的错误出发，再给自己一次回忆的机会。</p><Card><EmptyState title="复习功能尚未开放"><p>当前没有已提交的训练证据。复习卡片与调度将在 Phase 07 开发，浏览句子与草稿不会生成复习卡。</p><Link className="button primary" href="/courses">先浏览原创课 →</Link></EmptyState></Card></>; }
