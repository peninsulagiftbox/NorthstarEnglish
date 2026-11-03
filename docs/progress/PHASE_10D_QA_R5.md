# Phase 10D QA R5 再次封版验收

测试2026-11-02，归档2026-11-03（Asia/Shanghai）。结论：**FAIL，新P1 QA-D02-R5-FINAL-001。按既定停止门禁结束。**

改动：新增 `qa/phase10d-final-r5/` 独立QA运行器、原创21概念内容fixture、浏览器检查/只读复核和证据封装；新增 `docs/qa/phase10d/10D_D02_QA_R5_FINAL.md`；更新最终验收入口。没有改产品源码、迁移或既有测试断言。

候选：main/a5084cb，初始389项输入SHA `ac1e29849324b27325962fdd067b41935e3479afafa68753fd71a9f500d42f12`；最终392项SHA `708edab2f1364127ef65949f805378cab535245a4e9be7ac29c55c8212c5a9ad`（仅追加只读复核/收尾工具，原389项当前与实际测试副本字节一致）。Web BUILD_ID `fxpqzia8rPru49bVZ_KIY`，运行JAR `771a72e8…`；本轮重建JAR124应用条目0差异。

环境：新容器 `northstar-qa-final-r5-20261102`、MySQL3382、UUID `3c213ff3-d6d4-11f1-9124-068c3e69d404`；API8192/Web3199；媒体 `.local/qa-final-r5/`。未连接个人3308、未重启3100/8085，旧失败现场不清理。

实际验证：

- `python3 qa/phase10d-final-r5/run.py freeze/create/nodes/tests`：分别执行；Node36测试及typecheck/lint/build全部exit0；Java核心11测试exit0，package和原创fixture登记exit0。
- `python3 qa/phase10d-final-r5/browser_stack.py`：83来源独立复测PASS（82受限/1可见、5页、无重复、白名单正确）；队列检查exit1。首轮全页选择器包含24张旧句子卡，原始日志保留。
- `python3 qa/phase10d-final-r5/queue_recheck.py`：仅限定概念卡section后，首次/刷新/重开/到期4种场景均API22/DOM20，缺apple与pear，无翻页入口，exit1；9业务表前后逐值一致。
- `python3 qa/phase10d-final-r5/closeout.py preserve/package`：分别保全与打包。日志、退出码、候选/日志哈希在evidence/commands.jsonl。沙箱首次create失败保留于launch-failures.json，经批准隔离执行成功。

新缺陷根因：`ConceptReviewQueue.tsx:13–15` 忽略队列nextCursor，队列只能访问第一页；与已修复 `ConceptReviewCard.tsx` 卡内来源分页不同。本轮关闭旧来源分页缺陷，新增队列P1阻断；未修改业务。

未执行：B08完整A–H、B09全字段重启/重放/CAS、M03–M08恢复故障与续学、浏览器自评/双Tab/断网/丢响应/空队列/API错误、完整Demo和音频闭环。不把已有集成局部覆盖扩称完整门槛通过。

截图/轨迹：`output/playwright/phase10d-final-r5/`。22张卡/104条来源失败库和私有dump保留；本轮API/Web停止、8192/3199无监听。R4旧证据包已按相同SHA归档，当前封版证据更新到 `output/review/northstar-phase10d-final-qa-sanitized-evidence.zip`。

下一步依赖：CORE消费概念卡队列游标、验证页外卡可访问，冻结新候选后由QA重跑受影响测试并补齐并发/恢复门槛。未提交/合并/推送/部署，不进入10E。

交付校验：证据包独立解压后执行verify.py，exit0；最终392项输入仍与冻结字节一致，R4归档包SHA与原包一致；git diff --check exit0。最终包哈希见同名.zip.sha256。
