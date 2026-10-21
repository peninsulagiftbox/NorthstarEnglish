# 使用前说明
本文件仅是单阶段指令。先读根目录 `AGENTS.md` 和 `docs/IMPLEMENTATION_PLAN.md`；只执行本阶段，完成后等待审核。详情见 `Northstar_English_Codex_正式开发提示词_V1.md`。

## Prompt 00｜只读审查、架构规划（首先执行）

你是 Northstar English 的技术负责人、全栈工程师和测试负责人。**本轮只分析、只制定计划，不编写正式业务代码。** 如果 Codex 支持 Plan 模式，进入 Plan 模式。

先执行：
- 检查工作目录、已有代码、Git 状态、Node/包管理器、Java/Maven、Docker/MySQL 和端口占用情况；无权限运行的检查如实报告。不要碰全局环境。
- 仔细阅读 `references/phase1/english_lab_desktop_prototype.html`、`references/phase1/Northstar_English_Phase1_桌面Web详细设计与验收.md`、`references/phase1/新概念英语_AI学习网站_竞品与PRD_V1.md` 和预览截图。确认 UI、10 句原创内容、内嵌演示 MP3、六个 Tab、学习数据规则、已知原型缺陷。路径不同则先搜索，不要假定文件缺失。
- 把原型划分为哪些组件可参考、哪些交互可复用、哪些静态/模拟逻辑必须重写；禁止直接套 iframe 或原样粘贴 340KB 单页 JS 到 Next.js。

然后提出：
1. 单仓库结构建议：`apps/web`（Next.js）、`apps/api`（Spring Boot）、`infra`（本地数据库）、`references`、`docs`；若实际仓库已有结构，优先适配。
2. 最小可运行方案和依赖关系。确认采用 Java 21 + 兼容 Spring Boot、Node LTS + 兼容 Next.js；Maven Wrapper/包管理锁文件；MySQL 本地持久化，Redis 暂不需要。
3. 数据模型草图：content_license、book、lesson、sentence、audio_asset、knowledge_point、exercise、attempt、study_session、learning_evidence、review_item、writing_revision、user_setting；逐项注明必需字段、外键、唯一性、索引、状态和不该提前建的对象。
4. API 契约草图及错误协议、eventId 幂等、内容版本、时区处理、导出备份。
5. 音频组件/句子同步模型：当前 10 句各有独立音频；不能假装存在完整课文连续时间轴。逐句和 A-B 区间复读如何实现。
6. UI 页面与跨 Tab 状态保存方案、盲听防剧透方案。
7. 从第一句课文到听写、阅读、录音、写作、测验、复习、报告的纵向切片。
8. 测试矩阵，包括首访、刷新、错误、跳过、断网、媒体权限、重启服务、数据恢复。
9. 九阶段具体文件、可运行交付物、验收标准和风险。

将方案保存为 `docs/IMPLEMENTATION_PLAN.md`（如果 Plan 模式不允许修改文件，则先在对话里完整输出，获批准后再落盘；不得为保存文件擅自切到编码模式），同时提出应写入根目录 `AGENTS.md` 的长期规则。最后列出需要我审核的 3–5 个关键决策。**本轮不创建数据库/业务代码、不安装依赖、不启动开发任务，等待我的明确同意。**

---
