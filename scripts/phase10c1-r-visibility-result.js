async page => {
  const result = await page.evaluate(() => {
    clearInterval(window.c1RSampleTimer);
    const events = window.c1RVisibility ?? [];
    const transitions = events.filter(x => x.event === 'visibilitychange');
    return { status: 'NOT VERIFIED', transitions, events,
      observedHidden: transitions.some(x => x.visibility === 'hidden' && x.trusted),
      reason: 'Read-only diagnostic; native action provenance and resume checks must be reviewed separately. No visibilitychange was synthesized.' };
  });
  try {
    if (!await page.locator('audio').evaluate(a => a.paused)) await page.getByRole('button', { name: '暂停播放', exact: true }).click();
  } catch (error) { result.pauseCleanupError = String(error); }
  return result;
}
