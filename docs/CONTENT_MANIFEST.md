# Phase 02 内容包与来源记录

日期：2026-10-21。唯一可用内容为独立原创示例 **Demo 01 / The Neighborhood Garden v1**，使用范围为本地功能测试。`sourceType=original` 记录参考材料的原创声明，**不代表授权凭据已经核实**；文本和音频记录均为 `pending_review`，`releaseReady=false`。未导入四册教材正文、练习或录音。

## 来源与冻结

- 输入：`Northstar_English_Codex/references/phase1/english_lab_desktop_prototype.html`。
- 输入 SHA-256：`0debbd92494b34f9905e38386fe57fc833170c8dfd2ed50e1fa1cc5a4623306f`。
- 参考声明：`references/phase1/Northstar_English_Phase1_桌面Web详细设计与验收.md` 第 4 节称文本及讲解自行编写、音频由本地语音合成软件生成，仅用于验证流程。生成工具、声音、权利人及独立授权证明仍未知，未伪造许可证。
- 归档：逐文件原样复制至 `references/phase1/`，哈希清单为 `archive-manifest.json`；保留根目录不同版本的原型与精听截图，没有覆盖。
- 内容包：`content/demo-01/v1/{lesson.json,manifest.json,audio/01.mp3…10.mp3}`。manifest 包含原型及 lesson 哈希、两条来源记录、四册目录元信息和逐音频哈希/大小/时长。
- 已存在的冻结文件如内容不同，提取器拒绝覆盖。已入库版本的内容或 manifest 哈希变化，种子拒绝启动；已有行不一致也拒绝静默修复。修改内容应创建新版本，不能覆盖 v1。

## 内容和稳定标识

- 课程 `demo-01`，版本 `demo-01-v1`，`bookId=null`，不冒充教材课程。
- 句子 `demo-01-v1-s01…s10`，音频 `demo-01-v1-a01…a10`；序号只用于排序，正式关联使用显式稳定 ID。
- 5 个词语块按词项固定 ID，并关联来源句；15 个练习定义（10 听写、1 阅读、1 写作、3 测验）使用固定 ID、来源句和选项 ID。
- 阅读标准答案为 `Next to the blue bench.`，对应第 6 句。写作任务要求花园场景 2–3 句及 please / beside / I can，来源句为第 5、6、9 句。
- 标准答案保留在服务端内容包和版本 JSON；课程 GET 删除 `answerKey` 及测验答案解释。句子正文和教学讲解本身是本阶段可读学习内容，不宣称已提供盲听保护或作答功能。
- 词汇与练习先存版本 JSON；知识点、练习和作答表随后续阶段建立，没有提前创建学习业务空表。
- 四册只有目录元信息和声明课数 144/96/60/48，均为 `catalog_only`；没有展开 348 条空课程。

## 音频测量和读取

严格 Base64 解码后检查 MP3 头、文件大小，并通过 macOS `afinfo` 读取解码器识别格式及其估计时长，四舍五入为毫秒。未通过文本长度推测时长。浏览器实播结果另见阶段报告。

| 文件 | 对应句 | 字节数 | 解码器时长 / ms |
| --- | --- | --- | --- |
| 01.mp3 | s01 | 25277 | 3579 |
| 02.mp3 | s02 | 25643 | 3631 |
| 03.mp3 | s03 | 19243 | 2717 |
| 04.mp3 | s04 | 25094 | 3553 |
| 05.mp3 | s05 | 20523 | 2900 |
| 06.mp3 | s06 | 22168 | 3135 |
| 07.mp3 | s07 | 15403 | 2168 |
| 08.mp3 | s08 | 24728 | 3500 |
| 09.mp3 | s09 | 17597 | 2482 |
| 10.mp3 | s10 | 20888 | 2952 |

上述v1每句的 `startMs=0`，`endMs=durationMs`，属于独立文件的局部时间轴；v1没有词级对齐或波形。当前播放器的单句时间轴与v2词点见文末增量说明。SHA-256 和精确字节数以 manifest 为准。

