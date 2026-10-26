# 架构快照

2026-10-26，来自当前工作区源码，不代表运行态连接已验证。

```text
浏览器：Next App Router / React
  ├─ URL + LessonProvider：课程/版本/句子/Tab
  ├─ AudioController + MediaRecorder：播放与录音
  ├─ IndexedDB：草稿/outbox/上传失败 Blob；旧 localStorage 兼容
  └─ 同源 /api/v1 → Next rewrite → 回环 Spring Boot
       ├─ LocalAccessFilter / 校验 / Problem JSON
       ├─ catalog, study, exercise, practice, report, exportimport
       ├─ JDBC / TransactionTemplate → MySQL + Flyway V001–V008
       ├─ ContentPackage → 冻结 JSON/MP3（含哈希/来源）
       └─ 私人录音 → 项目专用本机目录（与SQL分开）
```

## 组件与边界

| 层 | 版本/职责依据 | 边界 |
|---|---|---|
| Web | `apps/web/package.json`：Next16.4.2、React19.3.1、TS5.9.3、Tailwind4.3.3 | 版本取自配置，不额外声称维护状态或依赖安全审计通过 |
| API | `apps/api/pom.xml`：Java21、Spring Boot4.1.1、JDBC、Flyway、MySQL驱动 | 模块化单体，无微服务/Redis/账号/租户/支付 |
| 持久化 | 8个迁移 SQL，初始化身份表和 Flyway 自有历史表 | SQL 是目标结构，不是已读取的实际数据库 schema |
| 运行 | Node22/npm10，Maven Wrapper，`scripts/local.py` | 只设项目子进程环境，不改全局版本；本次不启动 |
| 内容 | `ContentPackage.java`、`ContentSeeder.java` | ApplicationRunner 会写内容/当前版本；Flyway 启动迁移，不能当纯只读启动 |
| 媒体 | `catalog/CatalogController.java`、`practice/RecordingController.java` | 固定 MP3 校验；私人录音无加密；文件与 DB 不具有统一提交事务 |

## 真实记录模型

正式练习依靠 `command_receipt.event_id` 唯一键与 payload hash；同 ID 不同 payload 拒绝，回执、作答/观察、证据、状态与复习来源在控制器事务中处理。`study_stage` 等是当前状态投影，`learning_evidence` 是历史练习证据；浏览、收藏、上传、跳过不能单独制造 practiced。具体逻辑见 `ExerciseController.java`、`PracticeCommands.java`、`QuizReviewController.java` 和 V004/V006/V007。

草稿与提交分离；听写/写作通过 IndexedDB 缓冲并与服务器 CAS 同步，作文正式版本追加不可变。outbox 能重放未确认 event；浏览器存储故障/Origin 变更仍会影响未同步内容。并非通用离线应用，没有 Service Worker 冷启动离线保证。

课程关联以 lesson/version/sentence/exercise/knowledge point 显式 ID 和复合 FK 为主。旧内容版本保留，不将新版学习完成从旧版直接复制。`stable_key` 在单版本内唯一，但跨版本句子语义映射和内容撤回后的长期可读性没有完整产品契约。

## 安全与真实能力

`application.yml`、Web 启动参数和 Compose 使用回环；`LocalAccessFilter` 检查 Host/Origin/JSON/专用头，无通配 CORS；运行账号与迁移账号分开。该模式没有身份认证，不应视为可公网部署的安全模型。本次网络/监听验证受限，因此只确认源码配置。

AI/ASR/专业评分明确关闭；助教显示本地预置讲解；写作提示和听写匹配是规则，不是模型能力。录音回放≥250ms 是客户端时间观察，不能证明真人完整听过或发音质量。报告显示提交、样本量和人工自评，不等于语言能力测量。

`ReportController` 当前全版本遍历、逐课多次查询、阅读历史无分页；`ExportController.tables()` 全表读入内存。单人单课可用性的历史证据不证明大量教材和多年记录的性能。扩展详见 [专项评估](TEXTBOOK_EXPANSION_ASSESSMENT.md)。
