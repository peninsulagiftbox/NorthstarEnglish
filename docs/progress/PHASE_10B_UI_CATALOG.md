# 10B 课程中心局部视觉调整

日期：2026-10-28（Asia/Shanghai）。仅处理用户截图圈出的分区标题与目录状态标签，不开展后续阶段。

## 修改与设计

- `apps/web/src/components/CatalogPages.tsx`：两处分区标题使用相同结构，“册目录”明确为“四册目录”；计数说明改为次要文字；书册详情及可用状态分组。
- `apps/web/src/app/globals.css`：使用课程页专用类，分区顶部留白 32px、标题至卡片 16px；详情纵向间距 12px，状态至统计 8px；不可学状态使用灰蓝文字、浅灰背景和细边框，避免绿色成功态暗示。标题与说明可自动换行。
- 保留现有深蓝/青绿配色、书封、两列布局、数据来源和课程交互。未覆盖进入本轮前已有的 LearningReport 及其 CSS 改动。

## 验证与证据

使用项目级 Node 22.23.2，未改变全局版本。生产构建位于 `.local/ui-catalog/source`，不覆盖主站构建。

| 命令/检查 | 实际结果 |
| --- | --- |
| `npm run typecheck` | 退出 0 |
| `npm run lint` | 退出 0 |
| `npm test` | 27 项通过，退出 0 |
| 独立副本 `npm run build` | 首次沙箱拒绝 Next 遥测配置写入；设置 `NEXT_TELEMETRY_DISABLED=1` 后退出 0 |
| Playwright CLI 独立预览 | 1440×900、1280×900、390×900；四册状态、32px 分区间隔、8px 状态间隔、无横向溢出、展开/收起、空态、503 后重试通过，pageErrors=[] |
| `git diff --check` | 退出 0 |

浏览器 API 均由明确的测试夹具拦截；不将该结果当作个人站点真实 API 或部署验证，无数据库写入。仅启动本轮独立前端（127.0.0.1:3153）；首次沙箱禁止监听，授权提升后启动成功。

日志：`docs/handoff/evidence/ui-catalog-20261028/{build,build-retry,unit,browser}.log`（本地忽略文件）。浏览器脚本：`.local/ui-catalog/browser.cjs`。截图：`output/playwright/ui-catalog-{1440,1280,390}.png`。已人工查看 1440 与 390 截图。

## 验收与限制

- PASS：标题留白/层级统一，不再紧贴上排卡片；不可学习状态保留清晰文案并降低视觉强调；统计与状态不再拥挤。
- PASS：类型、静态检查、单测、构建及夹具浏览器验证。
- 初次预览交付时未部署；用户随后明确要求直接部署，实际结果见下节。未提交 Git。
- 本轮临时浏览器与前端验证完成后关闭；独立构建及截图保留供复核。无需数据库或下一阶段依赖，等待用户审核视觉结果。


## 用户授权后的本地部署

用户要求后续修改验证后直接部署，并要求本次立即部署。已核对已测副本所有前端 src 文件、Next 配置及 package.json 与当前工作区一致；候选同时包含此前已上线的学习路径样式。

- `.local/ui-catalog/install.py`：先核对 3100 监听子进程的 supervisor、cwd 和本项目记录，再暂存/备份/替换生产构建，仅重启本项目 Web。新 BUILD_ID：`UCi4OXypkbQhArL6nuKZF`；旧 BUILD_ID：`3kng7pNpI5-1m5g1a425B`，备份于 `.local/ui-catalog/previous-web-build-1793199483808692000`。安装退出 0，异常回退分支未触发。
- 3100 `/courses` HTTP 200、代理健康 UP；API supervisor 未变化，API JAR SHA-256 未变化。未执行数据库迁移或学习记录写入。
- `.local/ui-catalog/live-browser.cjs`：Playwright 读取真实 3100/API 验证四册标签、32px 分区间隔、灰蓝状态、真实空课程列表以及首页至少六步学习路径，`passed=true`、`pageErrors=[]`、`browserWrites=0`。健康版本仍为 `009.05`。
- 本地证据：`docs/handoff/evidence/ui-catalog-20261028/{installation.json,live-browser.log}`；实际站点截图：`output/playwright/ui-catalog-live-1440.png`。
- 本轮浏览器验收结束后关闭，3100 前端和原有 API 保持运行。部署不含提交或推送 Git。
