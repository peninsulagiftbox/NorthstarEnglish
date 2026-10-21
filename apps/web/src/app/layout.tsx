import type { Metadata } from 'next';
import { AppShell } from '@/components/shell/AppShell';
import './globals.css';
export const metadata: Metadata = { title: 'Northstar English · 本地工作台', description: '个人英语学习工作台，原创课程与本地预置讲解。' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body><AppShell>{children}</AppShell></body></html>;
}
