import Link from 'next/link';

export default function LoginPage() {
  return <main className="login-page">
    <section className="login-story" aria-labelledby="login-heading">
      <Link className="login-brand" href="/login" aria-label="Northstar English 首页">
        <span className="brand-mark">N</span><span>Northstar<small>ENGLISH LAB</small></span>
      </Link>
      <div className="login-story-copy">
        <p className="eyebrow">A LITTLE, EVERY DAY</p>
        <h1 id="login-heading">让每一次练习，<br />都成为进步的证据。</h1>
        <p>从一句真实的表达开始。听、读、写、复习，慢慢把英语变成自己的语言。</p>
      </div>
      <div className="login-lesson-preview" aria-label="原创课程示例">
        <div className="preview-topline"><span className="preview-dot" /> ORIGINAL LESSON <span>01 / 10</span></div>
        <p className="preview-label">TODAY&apos;S FIRST SENTENCE</p>
        <blockquote>“Good morning.<br />Is this the community garden?”</blockquote>
        <div className="preview-bottom"><span className="preview-play" aria-hidden="true">▶</span><span>听一句，再试着说出来</span><span className="preview-wave" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></span></div>
      </div>
      <p className="login-story-footer">原创课程 · 本地预置讲解 · 不虚构能力评分</p>
      <span className="login-orbit login-orbit-one" aria-hidden="true" /><span className="login-orbit login-orbit-two" aria-hidden="true" />
    </section>

    <section className="login-entry" aria-labelledby="welcome-heading">
      <div className="login-entry-inner">
        <span className="login-leaf" aria-hidden="true">✳</span>
        <p className="eyebrow">YOUR PERSONAL LEARNING SPACE</p>
        <h2 id="welcome-heading">欢迎回来</h2>
        <p className="login-entry-intro">给今天的自己，留一点学习时间。</p>
        <Link className="login-submit" href="/dashboard">进入本地学习空间 <span aria-hidden="true">→</span></Link>
        <div className="login-divider"><span>学习，从这里继续</span></div>
        <div className="login-local-note"><span aria-hidden="true">⌂</span><p><strong>这是你的本地学习空间</strong><br />无需注册或密码。学习记录保存在本机服务中。</p></div>
        <p className="login-privacy">内容与练习记录由你掌控。<Link href="/settings">了解本地数据设置</Link></p>
      </div>
      <footer className="login-entry-footer">NORTHSTAR ENGLISH <span>·</span> LEARN AT YOUR OWN PACE</footer>
    </section>
  </main>;
}
