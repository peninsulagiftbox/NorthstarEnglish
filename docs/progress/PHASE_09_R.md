# Phase 09-R｜验收闭环修复

2026-10-26（Asia/Shanghai）。已按用户“批准”完成本阶段，停止后续开发，等待审核；无推送。

唯一验收候选：phase-09r-rc1 / dd9e3f47a1a5c12296532846f676bb1fcbec7569。

1. 修改：修复.java白名单、Java集合/哈希与ZIP精确条目校验；补独立测试容器/构建/媒体/进程守卫和命令退出码证据；更新矩阵与发布建议。保留历史失败及旧包哈希；不改业务逻辑，不导入教材。
2. 文件：[逐项变更审查](../handoff/PHASE_09_R_CHANGE_REVIEW.md)，主要为docs/handoff/evidence/{freeze_sources,package_handoff,verify_packages}.py、scripts/phase09r.py、MigrationProbe.java、测试及回归入口/备份脚本、验收文档。原Phase09 CSS改动随候选保留，本轮不继续改样式。
3. 验证：[矩阵](../ACCEPTANCE_MATRIX.md)、[完整报告](../handoff/PHASE_09_R_ACCEPTANCE_REPORT.md)、[命令与退出码](../handoff/evidence/phase09r/commands.jsonl)。Node25/Python15/Java与MySQL20项PASS，类型/Lint/生产构建/后端编译PASS；Chrome学习闭环/故障/幂等/草稿/报告/安全PASS；37表+1份录音恢复、真实续学、503/重启、重复初始化PASS。真实库仅V008/列元数据与只读Flyway validate，PASS。报告生成不作为业务验收。
4. 风险：素材授权FAIL；实体麦克风、Safari/Firefox闭环、另机NOT VERIFIED；源包无待审MP3，完整音频复现CONDITIONAL PASS。完整真实学习库前后逐值一致NOT VERIFIED。未满足全平台发布验收。

截图：docs/evidence/phase-09r/screenshots/，交接包仅附选定的合成测试截图；原始trace为.playwright-cli/traces/，索引与哈希见交接证据。未包含私人录音或学习库快照。

测试环境：两台新专属MySQL回环3311/3312，API/Web8086/3101与8087/3102，独立.local/phase09r-rc1。结束只停止本轮服务，保留库卷媒体；主站不停止、不重建。

失败与关闭依据见完整报告：沙箱Python、缺Chromium、补充定位器超时、打包缓存拒绝均保留原始记录；历史HTTP422和主站恢复点事件不抹除。下一步依赖用户审核、合法素材凭据和真机/另机条件；不自动进入新业务阶段。
