# API 与数据库快照（源码级）

2026-10-26。**未读取数据库中的个人记录，也未执行 SHOW/SELECT SQL。** 以下是控制器和迁移定义，不是运行中数据库实测；当前 Flyway 已应用版本、账号授权和数据一致性均 NOT VERIFIED。

## API

实际扫描 41 个 method/path 映射，逐项文件与行号见 `evidence/api-inventory.json`；契约基线 `docs/openapi.yaml`（version0.8.0）。接口前缀 `/api/v1`，不是 `/api/health`。本次未验证 OpenAPI 每个字段与响应完全一致。

| 组 | 接口与方法 | 主要控制器 |
|---|---|---|
| 环境 | GET health、capabilities、settings；PUT settings | HealthController / ReportController |
| 内容 | GET books、lessons、lessons/{id}?versionId=、licenses/{id}、audio/{id} | catalog/CatalogController |
| 浏览 | GET/PUT study/resume；POST study/sessions | study/StudyController |
| 听写/状态 | POST exercises/{id}/attempts、study/events；GET study/stages | exercise/ExerciseController |
| 草稿 | GET/PUT drafts/{sentence} | ExerciseController |
| 阅读/收藏 | GET reading；PUT knowledge/{id}/favorite；POST reading/{id}/attempts、reading/{id}/events | ExerciseController |
| 写作 | GET writing；PUT writing/draft；POST writing/revisions、practice/events | practice/WritingController |
| 录音 | GET/POST recordings；GET recordings/{id}/audio；POST recordings/{id}/playbacks、ratings、delete | practice/RecordingController |
| 测验 | GET quiz；POST quiz/attempts、quiz/events | exercise/QuizReviewController |
| 复习 | GET reviews/items、reviews/due、reviews/{id}/answer；POST reviews/{id}/results | ExerciseController / QuizReviewController |
| 备份 | GET data/export；POST data/import-preview（只读预检） | exportimport/ExportController |

控制器路径根为 `apps/api/src/main/java/local/northstar/`。复合上下文传 lessonId/versionId，句子相关请求再传 sentenceId；正式事件需要 eventId。浏览恢复使用 If-Match；草稿/偏好/复习用各自 rowVersion；不是所有接口统一使用同一乐观锁协议。

返回成功资源或 Problem JSON。来源防护可返回403；未知资源404；方法405；非法请求400/422；event冲突409；恢复点过期412/缺版本428；数据库/音频不可用503。以具体控制器为准，不保证每个接口覆盖全部状态。音频 Range 支持来自 CatalogController，不等同整课时间轴。

## 迁移和表

目录：`apps/api/src/main/resources/db/migration/`。8个版本文件，SHA-256 与建表清单见 `evidence/migration-inventory.json`。加上初始化的 project_identity 和 Flyway 自建表，源码目标合计37表；**不是本次实测数据库表数**。

| 版本 | 表/主要变化 |
|---|---|
| 初始化 | `infra/mysql-init.sh` 建本项目主库/测试库、身份表、独立账号；并非 Flyway V000 |
| V001 | user_setting，个人本地设置与环境身份关联 |
| V002 | content_license、book、lesson、lesson_version、audio_asset、sentence；current_version FK与不可变内容基线 |
| V003 | study_resume，单一本地恢复点与 row_version |
| V004 | exercise、command_receipt、exercise_attempt、learning_evidence、study_event、study_stage、exercise_draft、review_item、review_source；恢复点播放句/位置 |
| V005 | knowledge_point、vocabulary_favorite、reading_question、reading_option、reading_answer、reading_progress；exercise 类型扩展 |
| V006 | writing_task、writing_source、writing_draft、writing_revision、personal_recording、practice_progress、recording_observation；证据扩展 |
| V007 | quiz_question、quiz_run、quiz_answer、quiz_progress、review_result；复习调度字段/唯一键/来源迁移 |
| V008 | user_setting.recording_enabled |

## 完整性与限制

- lesson_version 对 lesson/version_no 唯一；sentence 带 lesson_id/lesson_version_id/stable_key，复合 FK 避免跨版本串用；知识点、题目、作答、复习来源进一步绑定上下文。
- command_receipt 和正式记录 event 唯一，防重放多计数；写作版本有编号/源句/回载关系；草稿不等同正式作答。
- 状态 CHECK 包括 not_started/in_progress/practiced/skipped/paused；后端阻止通过普通状态事件直接 practiced，必须从正式证据路径产生。
- V002 的 book.availability 只接受 catalog_only；sentence.start_ms CHECK =0，audio_asset_id 全表唯一。现结构不能直接承载多句共享整课音频。
- V007 测验正确数 CHECK 0..3，控制器要求恰好3题，报告以 runs×3 算分母。题量可变不是配置问题。
- Flyway MySQL DDL 不能视作可回滚事务；V002 对部分 DDL 作幂等防护不等于所有迁移可安全重复。V008 历史发生人工登记协调，须复核见 KNOWN_ISSUES。
- `data-transfer.py` 用新恢复 schema 和媒体目录；数据 DML 可事务入库，但建库/DDL/授权/媒体不是整体原子操作。导入预检限同结构/同冻结内容，不是教材批量导入或跨版本数据升级器。

不随包提供当前学习库 dump、行内容、私人音频、`.env` 或数据库权限秘密。模板仅有 `.env.example` 的显式占位符。
