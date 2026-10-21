'use client';
export default function ErrorPage({ reset }: { reset: () => void }) { return <section className="surface"><h1>页面暂时无法显示</h1><p role="alert">请稍后重试。已保存的本机草稿可在重新打开工作台后恢复。</p><button onClick={reset}>重新加载</button></section>; }
