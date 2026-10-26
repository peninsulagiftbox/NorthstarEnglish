# Phase 10A｜通用课程架构与教学系统设计

> 10A-R更新（2026-10-26）：独立设计评审CONDITIONAL PASS，已按R1–R4和五项补充优化局部修订，等待复审。实际范围与验证见下方“10A-R实际修订与验证记录”。以下原10A记录保留为历史，不能当本轮重新运行的证据。

2026-10-26（Asia/Shanghai）。状态：设计文档已完成，等待人工审核；未进入10B。会话没有Plan模式切换工具，按规划边界执行，只新增文档。

1. 修改：审计真实Demo加载/播种、V001–V008、API、播放器、练习/阅读/复习/报告及测试；设计不可变课版本/稳定身份/段落、共享音轨、可变题集、全局概念与课内出现位置、导入CLI、可选教学闭环与真实证据报告。迁移采用停写备份、新目标恢复演练与逐条DDL状态检查，禁止以ROLLBACK掩盖隐式提交。
2. 文件：`docs/phase10/01_CURRENT_ARCHITECTURE_AUDIT.md` 至 `09_PHASE10_IMPLEMENTATION_PLAN.md` 共九份，以及本报告。未修改apps、迁移SQL、content、运行配置、依赖与锁文件；未提交Git。
3. 验证：读取源码、迁移、清单和测试；文档JSON Schema代码块的JSON语法与定义引用、相对文档链接、本轮变更范围、历史迁移hash和Git空白检查，结果以本报告下方最终记录为准。没有运行应用编译/单元/数据库集成/浏览器测试；设计文档改动不构成应用回归通过。09-R的历史PASS与本轮检查分开记录。
4. 风险/下一步：真实库当前全量数据未读取；素材授权仍未满足，实体麦克风/另机/其他浏览器完整闭环未验证。B–F为待批计划，所有新模型/API/导入/性能/教学效果均未实施。人工审核入口：`docs/phase10/09_PHASE10_IMPLEMENTATION_PLAN.md`，重点四项决定见其第5节。

截图：本阶段无UI改动，不生成新截图。09-R历史截图保留原位置，不作为10A新功能证据。

验收：A01文档完整性与范围检查；B01–F06尚未执行。下一阶段输入为10A审核结果、固定基线、迁移前预检与恢复演练条件；本阶段结束后停止。

## 本轮实际验证记录

- `git rev-parse HEAD` / `git status --short`：退出0；开始工作区干净，结束仅九份设计文档与本报告未跟踪，未暂存/提交。
- 通过 `python3 - <<'PY'` 内联只读校验：退出0；10份文档完整、16条本地链接存在、围栏闭合、JSON语法/递归本地$ref/required字段一致、逐行空白检查通过；V001–V008与 `git show HEAD:<path>` 逐字节一致；`git diff --name-only`为空，新增范围恰为这10份Markdown。
- `git diff --check`：退出0；该命令不覆盖未跟踪文件，已由上述逐行检查补充，未把空diff当成新文档验证。
- JSON Schema metaschema校验：NOT RUN，当前Python未安装jsonschema；未为文档设计安装新依赖。语法/引用检查不代表Schema行为、跨引用语义、导入器或数据库约束已验收。
- 应用编译/类型/单元/真实MySQL/Playwright：NOT RUN。本轮只改文档，未启动服务、未连接DB、未读取私人行、未触发播种/迁移/导入。对应新功能必须在获批B–F阶段实际验证。

结论：A01机械文档检查通过；方案仍待人工审核。没有把文档检查标成B–F功能通过。下一步停止于10A审核。

## 10A-R实际修订与验证记录

2026-10-26（Asia/Shanghai）。输入结论CONDITIONAL PASS；修订完成待复审，不代表B–F实现或验收通过。

1. 修改了什么：分别校验音频/规范化转录/对齐关联hash，补正反例；设计保留旧值的原创课/真人录音增量CHECK；统一basic_content与teaching_complete及历史legacy_unassessed；明确10B迁移的隔离双路径/恢复硬门槛；放开canonicalKey自然语言文本；拆10B-1/2/3并准备10B-1候选执行顺序；补可听音频边界测量协议，保留学习证据与能力评估边界。逐项问题/位置/方案/取舍/阶段影响/验收见[评审响应](../phase10/10A_REVIEW_RESPONSE.md)。
2. 涉及文件：原九份文档局部修订，新增10A_REVIEW_RESPONSE.md，更新本报告，共11份Markdown。未改变架构或实施后续阶段。
3. 运行验证：仅以下文档/工作区检查；未编译应用、未跑应用单元/类型/集成/Playwright，未连接数据库、执行SQL/Flyway/备份或启停服务。
4. 风险/下一步：文档修订待人工复审；JSON Schema行为、数据库迁移、导入及真实音频边界均未实施验证。既有素材授权和真设备事项仍保留，未转为PASS。只有复审通过且明确授权后才进入10B-1，数据安全报告后另审10B-2。

