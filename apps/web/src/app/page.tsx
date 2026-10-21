import { HealthPanel } from "@/components/HealthPanel";
import Link from "next/link";

export default function Home() {
  return <div className="app-shell">
    <aside className="sidebar"><Link className="brand" href="/" aria-label="Northstar English 首页"><span className="brand-mark">N</span><span>Northstar<small>ENGLISH LAB</small></span></Link>
      <p className="nav-label">LEARNING SPACE</p><nav aria-label="主导航"><Link className="nav-active" href="/" aria-current="page">本地工作台</Link></nav>
      <p className="sidebar-note">个人使用 · 本地保存<br />工程骨架 / Phase 01</p></aside>
    <div className="main-shell"><header className="topbar"><span>WORKSPACE / <strong>环境准备</strong></span><span className="local-badge">本地运行</span></header>
      <main><p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p><h1>为下一次学习，做好准备。</h1><p className="intro">先确认本地服务正常，再开始构建原创单课学习体验。</p>
        <section className="welcome" aria-labelledby="welcome-title"><p className="eyebrow">NORTHSTAR ENGLISH · PHASE 01</p><h2 id="welcome-title">从一个可靠的起点开始</h2><p>工程环境已进入第一阶段。课程内容与训练功能将在后续阶段审核后开放。</p></section>
        <div className="content-grid"><HealthPanel /><section className="surface empty" aria-labelledby="learning-title"><p className="eyebrow">LEARNING SPACE</p><h2 id="learning-title">学习内容尚未开放</h2><p className="muted">当前只验证本地运行环境，没有学习记录或练习统计。</p><p className="boundary">本地预置讲解、录音回放 / 人工自评将在对应阶段实现；当前未接入 AI 或语音评测。</p></section></div>
      </main><footer>Northstar English · 数据留在本地，学习一步一步来。</footer>
    </div>
  </div>;
}
