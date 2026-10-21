import Link from 'next/link';
export default function NotFound() { return <section className="surface"><h1>页面不存在</h1><p className="muted">请检查本地链接，或返回课程中心继续浏览。</p><Link className="button primary" href="/courses">返回课程中心</Link></section>; }