本机 Chromium 实播的解码后时长比 afinfo 估计值短 53–77ms，原始实测值逐句保存在浏览器验收日志；两者不能混称为精确相等。后续播放器应使用媒体元素实际 `duration` 限制 seek / AB 范围，不能依赖这些毫秒估计作精确对齐。

媒体接口仅接收资源 ID，通过数据库解析 storage key，并验证规范路径、真实路径 containment、大小和 SHA-256；支持完整读取、字节范围及后缀范围。未知 ID 为规范 404，缺失/损坏为 `503 AUDIO_UNAVAILABLE`；非法/越界 Range 为 416。不存在“播放成功”的伪造业务状态。

## 复现和发布边界

```sh
python3 scripts/extract-demo.py
python3 scripts/validate-content.py
# 后端从 apps/api 工作目录读取 ../../content；也可通过 Spring 属性 northstar.content-root 指定根目录。
# Flyway 完成后由 ContentSeeder 使用迁移数据源在同一事务内幂等导入，应用运行账号仍只有 SELECT。
```

这些命令需要本地保留的冻结原型和 macOS `afinfo`。原型 HTML、图片和提取音频继续被 Git 忽略，授权审核完成前不纳入公开仓库。仅从公开仓库 clone 无法获得完整原型及音频，不能宣称已可独立复现 Phase 02；缺内容包时 API 启动会明确失败，禁止用伪音频补位。

正式发布前需要补齐生成工具、声音来源、适用授权范围和证明，并审查文本及讲解的权利信息。当前没有上传、部署或发布素材，也未自动创建 Git 提交。后续正式授予使用权及版本升级需另行审核。


## 2026-10-22 英式语音 v2

用户对同样10句试听后明确选择英式Edge Sonia/Ryan，技术评测及更换结果见 `docs/TTS_EDGE_EVALUATION.md`。新增 `content/demo-01/v2/`；Mia使用en-GB-SoniaNeural、Leo使用en-GB-RyanNeural，edge-tts7.3.1，速率/音量+0%、音高+0Hz，24kHz/48kbps单声道MP3。正式v2保留原始生成文件，不做试听增益处理。

`active.json`登记v1/v2并默认v2。旧版课包、音频、草稿及真实作答不覆盖、不迁移成新版完成。新旧版本均有10句（数据库共20句）和独立听写目标；文本内容不变、授权范围仍为本地测试。API `GET /lessons/demo-01?versionId=demo-01-v1` 可显式访问旧版，工作台及复习链接携带version。

工具与音色来源现已可追溯，但在线服务/输出的正式发布授权尚未独立核实，音频不提交Git，继续pending_review、releaseReady=false。可复现生成/分析/冻结发布工具分别为 `scripts/evaluate-edge-tts.py`、`scripts/tts-comparison-preview.py`、`scripts/publish-edge-gb-content.py`；独立依赖锁在 `scripts/tts-evaluation-requirements.txt`。


## 播放器单词与句子时间点增量（2026-10-22）

`apps/web/src/lib/media/demo-word-timings.json`是英式v2的补充词边界数据，不修改冻结的v1/v2课包。由`python3 scripts/build-playback-timings.py`从同次合成缓存提取10段、68个WordBoundary；100ns offset/duration换算成ms，记录源记录文件哈希、版本、句子ID和对应音频SHA256/时长。构建前核对原MP3和已发布MP3哈希、原文词序、时间单调性和时长范围，不需要网络或新依赖。

前端仅在版本、音频哈希和时长匹配时使用词点；错误、缺失或v1均不生成等分的假词点。当前播放器只取当前播放句的词点，本句起点为0、红色“终”为本句末尾，不聚合其他句子。时长优先使用该句媒体元素实际duration，尚未加载时显示manifest时长；seek和A–B由媒体元素实际时长限制。词边界来自合成服务，未经人工或ASR逐词校正。

句末标记增量：在当前音频内按原文句号、问号、感叹号定位最后单词，将该词WordBoundary的startMs+durationMs作为10px大点；逗号不视为句末。原5px单词起点与红色音频文件终点保留；原文词序与时间戳不匹配或v1无词数据时不生成句末点。
