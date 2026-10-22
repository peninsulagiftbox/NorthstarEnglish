import Link from 'next/link';
import { Card, EmptyState } from '@/components/ui/Primitives';
export default function Reports() { return <><p className="eyebrow">YOUR LEARNING EVIDENCE</p><h1>学习报告</h1><p className="intro">看见真实尝试，而不是把浏览次数当作掌握程度。</p><Card><EmptyState title="报告汇总将在 Phase 08 开放"><p>当前可在听写页查看真实练习次数，在复习页查看听写错误来源；此处尚未提供汇总统计。</p><p>完成练习后，报告将在 Phase 08 汇总证据。当前不显示能力分数或模拟曲线。</p><Link className="button" href="/courses">浏览课程</Link></EmptyState></Card></>; }
