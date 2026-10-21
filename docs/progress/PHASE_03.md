# Phase 03｜桌面组件、路由与可恢复工作台

日期：2026-10-21（Asia/Shanghai）。用户已明确授权本阶段，并要求先读阶段提示词；已阅读根 AGENTS、实施计划、Phase 02 报告、`prompts/03_PHASE.md` 和根参考归档中的适用规范/截图。

结论：**本地功能验收 PASS_WITH_NOTES，等待用户阶段审核。****Phase 04–09 未开始；音频/来源正式发布仍因授权待审核而阻塞。**

本轮开始时存在 Phase 02 未提交改动，全部保留；没有提交、推送或部署。原始日志/截图仅位于被忽略的 `docs/evidence/phase-03/`，不意味着公开分发素材。

## 1. 改动文件与决定

- Web 路由：`apps/web/src/app/{dashboard,courses,lesson/[lessonId],review,reports,settings}/page.tsx`；根 `/` 重定向 `/dashboard`；`error.tsx` / `not-found.tsx` 提供异常入口；`layout.tsx` 共享 AppShell。
- Web 组件：`components/{shell/AppShell,lesson/LessonWorkspace,player/PlayerBar,ui/Primitives,CatalogPages,SettingsPanel}.tsx`；环境准备页 HealthPanel 保留到设置页。
- Web 逻辑：`lib/api/catalog.ts`、`lib/state/{context.ts,LessonProvider.tsx}`；单独的上下文/盲听/草稿键逻辑与视觉组件分离。`tests/context.test.ts` 补可恢复 URL、非法值/旧版本、盲听及草稿隔离检查。
- Web 样式：`app/globals.css` 保留原型深蓝/浅灰/绿色，224px 导航、课内约 2:1 双栏、76px 固定底栏；小于 980px 用右侧原生 dialog 抽屉；窄屏单列。`apps/web/package.json` 仅将生产构建指定为同版内置 webpack，不引入依赖、不改版本或锁文件。
- API：`study/StudyController.java`、新增 `V003__study_session_resume.sql`。`GET /study/resume` 返回恢复点或204，`PUT /study/resume` 与 `POST /study/sessions` 使用相同的初始化/更新语义和 If-Match；当前为单一本地浏览会话，sessionId 保留于该恢复点，不提前实现历史学习会话/练习事件。
- 写入边界：`config/LocalAccessFilter.java` 要求写请求携带允许的本地 Origin、JSON 和专用请求头。`health/HealthController.java` / `scripts/api-smoke.py` / OpenAPI 同步 phase=03 与实际浏览能力；AI/ASR/评分保持关闭。
- 启停/权限：`scripts/grant-study.py`、`scripts/local.py`；先核对容器/卷/schema 身份、成功 V003，再仅授权新恢复点表 INSERT/UPDATE。`db-test` 先打包、无 Web 启动测试 schema 迁移，再准备权限并运行全量测试。内容/设置仍只读，没有修改密码、全局运行时、容器/卷身份。
- 浏览器：新增 `scripts/workspace-browser-smoke.{js,sh}`；原 `scripts/browser-smoke.js` 的健康回归入口迁到 `/settings`。
- 文档：README、实施计划执行状态、OpenAPI、DEPENDENCIES、`docs/DESIGN_DEVIATIONS.md` 及本报告。

### 上下文与数据真实性

真实 API 提供四册 catalog_only 目录和唯一原创 Demo 01。未开放目录没有伪课程按钮。首页继续入口读取真实课/版本及恢复点；报告/复习显示功能未开放或无训练证据，不生成虚假数量/能力曲线。

URL 包含 tab/sentence/english/translation；显式 URL 优先于同课同版本恢复点。非法 Tab/句子归一到课文/首句，异课/旧版本恢复点不串用。选句更新本地预置讲解；听写 Tab 或关闭英文时，正文、译文、讲解和播放器一起遮挡目标文本。此为交互防剧透，课程 API 本身仍提供公开课文，不作为考试答案隔离机制。

MySQL 恢复点只保存浏览上下文和显示偏好；无音频引擎，不伪造播放时间。更新约350ms防抖、串行发送，提示与当前上下文匹配；未显示“浏览位置已保存”前关闭可能尚未保存。If-Match 初始 `"0"`，后续使用服务器 revision；412 不自动重试覆盖，保留页面/本机草稿并提示重新载入。DB成功但响应丢失时也停止自动写入，重读版本后再同步。

听写草稿按版本/任务/句子存 localStorage，写作按版本/课保存；只保存文本草稿，不提交、不判分、不记 practiced。存储失败提示自行复制。正式草稿/outbox、作答事件、播放句/位置和训练状态留给 Phase 04 以后。

## 2. 实际验证

