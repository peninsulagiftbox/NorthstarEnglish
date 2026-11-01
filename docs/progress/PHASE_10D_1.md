# Phase 10D-1｜知识概念登记、冻结证据与浏览 实施报告

日期：2026-10-31（Asia/Shanghai）。绑定 HEAD：`ff0dbe1f8b89a1817c2f5a0e7ba0755d5f971188`（实施全程未提交）。个人库（3308）与个人服务（3100/8085）全程只读未触碰；所有迁移、测试、服务与浏览器验证均在 `.local/phase10d` 隔离副本与专用容器命名空间（`-20261031d`，端口 3339+、API 8176、Web 3196 回环）完成。依据 `docs/phase10/10D_IMPLEMENTATION_PLAN.md` §7 D01 条目 1–20 实施并验收。**报告后停止，等待用户审核；未提交、未部署、未开始 10D-2。**

## 1. 改动了什么

| 领域 | 内容 |
| --- | --- |
| 数据库 | 新增 V012.01–V012.07：`knowledge_concept`/`knowledge_concept_revision`（NFC 规范键、utf8mb4_0900_bin、唯一键防同 kind+sense 重复）、`knowledge_occurrence`（lesson/paragraph/sentence 三 scope，显式引用选定修订）、`legacy_knowledge_link`（有依据的旧知识点映射）、`exercise_sentence`/`exercise_knowledge`（题目来源句与知识关联，主锚点约束）、`knowledge_projection`（注册冻结投影 + relations_sha256）、`attempt_knowledge`（每次尝试的服务端知识证据快照，含 source_sha256）；冻结守卫触发器；FK 方向保证恢复无循环（V012_04 的来源句 FK 指向 `sentence(id,lesson_version_id)`，修正了实施中发现的错误指向） |
| 后端 | 新增 `local.northstar.knowledge` 包：`KnowledgeConcepts`（入口 NFC/空白规范化与校验）、`KnowledgeRegistrationCli`（单事务登记：概念/修订/出现/legacy/来源句/练习关联校验，关系数>0 时冻结投影并核验哈希不变）、`KnowledgeSources`（提交尝试时按 `exercise_knowledge` 冻结服务端证据，永不信任客户端 concept 参数）、`KnowledgeController`（3 个 GET：概念分页、概念详情、出现位置；可见性统一为 lesson available + version published + license confirmed（demo 例外）；撤回课程仅返回受限元数据）；`ExerciseController`/`QuizReviewController` 三条尝试路径接入 `KnowledgeSources.record`；`ContentPublication`/`ExportController`/`ReportController` 发布快照与导出分类同步知识关系 |
| 前端 | 新增 `lib/api/knowledge.ts`（API 类型）与 `KnowledgeConcepts.tsx`（跨课概念区块：loading/success/error/empty、展开出现位置、受限来源提示）；`VocabularyPanel` 挂载；`globals.css` 最小样式。effect 内不做同步 setState（对齐 react-hooks 规则），播放器与既有布局未改 |
| 脚本 | 新增 `scripts/phase10d.py` 与 `scripts/phase10d_isolated.py`（迁移/故障/测试/serve 隔离编排，含放宽 socketTimeout=600000）；`data-transfer.py` schema 白名单加 `012.07` 并支持 `--phase10d` |
| 文档 | `docs/openapi.yaml` 新增 `/knowledge/concepts`、`/knowledge/concepts/{id}`、`/knowledge/concepts/{id}/occurrences`（node js-yaml 解析 43 paths 合法） |

## 2. 关键设计决定

1. 不可变性由数据库约束承担：`knowledge_projection.frozen` 后守卫触发器拒绝注册表写入；`attempt_knowledge` 快照含逐字段 JSON 与 SHA-256，新修订不影响历史（测试验证 byte-identical）。
2. 浏览端可见性集中在控制器一处（`VISIBLE` 谓词），概念列表、详情、出现位置共用；撤回行只保留 id/scope/versionId/lessonId/visible + `restricted:true`。
3. `visible`/`sentenceScope` 在控制器统一规范化为 boolean（MySQL 布尔表达式返回 1/0 Integer，直接 `Boolean.FALSE.equals` 会漏判撤回行——实施中发现并修复）。
4. `KnowledgeSources.record` 的时间戳在 SQL 内 `CAST(... AS CHAR)` 输出，规避该连接配置下 `LocalDateTime` 无法转 `java.sql.Timestamp` 的运行时错误。
5. 前端数据加载遵循仓库既有模式（`ReviewQueue`）：effect 只发起请求，setState 全部在 then/catch 回调；"重新读取"复用无游标的 `load()` 完成重置。

## 3. 运行命令与结果（argv/hash 见 `docs/handoff/evidence/phase10d/execution-commands.jsonl`、`migrations/commands.jsonl`；文件清单见 `manifest-sha256.txt`）