### 实际Git范围（含未跟踪文件）

本轮起点与结束HEAD均为 `4497e96fb3685d3e54b3e0995b5868b2db41b3ab`。起点已有九份设计文档及本报告未跟踪；不能把它描述成本轮开始工作区干净。结束时 `git diff --name-only` 与 `git diff --cached --name-only` 均为空，`git ls-files --others --exclude-standard` 恰为以下11个文件：

```text
docs/phase10/01_CURRENT_ARCHITECTURE_AUDIT.md
docs/phase10/02_LEARNING_BLUEPRINT.md
docs/phase10/03_TARGET_DATA_MODEL.md
docs/phase10/04_MIGRATION_PLAN.md
docs/phase10/05_AUDIO_ALIGNMENT_DESIGN.md
docs/phase10/06_CONTENT_IMPORT_PIPELINE.md
docs/phase10/07_API_AND_FRONTEND_IMPACT.md
docs/phase10/08_TEST_AND_ACCEPTANCE_PLAN.md
docs/phase10/09_PHASE10_IMPLEMENTATION_PLAN.md
docs/phase10/10A_REVIEW_RESPONSE.md
docs/progress/PHASE_10A.md
```

这证明当前相对HEAD的交付范围只有文档，apps/业务代码、迁移SQL、content、运行配置、依赖/锁文件均无差异；没有用空git diff遗漏未跟踪文件。对迁移目录V001–V008另外逐文件与 `git show HEAD:<path>` 比较原始字节，8/8一致；V002 SHA-256仍为 `1368dd578ad76f6ad4aca82b67fed40536c7622e2dcad3a32a0ae812d4cf1819`。没有创建V009或新迁移文件。此证据限定于本轮实际核对的Git工作区，不补造原10A会话的运行日志或数据库历史。

本轮编辑前复制原10份文档到 `/tmp/northstar-10ar-before/` 作为局部修订对照；以下为原九份设计相对此快照的逐行变化（不是Git tracked diff）：

| 文档 | 新增行/删除行 |
| --- | --- |
| 01 | +5 / -1 |
| 02 | +12 / -1 |
| 03 | +14 / -6 |
| 04 | +21 / -4 |
| 05 | +11 / -1 |
| 06 | +67 / -13 |
| 07 | +6 / -2 |
| 08 | +11 / -9 |
| 09 | +32 / -18 |

九份设计合计+179/-55，原主体保留；另外新增30行评审响应，本报告追加本轮证据。临时对照是本机复审辅助，不是已提交的历史证据。未暂存、commit或push，交付为工作区文档供审查。

### 命令与结果

cwd为本项目根目录；以下均实际退出0：

- `python3 /tmp/verify_northstar_10ar.py`：11份文档数量、围栏/逐行空白、本地Markdown链接存在性；06的Schema JSON语法、递归本地$ref、required与properties一致性、新枚举/对齐必需字段/基础发布标志/canonicalKey文本约束检查；执行06中的可复算hash样例，并补验Unicode/换行规范化、单句覆盖、过期关联与转录顺序；核对HEAD、跟踪/暂存/未跟踪范围及V001–V008字节一致性。全部通过。这是文档检查脚本，不是导入器或应用测试。
- `git diff --check`：退出0；另由上项覆盖未跟踪Markdown的空白检查。
- `git rev-parse HEAD`、`git status --short --untracked-files=all`、`git diff --name-only`、`git diff --cached --name-only`、`git ls-files --others --exclude-standard`：检查实际范围，无业务改动。
- `shasum -a 256 apps/api/src/main/resources/db/migration/V00*.sql`：8份历史迁移hash已核对，未修改V002。实际枚举来自只读查看V002源文件，不是猜测当前数据库约束已相同。

JSON Schema metaschema/完整实例行为校验：NOT RUN（本机未安装jsonschema，未安装依赖）；字段契约检查不等价于完整Schema验证。hash样例是字节夹具，不是MP3解码/实播或真实对齐审校。DB/Flyway当前状态、备份恢复、V008升级与空库初始化、故障演练、应用编译/类型/单元/真实MySQL/Playwright及可听边界实测：全部NOT RUN，留给明确授权阶段。

验收：A01文档机械检查通过；R1–R4/S1–S5已修订待复审；B01–F06未执行。无UI改动，无新截图；09-R证据仅保留为历史。停止于10A-R复审，不启动10B-1或10B-2。