| 命令/场景 | 结果与本地证据 |
| --- | --- |
| `npm run typecheck`、`npm run lint`（local.py exec） | PASS；最终证据 `logs/typecheck-release.log` / `lint-release.log` |
| `npm test` | PASS，8 项（原4项API健康 + 新4项上下文逻辑）；`logs/web-tests-final.log` |
| `npm run build` | PASS，webpack 生产构建含六路由及动态课次；`logs/web-build-release.log` |
| `python3 scripts/local.py db-test` | PASS，11 项、0失败/错误/跳过，Java21；包含完整迁移/权限新流程，`logs/api-db-test-lifecycle.log` |
| 恢复点真实 HTTP/MySQL 集成 | PASS，持久保存/ETag、缺版本428、无效值400、异句404、旧版本412、缺Origin/外域/缺专用头403；重跑迁移0条，保留原设置；同上日志 |
| `python3 -m unittest discover -s scripts/tests -v` | PASS，8 项；`logs/script-tests-retry.log` |
| `python3 scripts/api-smoke.py` | PASS，真实健康/设置/能力、Host/Origin拒绝、no-store、404/405；`logs/api-smoke-final.log` |
| 既有 `scripts/browser-smoke.sh` | PASS，设置页真实健康、加载/失败/键盘重试、四窗口无横溢出；`logs/health-browser.log` |
| 新 `scripts/workspace-browser-smoke.sh` | PASS，`passed:true`、pageErrors=[]；六路由/六Tab、恢复/草稿/防剧透、六种窗口、抽屉/焦点、双页冲突、非法/空/错误/重试；`logs/workspace-browser-final.log` |
| 主库与最小权限核对 | PASS，4册/1课/10句，V001–003成功、内容/设置只读，仅恢复点表INSERT/UPDATE；`logs/main-state.tsv` |
| 原主库设置不变 | PASS，与第二阶段逐字段相同；`logs/main-settings.tsv` / `settings-comparison.log`。原文件带身份/表头，先去除这些展示行再比对数据行 |
| OpenAPI YAML 解析、Git空白检查 | PASS，Ruby YAML解析10个路径；`git diff --check` |

### 验证中发现并修正

1. Turbopack PostCSS 辅助进程在普通及获准环境均遇到端口绑定被拒；普通 Node 回环绑定探针通过。使用同版内置 webpack 构建实际通过；保留 `web-build.log`、`web-build-retry.log` 等失败记录，不把环境失败称为编译成功。
2. 脚本首轮2项测试因沙箱禁止 ps/端口失败，获准环境8项全部通过，失败见 `script-tests.log`。
3. 草稿换句后立即断言早于React更新，验收增加对文本值的定向等待。后续恢复检查还发现“已保存”提示短暂对应上一次上下文：增加已确认上下文签名，当前上下文变化立即显示更新中，真实写入后才确认保存。
4. 原生弹窗的React autoFocus会提前改变待恢复焦点，移除该属性，先记录开启按钮，再由showModal管理焦点；Esc关闭恢复原按钮。助教窄屏使用真正右侧抽屉。
5. 视觉截图发现通用button样式把课文行居中；句子组件单独设为左对齐。首轮全页截图改为实际1440×900视口截图，用于和原型对照。
6. 两页面并发测试实际已显示412和保留草稿；首个定位器把带“重新载入”子按钮的状态容器当作精确纯文本，导致误报超时，已按状态区域文本定位后重跑。全部失败日志保留，最终结果单独记录。

## 3. 验收状态与设计复核

ui-design / ui-audit 的设计约定、tokens、组件状态与有意差异见 `docs/DESIGN_DEVIATIONS.md`。已查看首页/工作台实际渲染，与参考截图对照；不声称像素级完全一致。最终浏览器矩阵如下；1440×900工作台、979px助教抽屉、375px窗口等截图已实际查看。

| 条目 | 状态 |
| --- | --- |
| 六个实际页面 / 六个 Tab / 真实课程 API | PASS，见最终浏览器日志及截图 |
| 刷新、前进后退、显式URL、服务端无参数恢复 | PASS，见最终浏览器日志及截图 |
| 选句/助教绑定、草稿跨Tab/换句/刷新、盲听无可见目标泄露 | PASS，见最终浏览器日志及截图 |
| 224px导航、76px底栏、1440/1512/1280及窄屏无横溢出 | PASS，见最终浏览器日志及截图 |
| 窄屏助教抽屉、Esc恢复焦点、键盘Tab导航 | PASS，见最终浏览器日志及截图 |
| 未知课、非法上下文、加载/错误/空/重试、并发冲突 | PASS，见最终浏览器日志及截图 |
| 编译、类型、lint、相关单元/集成与脚本测试 | PASS |
| 音频引擎、训练提交、麦克风/评分、报告统计 | 本阶段不适用，未实现或未验证，不冒称通过 |
| 来源/合成声音授权、公开clone完整素材复现 | BLOCKED，沿用Phase02限制 |

## 4. 截图、未测范围与下一阶段依赖

截图目录：`docs/evidence/phase-03/screenshots/`，主要为 `dashboard-1440x900.png`、`courses-1440x900.png`、`lesson-1440x900.png`、`dictation-protected-1440x900.png`、`lesson-{1512,1280,979,768,375}x900.png`；另含 `courses-{loading,error,empty}.png`、`lesson-not-found.png`、`tutor-drawer-979x900.png`。

未覆盖：真实 Safari/Firefox、屏幕阅读器及完整无障碍合规、手机软键盘、浏览器麦克风权限、人工音频听感。播放器按钮明确禁用；无真实AI/ASR/专业评分。允许本地审核，不发布仍待审查素材。

审核入口为本项目 `http://127.0.0.1:3100/dashboard`，原创工作台 `/lesson/demo-01`，API8085 / MySQL3308。交付时Web/API/MySQL保持运行，本项目监督进程PID/cwd已核对，Web代理读取到第6句/课文Tab的真实恢复点；见 `logs/final-runtime.log`。停止用 `sh scripts/dev-down.sh`，保留数据和其他项目服务。

Phase 04 依赖本阶段审核后才能启动：沿用 `demo-01` / `demo-01-v1` 和稳定句子ID，实现真实音频控制/AB、正式听写与草稿协议、幂等作答/证据；浏览恢复点不当作已练习记录。本轮不会自动进入下一阶段。
