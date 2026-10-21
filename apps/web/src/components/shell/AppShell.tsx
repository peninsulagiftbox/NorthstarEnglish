'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { getResume } from '@/lib/api/catalog';
import { lessonHref } from '@/lib/state/context';
const navigation = [['/dashboard', '▣', '学习首页'], ['/courses', '▤', '课程中心'], ['/review', '◇', '智能复习'], ['/reports', '▥', '学习报告'], ['/settings', '⚙', '个人设置']];
export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const [current, setCurrent] = useState('/courses');
  useEffect(() => { let active = true; getResume().then(r => { if (active) setCurrent(r ? lessonHref(r) : '/courses'); }).catch(() => {}); return () => { active = false; }; }, [path]);
  const title = navigation.find(n => n[0] === path)?.[2] ?? '课文精学';
  return <div className="app-shell"><a className="skip-link" href="#main-content">跳到主要内容</a>
    <aside className="sidebar"><Link className="brand" href="/dashboard"><span className="brand-mark">N</span><span>Northstar<small>ENGLISH LAB</small></span></Link>
      <p className="nav-label">LEARNING SPACE</p><nav aria-label="主导航">{navigation.map(([href, icon, label]) => <Link key={href} href={href} className={path === href ? 'nav-active' : ''} aria-current={path === href ? 'page' : undefined}><span aria-hidden="true">{icon}</span>{label}</Link>)}</nav>
      <div className="classroom"><p className="nav-label">MY CLASSROOM</p><Link className={path.startsWith('/lesson/') ? 'nav-active' : ''} href={current} aria-current={path.startsWith('/lesson/') ? 'page' : undefined}>◎　当前学习课程</Link></div>
      <div className="sidebar-note"><strong>🌱 坚持每次一点点</strong><p>从一句真实的表达开始。<br />浏览与草稿不计练习完成。</p><small>个人使用 · 本地数据<br />原创内容 · 授权待审查</small></div></aside>
    <div className="main-shell"><header className="topbar"><span>LEARNING / <strong>{title}</strong></span><span className="local-badge">● 本地测试版</span></header><main id="main-content">{children}</main></div>
  </div>;
}
