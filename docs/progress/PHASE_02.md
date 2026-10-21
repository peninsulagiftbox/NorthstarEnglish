# Phase 02｜原创内容入库、来源记录与课程 / 媒体 API

日期：2026-10-21（Asia/Shanghai）。结论：**本地功能验收 PASS_WITH_NOTES；素材正式发布 BLOCKED，等待来源及声音授权审核。Phase 03–09 未开始，报告后等待用户审核。**

用户明确授权本阶段并要求先读提示词；已阅读根 AGENTS、实施计划、Phase 01 报告、`Northstar_English_Codex/prompts/02_PHASE.md` 及适用参考设计。起始 Git 工作区干净。根 `references/phase1/` 起初不存在，实际输入位于参考包，本阶段已逐文件校验归档。

原始日志、截图和环境状态仅保留在被忽略的 `docs/evidence/phase-02/`；下文路径用于本地复核，不代表公开分发。未提交、推送或部署。

## 1. 修改文件

- 内容工具：`scripts/extract-demo.py`、`scripts/validate-content.py`、`scripts/tests/test_content.py`。
- 冻结内容：`content/demo-01/v1/lesson.json`、`manifest.json`、`audio/01.mp3…10.mp3`。音频继续被 Git 忽略。
- 参考归档：`references/phase1/` 中原始参考包六个文件及 `archive-manifest.json`；HTML/图片继续被 Git 忽略，保留根目录同名异版输入。
- 后端：`apps/api/src/main/java/local/northstar/catalog/{ContentPackage,ContentSeeder,CatalogController}.java`，`V002__catalog_content_versions.sql`，`health/HealthController.java` 的阶段及内容 API 能力声明。
- 测试：`apps/api/src/test/java/local/northstar/catalog/{ContentPackageTest,CatalogIntegrationTest}.java`；`scripts/content-browser-smoke.{sh,js}`；更新 `scripts/api-smoke.py` 的阶段能力契约。
- 文档：`README.md`、`docs/CONTENT_MANIFEST.md`、`docs/openapi.yaml`、实施计划执行状态、`docs/PUBLICATION.md`、本报告；`.gitignore` 补充归档原型及提取音频的发布排除。
- 没有修改前端业务模块、引入新依赖、改变锁文件或全局 Node/Java；没有开发后续学习阶段。

## 2. 关键设计与运行事实

### 提取、版本与来源

安全解析冻结原型中的数据字面量，不执行 HTML / JavaScript，不使用 eval。源文件 SHA-256 固定为 `0debbd92494b34f9905e38386fe57fc833170c8dfd2ed50e1fa1cc5a4623306f`；已存在文件内容不一致时拒绝覆盖。

唯一独立原创课为 `demo-01` / `demo-01-v1` / *The Neighborhood Garden*，`bookId=null`。10 句含说话者、原文、译文、讲解及 focus；5 个词语块和 15 个练习定义（10 听写、1 阅读、1 写作、3 测验）带固定 ID 及来源句。标准答案保存在服务端版本包，课程 GET 删除答案键及测验答案解释；本阶段没有判分接口或练习记录。

10 个严格解码 MP3 共 216,564 字节，逐一检查文件头、格式、大小、SHA-256，并通过 macOS `afinfo` 读取其解码器估计时长。每句 `startMs=0,endMs=durationMs`，不虚构整课时间轴或按字数猜测时长。浏览器实播单独验证。

来源记录 `demo-text-v1` / `demo-audio-v1` 的 `sourceType=original` 表示参考材料声明；权利人、生成工具、声音及独立证明未知，均保持 `pending_review`、`usageScope=local_test_only`、`releaseReady=false`。已询问用户补充来源，未据此伪造凭据。**技术测试通过不能等同于素材授权确认或正式发布通过。**

### 数据库与幂等

新增 `content_license`、`book`、`lesson`、`lesson_version`、`audio_asset`、`sentence` 六表；唯一键与复合外键约束版本归属、当前版本归属、句子顺序及音频归属。四册只有 `catalog_only` 元信息（144 / 96 / 60 / 48），没有教材课文、录音或 348 条伪课程。

