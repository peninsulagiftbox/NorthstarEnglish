# 实际测试结果

环境：项目级Node22.23.2，既有npm/依赖，Chrome157，Next16.4.2；不更改全局运行时，不安装新业务依赖。

| 命令/流程 | 结果 | 本地证据 |
| --- | --- | --- |
| npm run typecheck | PASS，tsc退出0 | output/ui-review/visual-rhythm/typecheck.log |
| npm run lint | PASS，退出0；0错误、1既有warning | lint.log；KnowledgeConcepts.tsx busy未使用，非本次范围 |
| npm test | PASS，43/43 | tests.log |
| API_PORT=5197 npm run build | PASS，独立build-source源码快照，退出0 | build.log；BUILD_ID mCLsBtsPLlGOc1mzMjcxn |
| 同环境基线production build | PASS，退出0 | baseline-build.log；BUILD_ID jYAAvof0w3-j4Ofy5DwDp |
| python3 scripts/ui/capture-pair.py | 最终Before/After各81组合完成 | production-before.log、production-after.log、production-after-r4.log |
| python3 scripts/ui/validate-layout.py | PASS | layout-validation.json；源码SHA与被测构建一致 |
| scripts/ui/interactions.js 经run-browser.py执行 | PASS，14项核心交互 | interactions-r4.log |
| scripts/ui/states.js 经run-browser.py执行 | PASS，加载、失败、重试与恢复 | states.log、after-concepts-{error,loading}-390.png |
| python3 -m py_compile scripts/ui/*.py | PASS | 本轮执行结果 |
| git diff --check | PASS | 本轮执行结果 |

14项生产交互：弹窗键盘焦点、课程弹窗开关、真实保存偏好、概念筛选刷新、六Tab切换、键盘Tab顺序、10句列表选择/滚动、内容来源弹窗、200%等效CSS视口、真实注册表单、真实Quiz交卷、真实错题生成概念卡、退出、真实登录表单。不是仅测试按钮可点击或状态颜色。

真实数据条件：Demo错题进入句子复习；teaching-a合成教学题集5题真实错误产生beside概念卡5个来源。所有操作使用新建合成账户，仅写入既有G3 v5合成测试库，不触及个人库；未修改API响应或题集来让断言通过。网络失败/延迟测试只abort/暂挂真实请求，恢复后继续真实API。

## 环境与失败记录

- 独立工作树最初不可写，移至可写临时目录实施，最终回到所附UI工作树。原主工作区混合G2/G3改动没有覆盖。
- 新端口直接使用旧API时被Origin规则403拒绝，符合现有安全设计。浏览器转发尝试未用于最终签署，未改安全过滤器/API协议。
- 既有3100/51782测试服务后续核查时已不监听；本轮没有重启原服务。临时独立API5197和Web3197用于最终验证。
- 禁用Flyway的首次临时启动因缺少Bean失败；之后使用冻结JAR和无DDL权限的应用账号、既有准确迁移目录启动。日志明确019.03、No migration necessary，未执行新迁移或修改Schema。凭据只读入进程，不写报告。
- 注册表单标签包含帮助文字、开发模式首次水合、并行浏览器命令互相导航、断言未等待React提交导致过早检查，均为初期测试驱动问题；最终采用串行production流程。
- Demo不生成跨课概念卡，改用真实支持该映射的既有合成教学样例；未改业务。退出回归后旧会话撤销，重新登录保存新会话。
- 旧版没有新版新增的具名region，改用前后都存在的工具栏定位。CLI缓存补丁版本更新导致固定版本发现失败，驱动改为发现现有版本，继续同一Chrome会话。失败日志与最终成功日志分别保留。

最终配对、交互、状态流程有成功结果，初期失败不伪装成产品通过，原始失败日志保留在output/ui-review/visual-rhythm/及私有.local/ui-rhythm/。

## 未执行/不覆盖

没有重新执行Java编译、后端全集、完整教学五层报告语义回归、个人数据备份恢复、100k容量、真实音频听感、Safari或实体麦克风；本次未修改这些业务层。没有声称录音硬件或语言评分通过。

浏览器原生缩放用等效CSS视口验证布局空间；跨操作系统实际缩放仍可手工复核。手工步骤：1280×900将浏览器缩放至200%，检查复习工具栏换行、滚动到底、分页说明；真实麦克风需在测试账户口语Tab授权录制、停止、回放，当前不作硬件验收。

截图、会话与构建默认不提交Git；会话文件含合成账户cookie，仅保存在忽略的.local目录。公开日志输出只保留结果/错误，不包含注入的cookie或执行代码。
