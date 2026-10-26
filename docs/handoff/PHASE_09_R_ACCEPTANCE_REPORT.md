# Phase 09-R 验收闭环报告

日期：2026-10-26（Asia/Shanghai）。用户已批准本轮打包、候选commit/tag、隔离回归和真实库元数据只读查询。未推送Git，未导入四册教材，未修改Java业务源码/迁移SQL/学习产品逻辑。

唯一源码候选：`phase-09r-rc1`，Git SHA **dd9e3f47a1a5c12296532846f676bb1fcbec7569**。后续交付证据提交不是新的已测试产品候选。

## 结果

- 本地已测核心工程与Java源码交接：PASS。
- 实体Chrome/Safari麦克风、Safari/Firefox闭环、另一台全新机器：NOT VERIFIED。
- 素材公开分发授权门禁：FAIL，pending_review/releaseReady=false。
- 全平台正式发布验收：NOT VERIFIED。包装生成或校验成功不替代以上结论。

完整逐项状态见[验收矩阵](ACCEPTANCE_MATRIX.md)。仓库原路径为docs/ACCEPTANCE_MATRIX.md；包内附同内容的相对链接副本。

## 固定源码与差异

[差异审查](PHASE_09_R_CHANGE_REVIEW.md)逐项列出原Phase09未提交改动与09-R修复；[candidate.json](evidence/phase09r/candidate.json)记录候选文件哈希、依赖锁/POM/Wrapper、全部迁移SQL、内容清单和测试脚本。

原19个Java主源码与13个测试文件相对Phase08没有变化。遗漏由打包白名单造成，已补.java，并增加集合/数量/哈希守卫，防止“被选中的文件都正确”掩盖整类源码缺失。额外的MigrationProbe.java仅供验收只读查询，不是业务修改。

候选后仅新增报告/原始证据和补充验证命令。补充测试脚本及失败v1/修正v2的哈希另见[supplemental-scripts.json](evidence/phase09r/supplemental-scripts.json)；v2仅更正错误提示定位器。候选apps/scripts/infra/content及锁文件完整性检查退出0，无源码漂移。

## 实际环境与原始证据

[环境](evidence/phase09r/environment.json)、[每条实际命令/argv/cwd/原始退出码](evidence/phase09r/commands.jsonl)、[可读索引](evidence/phase09r/COMMANDS.md)。日志只作配置秘密精确替换、机器路径与本地身份脱敏，没有从passed:true倒推退出码。

- Node22.23.2/npm10.9.8、Java21.0.12.1，沿用既有项目级运行时；未改变全局版本。
- MySQL8.4.9固定镜像digest；新source/restore容器与专属卷，回环3311/3312。
- 测试Web/API分别3101/8086、3102/8087；独立构建副本与媒体目录在.local/phase09r-rc1，无主站构建覆盖。
- Chrome155.0.8059.85、固定Playwright CLI0.1.22；隔离浏览器/虚拟麦克风，真实本地冻结课程音频。
- Node25项、Python15项、Java/MySQL20项均退出0；Java无失败、错误或跳过。类型/Lint/Web生产构建/API编译退出0。
- 真实报告与SQL对应：源库听写1、阅读1、作文2版本、测验1轮/1题正确、ready录音1、自评1；恢复续学后听写2，其他项相同。曝光答案样本不冒充独立能力成绩。
- SQL逻辑恢复到northstar_restore_20261026194500：37张表逐列逐值相同，1份ready录音大小/SHA相同。随后原音频实播、UI提交一次、同event幂等、DB503/重启、API重启及新浏览器回访后再次37表/媒体一致。
- 只停止本轮测试服务，容器、库、卷、媒体与备份均保留；不停止主站或其他项目。

## 真实学习库边界

真实库只以app账号读取V008历史与user_setting列元数据、运行Flyway validate。实际V008 checksum=-1543956184、success=1，recording_enabled为tinyint(1) NOT NULL DEFAULT1，校验9条记录（baseline+001–008）。未调用migrate/repair/baseline或手工补历史。历史Phase08人工协调事件仍保留；今天的校验不证明当时全过程自动迁移无异常。

本轮未打开主站浏览器、读取学习表、导出私人快照或执行主库写命令。没有进行全库前后逐值比较，所以“真实库全量一致”仍NOT VERIFIED。恢复只用本轮合成测试学习数据和虚拟设备录音。

## 失败保留与关闭依据

| 记录 | 原始结果 | 当前处置 |
|---|---|---|
| prefreeze-python | FAIL，exit1，13通过/2沙箱权限Error | 已复验：候选下本机权限15项PASS，原日志保留 |
| prefreeze-packaging-failure.txt | FAIL，exit1，缓存被打包排除守卫拒绝 | 已修复枚举排除与预扫描，后续包装PASS；不是业务修复 |
| packaging-privacy-rejection.txt | FAIL，exit1，Spring启动元数据含本地身份 | 原成功日志另存私有目录，公开副本精确脱敏；后续包装PASS；退出码/断言不改 |
| browser-fresh | FAIL，exit1，Playwright自带Chromium未安装 | 同候选改用已安装Chrome，browser-fresh-chrome PASS；未安装新浏览器 |
| playback-product-rejection与外层v1 | FAIL，exit1，精确文本定位超时 | trace显示产品已有错误提示；v2改定位容器，产品拒绝/无作答/实际重试PASS；v1不删除 |
| 初始git diff --cached --check | FAIL，exit2，3份历史失败日志末尾空行 | 不改历史证据。仅关闭blank-at-eof规则检查其余空白，退出0；当前增量diff另行检查 |
| 收尾git-evidence-whitespace | FAIL，exit2，原始日志含尾空格/CRLF | 不改日志；非日志差异单独检查PASS，证据Git属性-text与索引逐字节核对PASS |
| 历史全闭环/音源/安全/重复up/HTTP422 | 历史FAIL/退出码UNKNOWN均保留 | 本次固定候选独立重跑相关要求PASS；历史422及主站恢复点事故不改成历史PASS |

历史事故原文在PHASE_09.md、KNOWN_ISSUES与historical目录。旧日志缺退出码仍为null/UNKNOWN，不纳入本次PASS。

## 剩余问题与发布建议

| 优先级 | 状态 | 问题/处置 |
|---|---|---|
| P0 | PASS | Java源码遗漏、候选未冻结、统一命令退出码缺口本轮已关闭 |
| P0 | FAIL | 内容/声音授权凭据不足，公开分发素材门禁仍未满足 |
| P1 | NOT VERIFIED | 实体Chrome/Safari麦克风、其他浏览器完整闭环、另一台全新机器 |
| P1 | CONDITIONAL PASS | 源码ZIP无待审MP3，完整复现需要合法原哈希素材；不能以重生成音频替代 |
| P2 | CONDITIONAL PASS | UI仅1440/375与标签/对比度抽样，非全面WCAG/像素还原 |
| P2 | CONDITIONAL PASS | 历史Flyway人工协调和主站只读测试事故已记录；本轮不伪造其历史成功或全库未变证据 |

允许据本次证据审核个人本地有限交付；不建议公开素材或宣称全平台发布验收通过。不开始四册教材导入、AI/ASR或新业务阶段。

实体设备手工步骤：分别记录Chrome/Safari与系统版本，允许麦克风→录制→停止→实际回放→刷新再播→人工自评；再拒绝权限→确认提示→跳过→继续写作/测验。另机用合法素材和新配置从零安装、初始化、SQL+媒体恢复与真实续学，记录原始退出码。上述尚未执行。