Flyway 后由 `ContentSeeder` 使用迁移数据源事务导入；锁定项目标记避免并发播种。重跑先比较版本哈希、manifest 哈希、JSON 及各内容行，完全一致才返回，不覆盖已发布内容、不静默修复差异。运行数据源账号仍只有 SELECT，未扩权。词汇及练习暂存版本 JSON，后续阶段才建正式知识点、练习和作答表。

主库实际为 **4 book / 1 lesson / 1 lesson_version / 10 sentence / 10 audio_asset / 2 content_license**。主库 V002 一次成功；V001 设置和项目身份在本次迁移前后完全一致。测试继续使用项目既有独立 `northstar_phase01_test`，没有删除/重建 schema、容器或卷。

### API 与本地服务

沿用统一 `/api/v1`，没有增加提示词旧 `/api/books` 等别名：

- `GET /books`：四册元信息和独立原创课；`GET /lessons`：唯一可用原创课列表。
- `GET /lessons/demo-01`：一次返回版本、10 句、预置讲解、词汇、练习定义、来源记录及音频 URI。
- `GET /licenses/{id}`：查询来源/审查记录。
- `GET /audio/{id}`：数据库解析文件、真实路径限制、大小及哈希校验，支持 200 / 206 和后缀 Range；非法/越界范围 416。
- 未知资源为规范 404；文件缺失/损坏为 `503 AUDIO_UNAVAILABLE`，课程响应也不会在缺音频时假装完整可用。

能力声明为 phase=02、contentApiAvailable=true；learningContentAvailable=false 表示学习 UI / 训练尚未开放。AI / ASR / 专业发音评分仍关闭。前端继续使用 Phase 01 环境准备页，不能把测试面板当作工作台交付。

仅按监督进程 PID/cwd、Compose 标记核对后重启本项目服务。交付时 Web `127.0.0.1:3100`、API `127.0.0.1:8085`、MySQL `127.0.0.1:3308` 保持运行供审核。

## 3. 实际验证

| 命令 / 场景 | 结果与本地证据 |
| --- | --- |
| `python3 scripts/extract-demo.py` 连续两次 + `python3 scripts/validate-content.py` | PASS；固定输出无差异，10 句/10 音频一一对应，关联/哈希/解码器时长通过；`logs/content-extraction.log` |
| `python3 -m unittest discover -s scripts/tests -v` | 获准环境 PASS，8 项，含拒绝可执行表达式及拒绝覆盖冻结文件；`logs/scripts-tests-retry.log` |
| `python3 scripts/local.py db-test` | PASS，Java21 编译/打包，10 项测试，0 失败/错误/跳过；`logs/api-db-test-complete.log` |
| 真实 MySQL 内容集成 | 两次再播种行数不变、Flyway 重跑 0 条、运行账号写入拒绝、未知课/音频/来源规范404、两种 Range206、非法及越界416、缺失/损坏503、冻结哈希变化拒绝；同一集成日志 |
| 关联约束 | 重复句序、未知音频、错误当前版本、跨课当前版本及跨版本句子均拒绝；临时测试对象事务回滚，无额外课程残留；同一集成日志 |
| `npm run typecheck && npm run lint && npm test && npm run build`（经 local.py exec） | PASS，4 项前端测试及 Next 生产构建；`logs/web-checks.log` |
| 主库内容与设置核对 | PASS，六类内容行数、四册占位、独立 Demo、pending_review、V002成功；`logs/main-catalog-state.tsv`。前后项目标记和设置 TSV 经 `cmp` 完全一致 |
| `python3 scripts/api-smoke.py` | PASS，实际健康/能力/设置、no-store、404/405/Host403/Origin403、无通配 CORS；`logs/api-http-smoke.log` |
| `python3 scripts/local.py exec sh scripts/content-browser-smoke.sh` | PASS，Chromium 经 Web 同源转发读取10个音频，逐段时间推进并播放至 ended，浏览器时长与manifest误差不超过150ms，无 pageerror；`logs/content-browser-smoke-final.log` |
| `python3 scripts/local.py exec sh scripts/browser-smoke.sh` | PASS，健康页加载/成功/模拟503/键盘重试，四窗口尺寸及无横向溢出；`logs/health-browser-regression.log` |

