> 当前 Phase 09-R（2026-10-26）已完成固定候选隔离复验，见 [09-R 报告](PHASE_09_R_ACCEPTANCE_REPORT.md) 与 [矩阵](ACCEPTANCE_MATRIX.md)。下文为此前交接审计原文，保留当时结论与证据边界，不能替代本次结果。

# Phase 09 独立验收报告

日期：2026-10-26。结论：**NOT VERIFIED；不签整体 PASS，不批准素材发布**。

历史 `docs/progress/PHASE_09.md`（2026-10-25）声明 BLOCKED。当前 `docs/evidence/phase-09/logs/` 有 2026-10-26 的更新成功和失败记录：后端 20 项、完整学习脚本和边界脚本曾成功，随后并行执行又产生安全/重复启动/恢复/重访/新实例初始化成功日志（详见TEST_EVIDENCE）。本次未重跑，原始退出码未知，且脚本发生漂移；不能合成一次同版本完整验收。旧报告未随之更新，本审计保留差异，不改原文。

## 核心端到端核查

| 项目 | 实现与支持证据 | 本次状态 | 仍缺什么 |
|---|---|---|---|
| 课程读取/关联 | CatalogController、V002 复合 FK；内容 v1/v2 校验退出 0；历史闭环成功 | CONDITIONAL PASS（静态/本地包） | 当前 HTTP 查询被权限阻塞，端到端 NOT VERIFIED |
| 逐句播放/同步 | AudioController、timeline；本次单测；历史脚本第 6 句 actual currentTime>0.1 | CONDITIONAL PASS | 本次真实解码/切句/后台节流 NOT VERIFIED，听感未测 |
| 听写及学习记录 | ExerciseController.command 事务/回执、TokenAligner；历史同 event 重放与对照 | NOT VERIFIED（本次 E2E） | 不追加数据，未验证新提交/重试入库 |
| 跳过和完成分离 | V004/V005/V006/V007 独立状态和 evidence；事件仅 start/skip/pause | CONDITIONAL PASS（代码） | 当前记录前后计数/回执 NOT VERIFIED；历史口语跳过成功 |
| 草稿持久化 | IndexedDB/outbox、后端 CAS；历史刷新/离线边界通过 | NOT VERIFIED（本次 E2E） | 本次不触发恢复点/草稿写入；阅读未提交选项仅页面保存 |
| 词汇/阅读/复习 | VocabularyPanel、ReadingQuestion、ReviewQueue；历史错误→源句→复习通过 | NOT VERIFIED（本次 E2E） | 收藏及调度写入不重跑 |
| 真实报告 | ReportController 直接汇总证据，固定 3 题分母，阅读历史可追溯 | CONDITIONAL PASS（实现） | 本次未访问私人报告/逐记录对账 |
| AI 导师 | HealthController 明确 aiEnabled=false；LessonWorkspace 明示本地预置讲解 | PASS（真实实现边界的静态核对） | 未实现 AI 供应商/模型调用；不是 AI 功能验收通过 |
| 录音 | MediaRecorder、上传/回放/自评/墓碑；本次 recorder 单测；历史虚拟设备日志 | CONDITIONAL PASS | 真实设备允许/拒绝、Safari 回放与重启文件一致 NOT VERIFIED；无 ASR/专业评分 |
| 应用重启数据一致 | 既有 main-snapshot 记录37表相同/media=0；restore-values/restored-after-continue-restart声明37表与1份媒体一致 | NOT VERIFIED | 本次未重启，也未比较实时全库/私人媒体；media=0不能证明媒体恢复 |
| 部署可重复性 | 锁文件、Wrapper、固定 MySQL 镜像、现有安全脚本 | NOT VERIFIED | 已有同机新实例/重复启动成功日志；另一台新机与本次独立复验缺失；源码包缺授权音频 |
| SQL+媒体恢复后续学 | data-transfer.py 与恢复 runtime 存在 | NOT VERIFIED | 不新建库/导入；已有restore-values/续学/重启/重访成功日志；不是本次独立逐值核验，recovery-restart-continue还保留HTTP422失败 |
| 本地安全门禁 | LocalAccessFilter、回环绑定、secret 扫描脚本 | NOT VERIFIED | 历史初次Build assets missing，后续security-runtime-final/security-delivery日志passed:true；本次网络/监听独立复验仍未完成 |
| 1440×900及375布局 | 历史两份脚本含桌面几何和窄屏检查，前端构建成功 | CONDITIONAL PASS | 本次截图/视觉和真实浏览器回归未重跑，未逐图复核旧截图 |

历史浏览器最终日志为 `evidence/historical/full-learning-loop-20261026143113.txt` 与 `release-boundaries-20261026143219.txt`；各自包含 `passed:true` 和测试代码。它们的原始执行退出码未知，不填写 0。前序失败已一并保留。完整命令、退出码表见 TEST_EVIDENCE。

## 关闭验收缺口的顺序（本次不执行）

1. 审查未提交 Phase 09 diff、运行脚本与恢复权限；解决计划/报告/日志状态不一致。
2. 在明确允许数据库测试写入的独立环境验证启动、完整 E2E、幂等、跳过计数、报告对账，禁止使用已有个人学习库。原命令见 `evidence/not-executed.json`，不是本次通过证据。
3. 新目标执行 SQL+媒体恢复、逐值/哈希验证、续学、重启对比；记录源/目标范围和失败处理，避免将 DDL 当可回滚事务。
4. 完成本地安全脚本最终通过、新机从锁文件安装与 Chrome/Safari 物理麦克风手测。
5. 明确教材与声音分发权利。未获授权不得通过公开/商业素材发布门禁。

人工麦克风步骤：授权环境选择固定课程/版本/句子→允许权限录制→停止→真实回放满 250ms→确认客户端观察和自评各自计数→刷新/重启读取同一文件→另建浏览器上下文拒绝权限，确认不产生完成/证据。保留截图与操作时间，不把虚拟设备日志代替实体结果。此步骤本次 **NOT VERIFIED**。
