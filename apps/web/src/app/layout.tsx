import type { Metadata } from 'next';
import { AppShell } from '@/components/shell/AppShell';
import './globals.css';
export const metadata: Metadata = { title: 'Northstar English · 让每次练习都有依据', description: '个人英语学习空间，从原创课程开始，记录每一次真实练习。' };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body><AppShell>{children}</AppShell></body></html>;
}
