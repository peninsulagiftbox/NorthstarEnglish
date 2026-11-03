# Phase 10D-2 P1 定向修复

日期：2026-11-02。HEAD a5084cb4442a7b78afad5c920459c22f02f679ce。
状态：CORE修复与回归通过；新候选等待独立QA复测，尚未最终签收。

## 改动

仅修改两个业务/测试文件，相对R1的差异见 qa/phase10d2-p1/evidence/fix.diff：

- ConceptReviewController.java：在受限字段裁剪前保存nextCursor，避免页尾Map移除cursorKey后触发NPE；保持受限响应字段白名单。
- 同文件游标入口校验：occurrenceId允许1–36位合法字母/数字/下划线/连字符，不再错误地强制为UUID。新增连续翻页测试在旧实现实测发现422，属完成本次分页修复必需的同路径修正。
- ConceptReviewIntegrationTest.java：混合来源、全撤回来源、单条满页、limit=1/20/默认/精确整页、最后空页、游标严格推进、无重复/遗漏、受限字段白名单、聚合计数及非法游标422。通过真实错误Attempt补足大于20条来源，不伪造来源或放宽约束。

## 实际验证

| 验证 | 原退出码/实际结果 |
| --- | --- |
| 新回归 + 旧实现（首次连续分页） | 1，真实下一页422，red.log |
| 新回归 + 旧实现（单条受限满页） | 1，真实500及ConceptReviewController:130 NPE，red-restricted.log |
| 修复后D02全量 | 0，1/1 PASS，green.log |
| 最终D02+D01+10C-2-R1 | 0，7/7，零失败/错误/跳过，final-regression.log |
| Maven package | 0，package.log |
| 原失败库只读HTTP | 0，83来源在limit=1/20/默认/83/100下完整读取，字段裁剪/visibleSourceCount=1正确，撤回正文和音频拒绝，所有表前后哈希一致 |
| 真实Playwright | PASS；原失败库82条restricted、1条visible，概念卡显示受限占位，未出现撤回课标题；browser-result.txt |
| 前端构建 | 0，BUILD_ID Yba9fWAQ-R7cJftXp7aXb；源文件及配置58项与主候选一致 |
| 新冻结清单 | 336项输入独立校验PASS，含未跟踪文件；V012.01–11哈希与旧候选完全一致 |

Java集成测试库：新建专用MySQL 8.4.9，northstar-d02-p1-20261102-p1，127.0.0.1:3373，UUID fa659971-d67f-11f1-b010-8aeb551daec2，northstar_phase01_test。测试清理只作用于此库。

HTTP/浏览器使用保留的原失败库：northstar-d02-risk-20261102-empty，3364，UUID e6d3595e-d67d-11f1-a92d-8696ac132eb0；API8186/Web3197；账号local。此轮仅只读访问，未重建或清理原现场。自建API/Web进程已停止；个人3308未连接。

## 新候选与可审计交付

旧R1清单与原JAR不覆盖，旧故障包保留。新旧27文件对比仅Controller与集成测试两项发生变化。

- 新完整输入：qa/phase10d2-p1/evidence/candidate-inputs.json，336项；SHA-256 31131ea6b5a92b87ff12d32e61ad6fef9896e2028d16ecba5b7e9368f60b1a6c。
- 新JAR：output/review/northstar-phase10d2-p1-candidate.jar；SHA-256 771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6。
- 新源码与脱敏日志包：output/review/northstar-phase10d2-p1-sanitized-evidence.zip，附.zip.sha256。包含冻结源码输入、红绿测试、原库HTTP对账、浏览器原始输出、迁移哈希、差异和独立校验脚本。
- 解压后执行 python3 verify.py 校验整个包；执行 python3 source/qa/phase10d2-p1/tools/verify_candidate.py --root source 校验源码输入。

未为本次后端修复重复执行Node单测/lint；前端源码无变化，实际前端构建和受影响的真实浏览器流程已验证。未在新JAR上重新运行迁移故障注入或16并发补测；其上轮结果只归属旧JAR，不混称本轮结果。

## QA交接

QA-D02-R4-BUG-001及同路径422已由CORE定向修复。独立QA应以本新JAR/清单重新复测：默认和边界分页、页尾restricted、游标翻页至结束、字段与聚合、音频/正文拒绝、浏览器占位及必要D02回归。

最终独立QA结论仍待复测；CORE通过不替代独立验收。未提交、合并、推送、部署或进入10E。
