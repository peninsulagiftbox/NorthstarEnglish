async (page) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const response = await page.request.get(new URL("/api/v1/health", page.url()).toString());
  if (response.status() !== 200 || (await response.json()).project !== "northstar-english-local-v1") {
    throw new Error("Expected actual project API health");
  }
  await page.goto("http://127.0.0.1:" + new URL(page.url()).port + "/settings");
  await page.getByText("已连接", { exact: true }).first().waitFor();
  await page.getByRole("heading", { name: "本地偏好" }).waitFor();
  for (const [width, height] of [[1440, 900], [1512, 900], [1280, 800], [375, 812]]) {
    await page.setViewportSize({ width, height });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)) throw new Error("Horizontal overflow: " + width);
    if (width === 1440 && await page.locator(".sidebar").evaluate(el => el.getBoundingClientRect().width) !== 224) {
      throw new Error("Sidebar must remain 224px");
    }
    await page.screenshot({ path: `output/playwright/health-${width}x${height}.png`, fullPage: true });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route("**/api/v1/health", async route => { await gate; await route.continue(); });
  await page.getByRole("button", { name: "重新检查" }).click();
  await page.getByText("正在检查 API 与数据库连接…", { exact: true }).waitFor();
  if (!await page.getByRole("button", { name: "重新检查" }).isDisabled()) throw new Error("Loading button must be disabled");
  await page.screenshot({ path: "output/playwright/health-loading.png" });
  release();
  await page.getByText("已连接", { exact: true }).first().waitFor();
  await page.unroute("**/api/v1/health");
  await page.route("**/api/v1/health", route => route.fulfill({ status: 503, contentType: "application/problem+json", body: '{"status":503}' }));
  await page.getByRole("button", { name: "重新检查" }).click();
  await page.getByText("本地服务或数据库暂不可用，请检查启动日志后重试。", { exact: true }).waitFor();
  if (await page.getByText("已连接", { exact: true }).count()) throw new Error("Failure cannot leave UP visible");
  await page.screenshot({ path: "output/playwright/health-error.png" });
  await page.unroute("**/api/v1/health");
  const nextHealth = page.waitForResponse(response => response.url().endsWith("/api/v1/health") && response.status() === 200);
  await page.getByRole("button", { name: "重新检查" }).focus();
  await page.keyboard.press("Enter");
  await nextHealth;
  await page.getByText("已连接", { exact: true }).first().waitFor();
  if (errors.length) throw new Error("Browser runtime errors: " + errors.join("; "));
  return { passed: true, checks: "actual health, empty, loading, 503, keyboard retry, four viewports, no horizontal overflow or runtime errors" };
}
