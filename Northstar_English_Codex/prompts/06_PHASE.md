# 使用前说明
本文件仅是单阶段指令。先读根目录 `AGENTS.md` 和 `docs/IMPLEMENTATION_PLAN.md`；只执行本阶段，完成后等待审核。详情见 `Northstar_English_Codex_正式开发提示词_V1.md`。

## Prompt 06｜口语跟读录音、写作草稿与历史版本

在 Phase 05 验收后执行；此阶段不做模型语音评分。

开发：
1. 实现录音状态机：idle → requesting_permission → recording → processing → ready / failed / denied。使用 `MediaRecorder` 及 getUserMedia，在 localhost 安全上下文工作；选择句子后可先听原音，再录音、停止、回听、重录。录音停止与页面卸载需释放麦克风轨道、对象 URL。
2. 记录必须绑定 lessonId + sentenceId + createdAt + MIME 类型 + 时长。设计本地稳定保存策略（例如私有本地磁盘 API 存储文件并记录数据库元信息；或在用户明确选择后保存到 IndexedDB），必须可查询、删除；不能把录音塞入 localStorage，也不能假装关闭页面后还在。对于不能跨重启恢复的临时录音，明确标注。
3. 权限拒绝、浏览器无支持、设备断开、录制失败时显示原因，可重试/跳过，不阻止其他学习；用户无可回放录音时不能标记口语 `practiced`。
4. 不接 STT 时只能自评与回放，不出现“发音 95 分”；后续 STT 与专业发音评测预留接口但不必实现。
5. 写作 Tab 为原创任务：`Write 2–3 sentences about helping in a garden. Use please, beside, or I can ...`。提供非空草稿自动保存、V1/V2/... 不可变版本、版本列表、内容对比和基础规则提示；规则检查明确非 AI 语法校对。
6. 保存版本应由服务端生成递增版本号、处理并发/重复提交；草稿与已保存版本分离。编辑历史不覆盖，删除操作需二次确认。

验收：许可麦克风时录制/停止/回放，重新打开可按约定访问持久录音；拒绝权限时跳过且不计完成；作文写出两版后刷新能看到 V1/V2 且内容不被覆盖；服务重启数据不丢。浏览器权限相关未自动测试项目必须记录人工实测步骤。写 `PHASE_06.md` 并停止。

---
