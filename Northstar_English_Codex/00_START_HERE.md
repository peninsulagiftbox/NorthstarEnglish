# Northstar English｜Codex 开发启动包

这个开发启动包包含原创 HTML 原型、详细 PRD 与设计验收说明、页面预览、总控规则、十份按顺序执行的 Codex 提示词。

## 目录

- `references/phase1/`：上一轮已验收通过的 HTML 原型、原创音频、MD 规格与预览截图。**原型是输入参考，不是生产代码。**
- `prompts/00_PLAN.md`：先让 Codex 审查并输出规划，不写代码。
- `prompts/01_PHASE.md` 到 `prompts/09_PHASE.md`：九个正式开发阶段；每次只粘贴其中一个阶段。
- `Northstar_English_Codex_正式开发提示词_V1.md`：一份完整合集。
- `AGENTS.template.md`：建议的项目级 Codex 工作规则。

## 新项目使用方法

1. 在 Mac 上建立 Git 项目目录，例如 `~/Projects/Northstar-English`。如果已有同名/已有代码，不要盲目覆盖；先将本包解压到临时目录，选择性复制。
2. 将解压得到的 `references/`、`prompts/` 和本文档复制到项目根目录。若仓库没有 `AGENTS.md`，审查后将 `AGENTS.template.md` 复制/改名为 `AGENTS.md`；已有规则则合并，避免覆盖。
3. 在该目录打开终端，执行 `git status` 并确认你了解现状，再启动你已安装的 `codex`。
4. 将 `prompts/00_PLAN.md` 的**全文**复制到 Codex，先审查方案。该轮不应执行任何安装、数据库创建或业务代码修改。
5. 只有你明确批准规划之后，才发送 `prompts/01_PHASE.md`，以后根据测试报告依次发送 02–09。
6. 每轮查看 `docs/progress/PHASE_XX.md` 与实际测试日志，审核通过后再开始下一阶段。若计划与现实冲突，要求 Codex更新计划并说明取舍，不要默默更改范围。

## 核心验收点

`原创 10 句内容真实入库 → 可准确播放 → 听写错句溯源 → 阅读题证据句 → 录音回放 → 作文版本 → 测验错题 → 到期复习 → 首页与报告持久恢复`。

## 版权与测试说明

只允许使用原创 Demo 01 *The Neighborhood Garden* 的文本和内嵌合法演示合成 MP3。四册《新概念英语》暂时只做课程结构，明确 `catalog_only`，未来取得相应授权后再导入正式教材内容。静态原型里曾使用内存录音和 localStorage，正式版需要能可靠存储学习记录，不得宣称演示功能已经完成真实后端开发。