| 验证 | 结果 |
| --- | --- |
| `mvnw package -DskipTests`（隔离副本，JDK 21） | PASS（compile-1793444161417281000.log） |
| `migrations`（固定旧备份逐值升级 + 空库迁移至 012.07，两次重启快照一致） | PASS（`migrations/upgrade-acceptance.json`、`empty-acceptance.json`：oldCellsExact/restartsExact=true） |
| 迁移故障演练 V012_01–V012_06（文件 SQL 与 SIGNAL 注错逐条）+ V012_07 fault_migrator | PASS（`migrations/fault-0*-acceptance.json`） |
| `KnowledgeSourcesIntegrationTest`（真实 MySQL：A/B 注册、三 scope、legacy 映射、SQL/FK 负例、browse 可见性与分页、听写/阅读/quiz 三路径证据冻结、幂等回执、撤回受限、证据不可变性） | PASS（knowledge-sources-1793444585971318000.log） |
| `KnowledgeNormalizationIntegrationTest`（规范化矩阵、NFC/NFD 等价冲突、共享义项、跨 kind 同名、登记负例、冻结守卫） | PASS（knowledge-normalization-1793445002359372000.log） |
| `QuizScaleIntegrationTest`、`QuizReportR1IntegrationTest` 回归 | PASS（quiz-scale-1793445011780660000.log、quiz-report-r1-1793445033328998000.log） |
| Web `npm run typecheck` / `lint` / `test` / `build`（隔离副本） | PASS（web-*-d1-*.log） |
| `python3 -m unittest discover -s scripts/tests` | PASS 18/18（py-tests-1793445339449906000.log） |
| 浏览器 D-1 冒烟（Playwright 1440×900，隔离 8176/3196，校验 test 库响应头与 012.07） | PASS：demo 词汇页渲染跨课概念、展开出现位置、课程标题/句子文本钻取、无页面错误；截图 `output/playwright/phase10d/knowledge-concepts-demo.png`（browser-smoke-script.js） |

## 4. D01 逐项验收（计划 §7 条目 1–20）

| 条目 | 结论 | 证据 |
| --- | --- | --- |
| 1–3 规范化（空格/撇号/连字符/NFC/大小写） | PASS | KnowledgeNormalization：`don't`、`café` NFD→NFC、`well-known`、`Bank` 保留 |
| 4–7 Unicode 空白/多空格折叠、空/超长/255 码点、共享义项与跨 kind 同名 | PASS | 同上 + `look after` 折叠（修正了断言笔误）、`x*255`/`x*256` 边界、bank 两义见 KnowledgeSources（kn-bank-fin/kn-bank-riv 共享 canonicalKey 分开义项） |
| 8–10 A/B 全结构、三 scope、legacy 有依据映射与未映射 | PASS | KnowledgeSources 注册 A/B/C（REGISTERED、ALREADY_FROZEN 幂等） |
| 11–14 错课/错版/段句包含错/外题/外 occurrence 负例（服务校验 + FK） | PASS | `sqlNegatives()`（CV 拒绝、跨版本 occurrence 拒绝、lesson scope 绑段拒绝）+ `fault-04` FK 实测 |
| 15–16 客户端伪 concept 不影响来源；同 event 重复/异 payload | PASS | `KnowledgeSources` 仅按 exercise_knowledge 冻结；command_receipt 重放同响应、IDEMPOTENCY_CONFLICT |
| 17 三路径知识写入原子性 | PASS | demoDictation/readingAttempt/quizSubmit 证据行齐全；`invalidQuizRollsBack` 全或无 |
| 18 课→版→段句→题→attempt→occurrence→concept 完整钻取 | PASS | browse：概念分页/详情/出现位置（sentenceText、exerciseCount、wrongAttemptCount） |
| 19 新版本/新解释不改历史 | PASS | `immutability()`：插入 rv-bank-fin-2 后 attempt 证据 byte-identical |
| 20 撤回后正文/答案/音频/来源不绕权利控制 | PASS | withdrawn 后 occurrences 仅受限元数据、lessonCount 计数下降（hidden 断言）；API 层 VISIBLE 全路径复用 |
| 浏览器 D-1（计划 §6：两课浏览、多义项、钻取、版本切换、撤回） | 部分覆盖 | 已测：demo 概念浏览/展开/句子钻取/截图/无页面错误（见 §3）。未测：两课并列浏览与撤回的 UI 呈现（API 层已由 D01 18/20 覆盖），列入 §5 |

## 5. 未测项与风险

1. 浏览器未覆盖：两课并列概念浏览、UI 上的版本切换与撤回受限提示（API 层已验证）；`conceptReviews` 属 10D-2，未实现。
2. 实体麦克风、Safari 播放等无法自动化项：本阶段未涉及录音路径改动，沿袭 10B/10C 结论。
3. `attempt_knowledge` 的 INSERT 权限仅授予测试 schema 的 app 用户；个人库升级（10D-2 部署范围）时需同步授权，恢复工具 `--phase10d` 的备份/恢复端到端演练归入 D02 恢复验收（计划 §7 恢复续学条目）。
4. 实施中发现并修复的真实缺陷（均已回归验证）：V012_04 FK 指向错误；CLI 练习关联校验/INSERT 列序错误；控制器 SQL 文本块空白剥离、`nextCursor` NPE、`sentenceScope`/`visible` 类型误判；`KnowledgeSources` 时间戳 ClassCastException；测试夹具的 lessonId 参数错误与清理顺序；前端 effect 同步 setState。

## 6. 下一阶段依赖（10D-2，需另行批准）

`conceptReviews` API 与概念复习组件、多源卡分组、自评/CAS/断网恢复、`ReadingQuestion`/`ReviewQueue` 接入、D02 验收矩阵、恢复续学演练（含 `--phase10d` 备份/恢复端到端）、完整旧回归与 `PHASE_10D_2.md`/`PHASE_10D.md` 汇总。个人库升级、Git 提交推送均不在本轮授权内。
