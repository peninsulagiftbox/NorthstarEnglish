import Link from 'next/link';
import { Card, EmptyState } from '@/components/ui/Primitives';
export default function Reports() { return <><p className="eyebrow">YOUR LEARNING EVIDENCE</p><h1>学习报告</h1><p className="intro">看见真实尝试，而不是把浏览次数当作掌握程度。</p><Card><EmptyState title="还没有可生成的学习报告"><p>训练提交与报告统计尚未实现；没有可展示的真实作答、写作版本或复习记录。</p><p>完成练习后，报告将在 Phase 08 汇总证据。当前不显示能力分数或模拟曲线。</p><Link className="button" href="/courses">浏览课程</Link></EmptyState></Card></>; }
