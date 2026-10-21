import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Northstar English · 本地工作台", description: "个人英语学习工作台，Phase 01 本地环境检查。" };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