普通沙箱首轮 Python 测试因禁止 `ps` 和绑定本地端口失败，Java Mockito 亦因自附加限制失败；日志保留为 `scripts-tests.log` / `api-unit.log`。获准环境中的完整检查通过，没有把环境失败冒称通过。

### 发现并修正的问题

1. 测试库首次 V002 在创建 sentence 时，MySQL 拒绝列级 CHECK 引用另一列。修为表级约束，并让 DDL 可重入。只读确认五个新表均为空、主库未执行 V002 后，保存失败历史行到 `logs/failed-migration-row.tsv`，定向删除独立测试库唯一 success=0 的 V002 历史行，再执行修正迁移。没有删表、改写成功迁移、执行 clean/repair 或伪造成功历史。原失败保留在 `logs/api-db-test.log`。
2. 课程来源查询因 `SELECT DISTINCT details_json ORDER BY id` 触发 MySQL 排序限制，返回503；已移除不必要的 DISTINCT（主键和 IN 已保证去重）。原失败见 `logs/api-db-test-retry.log`，最终全量测试通过。
3. 浏览器首轮已播放至十段 ended，但 CLI 不将 console.log 收集为结构化返回值，外层验收失败；改为返回结果并重新实播，最终日志含 `passed:true` 和十项记录。保留首轮 `logs/content-browser-smoke.log`，没有以首轮失败代替正式通过证据。

## 4. 验收状态

| 条目 | 状态 |
| --- | --- |
| 原创 10 句及对应译文/讲解/词汇/答案安全提取 | PASS |
| 10 个独立 MP3 格式、大小、哈希、局部时长 | PASS |
| 来源、版本、稳定 ID 及四册 catalog_only | PASS（来源审查状态明确待审） |
| 幂等播种、唯一键及同课/版本约束 | PASS |
| 一次 API 获得真实 10 句及音频 URI | PASS |
| 10 个音频实际请求、解码并播放至 ended | PASS（自动化 Chromium；未人工听感验收） |
| 缺失、损坏、未知课、Range、路径穿越/符号链接拒绝 | PASS（HTTP集成及文件边界单测） |
| 未导入未经许可教材正文/录音 | PASS（只有原创 Demo，四册仅元信息） |
| 单元/真实数据库集成、前端编译、必要浏览器验收 | PASS |
| 合成工具/声音授权凭据及正式素材发布 | BLOCKED：信息未知，不能签署授权确认 |
| 新机器仅从公开仓库独立复现 Phase02 | BLOCKED：原型及音频未公开分发 |
| 真实学习工作台、训练证据、麦克风/AI/恢复演练 | 本阶段不适用，未实现/未验收 |

## 5. 截图与后续依赖

`docs/evidence/phase-02/screenshots/audio-api-browser-audit.png` 已实际查看，显示十段 ended 和待审查来源提示；它是 Playwright 临时注入的明确标记测试面板，不是正式产品 UI。健康页回归截图仍由原脚本输出至 `output/playwright/health-*.png`。

运行与内容查询可在本地审核；停止使用 `sh scripts/dev-down.sh`，保留专属数据。正式分发前需补齐音频生成工具、声音来源、适用授权与证明，并审查文本/讲解权利。公开 clone 缺少音频时 API 启动会明确失败，不生成伪素材。

审核后 Phase 03 才可开始桌面组件、路由和会话恢复。后续沿用 `demo-01`、`demo-01-v1` 及现有稳定资源 ID；播放/听写功能在 Phase 04 实现，不把本次 API 播放测试视为已实现正式播放器。Chromium 实测解码时长比 afinfo 估计短 53–77ms，后续 seek / AB 应以媒体元素实际 duration 限制范围，不能将包内估计值当作精确对齐。当前不自动进入下一阶段。
