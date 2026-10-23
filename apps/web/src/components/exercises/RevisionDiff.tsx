/** Paragraph-level exact comparison; no linguistic quality judgement. */
export function RevisionDiff({ before, after }: { before: string; after: string }) {
  if (before === after) return <p className="muted">内容相同。</p>;
  return <div className="revision-diff"><section><h4>比较版本</h4><del>{before || '（空）'}</del></section><section><h4>当前草稿</h4><ins>{after || '（空）'}</ins></section></div>;
}
