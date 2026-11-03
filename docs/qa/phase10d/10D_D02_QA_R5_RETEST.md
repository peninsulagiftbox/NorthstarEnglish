# D02 R5 概念队列分页修复：独立 QA 复测

日期：2026-11-03（Asia/Shanghai）。角色：独立QA。**本次定向复测 PASS，关闭 QA-D02-R5-FINAL-001。阶段整体 CONDITIONAL PASS；未将本轮定向结果扩展为全部10D验收通过。**

## 1. 候选与隔离

CORE交付：`PHASE_10D_2_R5_FIX.md`，HEAD基线a5084cb4442a7b78afad5c920459c22f02f679ce，含未提交/未跟踪修复。219项冻结清单SHA-256 `31a9a13065af5113a56929a2ba1aa5856f32228124b34750079fef7087683eb7`。交付包394文件校验通过。QA另复制709项源码到本worktree `.local/qa-r5-independent/source`，测试前后逐项哈希一致；完整清单见 `evidence/full-source-inputs.json`。没有修改产品源码、迁移、Node/Java测试预期。

- 实际运行JAR：771a72e8ea66304ebfb2e4b5e873d759c60a176fc2dd09fdfe31648da7ff92c6；后端源码未改变，本轮单独编译对照124个应用class/resource条目完全一致，JAR ZIP封装哈希不同不视为业务差异。
- 独立前端BUILD_ID：LSUSSnp7AbOI9MJJIZPpO，Node v22.23.2、项目Java21；不复用CORE前端构建结果。
- 新容器/新卷：northstar-qa-r5-independent-20261103；MySQL8.4.9、127.0.0.1:3381、UUID983c5238-d744-11f1-9a6d-b694e84dafc4，schema northstar_phase01_test。运行账号DML，迁移账号仅本schema测试权限；写入前校验UUID。
- 自建API/Web：127.0.0.1:8196/3203；独立Playwright contexts，1440×900。
- 旧R5失败包 SHA-256 8705e518524c1eac3db6c58bdae2c213ea161a90911cce3f83a7ff244d00e954 再次核验一致；旧故障库/构建未操作。个人3308未连接。

## 2. 真实执行结果

| 检查 | 结果 |
| --- | --- |
| 新库初始化 | PASS；空库正式Flyway迁移到012.11，49项迁移原文与冻结源码一致，所有history成功 |
| Node | test 43/43、typecheck、lint、production build全部exit0；lint保留既有KnowledgeConcepts忙状态未用警告 |
| Java | 核心11/11、0失败/错误/跳过，package exit0；D02/D01知识关联与10C-2测验报告覆盖 |
| Python | 18/18，exit0 |
| 原创fixture | 2个fixture测试通过；100概念经正式登记入口，练习/来源关系完整；登记阶段没有伪造Attempt或卡 |
| 连续数量矩阵 | **从空库0卡连续执行**0/1/20/21/22/100/101，每次增加均来自真实HTTP错误作答；首次到期、全部、刷新、模式切换、重新打开均逐卡对齐API顺序，不漏不重。本轮没有100卡检查点续跑 |
| 分页交互 | 100卡：快速三连点只发1个分页请求；刷新/模式切换后迟到分页丢弃；注入分页503保留20卡并从原游标重试成功；无浏览器pageerror |
| 页外卡与outbox | 从API实际末卡选择第100张（位于首20张之外），展开来源与自评成功；故意丢失提交响应后刷新，原pending事件保留，重试原事件得到回执，卡到期队列变99张 |
| DB幂等/CAS | 上述event仅1条result、rowVersion恰+1；新event携旧rowVersion返回409且result总数不变；该课程真实attempt仍100条 |
| 101卡混合权限 | bank卡83条来源全部在UI/API可达；82条受限白名单、1条可见练习链接，无重复来源；已修卡内来源分页未回退 |
| 到期UI数量 | 到期0/1/20/21/22/100的独立场景全部通过；明确“已加载”口径，无自动无界遍历；读完所有页后数量一致 |
| API分页 | due0/1/20/21/22/100完整遍历，20满页后空尾页终止；all101张分别limit1/20/100全部读取、全局排序、ID唯一；limit101为422 |
| 到期只读性 | 设置due_at只限本轮测试库；各数量浏览器检查前后source/result/receipt逐值不变 |
| 独立SQL终态 | 101卡、183来源、1自评result；队列课100Attempt、bank两课83Attempt；非法/孤儿来源、重复卡、重复result版本、跨概念Occurrence计数均0 |
| 保全 | 709源码哈希、219项CORE冻结输入、旧R5 ZIP均不变；API/Web本轮PID已正常SIGTERM停止，退出143为主动停止，不是测试失败 |

真实命令、起止时间、子进程退出码和日志哈希：`qa/phase10d2-r5-independent/evidence/commands.jsonl`。浏览器总驱动本轮exit0；`container-must-not-exist`退出1是新建前“容器应不存在”的预期探测，不能当作被测用例失败。没有修改业务断言以消除失败，本轮完整矩阵首次连续运行通过。

## 3. 测试方法与可复现性

复用仓库现有原创fixture和matrix/due/API脚本，在QA目录独立执行；适配仅为新容器、端口、私有目录、证据目录和截图路径，跳过已归档旧构建baseline重演（旧FAIL证据原样保留）。QA新增独立终态SQL核对，不仅根据HTTP状态或CORE报告判定。

从本worktree执行：

```sh
python3 qa/phase10d2-r5-independent/run.py create
python3 qa/phase10d2-r5-independent/run.py nodes
python3 qa/phase10d2-r5-independent/run.py regressions
python3 qa/phase10d2-r5-independent/run.py seed
python3 qa/phase10d2-r5-independent/browser_stack.py
```

`create`仅允许全新名字；已保留环境不要重复创建/覆盖，复现时更换独立命名空间。脚本使用本机项目级JDK21、Node22、已安装Playwright和原创音频，位置依赖在脚本中显式保留；证据包可独立解压校验文件完整性，不冒称无需运行依赖的一键异机复跑。

## 4. 结论与限制

R5原P1“API22张/UI20张且无更多入口”在本新候选独立复测关闭。旧R5仍为历史FAIL；本次修复候选定向PASS。未发现本次范围内的来源泄露、跨概念错误关联、CAS丢更新、自评生成客观Attempt或旧故障现场变化。

未在本轮补跑完整B08（新错误×自评并发）/B09（重启逐值）、M03–M08（完整备份恢复及逐DDL故障）、完整Demo/实音频闭环、真实设备麦克风。不得以本轮结果声称10D整体无条件PASS或开始10E；阶段CONDITIONAL PASS待上述门槛独立补齐。

交付：`output/review/northstar-phase10d2-r5-independent-evidence.zip`，附SHA-256；含报告、命令/退出码、实际成功日志、fixture、DB身份与终态、冻结输入清单、截图/trace与独立校验脚本。凭据/私有录音/个人数据不入包。新QA库/卷保留，未提交、合并、推送、部署。
