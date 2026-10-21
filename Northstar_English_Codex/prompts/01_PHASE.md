# 使用前说明
本文件仅是单阶段指令。先读根目录 `AGENTS.md` 和 `docs/IMPLEMENTATION_PLAN.md`；只执行本阶段，完成后等待审核。详情见 `Northstar_English_Codex_正式开发提示词_V1.md`。

## Prompt 01｜工程骨架、数据库与本地启动

我已批准 `docs/IMPLEMENTATION_PLAN.md`，现在只执行 Phase 01。先检查 Git 状态，重读 AGENTS.md 和阶段计划，禁止提前实现课程训练功能。

开发：
1. 按批准的布局创建前后端最小可运行工程；Node 受维护 LTS、Next.js App Router、严格 TypeScript、Tailwind、ESLint；Java 21、Spring Boot、Maven Wrapper、Bean Validation、MySQL Driver、Flyway。选用实际兼容版本并固定依赖。
2. Docker Compose 只启动**本项目专属** MySQL 8，卷和容器名称区分已有项目，端口使用环境变量，默认只绑定回环地址；如果 3307 被占用，不能抢占/停掉其他服务，改 `.env` 并写清楚。
3. 建立后端统一响应/错误结构、健康检查 `/api/health`、环境变量校验和配置说明；只允许本地开发访问，无需登录系统。
4. 通过 Flyway 建立必需的第一版关系表、外键、事件唯一键、合理索引和时间字段（UTC 存储，本地展示），避免在代码中自动 `ddl-auto=update` 造成隐式更改。注意学习尝试、跳过事件、草稿、作文历史不能合成一张布尔状态表。
5. 前端建立布局骨架和错误/加载空状态，API 客户端带请求超时/错误处理。生成 `.env.example`、`.gitignore`、`README.md`、本地初始化/启动脚本。
6. 后端提供简单数据库连通性集成测试；前端能展示从真实 API 获取的健康状态，而非硬编码“服务已连接”。

验收：新的 Mac 环境按 README 启动可看到前后端页面；MySQL 数据重启后仍在；Flyway 可重复启动且不会清空表；健康检查真实访问成功；已有 MySQL/容器不受影响；前后端 build/测试实际执行并记录。

将报告写入 `docs/progress/PHASE_01.md`。列出完成与未完成，停止并等待审核。

---
