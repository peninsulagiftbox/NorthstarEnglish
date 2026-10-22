# Edge TTS 对比评测与英式语音更换报告

日期：2026-10-22（Asia/Shanghai）。范围为现有原创 Demo 01 的10句；不扩展教材、不接入实时AI/ASR、不进入Phase05。

## 结论与采用依据

采用 **英式 Edge：Mia → Sonia（en-GB-SoniaNeural），Leo → Ryan（en-GB-RyanNeural）**，发布为不可变 `demo-01-v2`。原v1文件、音频元数据和已有学习记录保留；默认入口使用v2，旧版与复习来源通过显式version访问。

决定由两类证据共同支持：本轮生成、解码与播放测试；以及用户在本地对比试听后明确选择“英式 Edge（Sonia/Ryan）更好”。这是一位用户的主观偏好确认，未收集逐句评分，不是多人盲测、MOS或专业发音评测。**不能宣称Edge在所有指标或所有场景都更好**：其句首静音更长，发音准确性也没有独立ASR/专家逐词结论。

## 测试设计

- 完全相同的10句原文，保持大小写、标点和Mia/Leo角色。对照为现有10段MP3，原生成引擎/音色仍unknown。
- 英式为Sonia/Ryan；美式为Aria/Guy。服务返回声音列表实际确认四者可用。参数均 `rate=+0% / volume=+0% / pitch=+0Hz`，输出24kHz、48kbps、单声道MP3。
- 每组10次完整生成；第6句每组再生成3次。因此共26次请求；没有使用缓存冒充新生成。本轮26/26成功。
- 采用项目内独立Python3.14环境和edge-tts7.3.1，完整依赖锁定在`scripts/tts-evaluation-requirements.txt`；不修改全局环境、Java/NPM应用依赖。
- 使用macOS afinfo获取MP3元数据，afconvert真实解码PCM。10ms RMS帧超过−45dBFS作为能量阈值，统计静音和响度；这是能量分析，不是语音活动的语言学真值。
- 等响度试听副本仅施加恒定增益：目标活跃帧RMS−22dBFS、峰值上限−1dBFS。不降噪、不变速、不删停顿。采用的正式v2仍为原始Edge MP3，不是试听WAV。
- 本地A/B/C来源可隐藏/揭示，角色音色对应固定；这不是预注册的独立双盲实验。页面不产生学习证据，不上传试听判断。

## 自动测量结果

| 指标 | 现有 | Edge英式 | Edge美式 |
| --- | ---: | ---: | ---: |
| 真实PCM解码通过 | 10/10 | 10/10 | 10/10 |
| 10文件总大小/字节 | 216,564 | 186,624 | 203,328 |
| 相对现有大小 | 基准 | 减少13.8% | 减少6.1% |
| 总时长/秒 | 30.616 | 31.104 | 33.888 |
| 采样率/Hz | 22050 | 24000 | 24000 |
| 码率/kbps | 约56 | 48 | 48 |
| 接近满幅样本数（绝对PCM≥32760） | 0 | 0 | 0 |
| 平均活跃帧RMS/dBFS | -20.69 | -17.767 | -19.002 |
| 平均句首能量阈值静音/ms | 34 | 200 | 185 |
| 平均句尾能量阈值静音/ms | 526.7 | 655.4 | 899.8 |
| 在线生成成功/请求数 | 本轮未重新生成 | 13/13 | 13/13 |
| 本轮生成耗时中位数/秒 | 不适用 | 1.577 | 1.457 |

采样率提高、文件变小或没有接近满幅样本，都不能独立证明自然度、词尾完整或发音正确。英式原始平均响度比现有约高2.9dB，直接比较容易产生音量偏好，因此提供等响度版本。句首/句尾指标依赖阈值，包含编码延迟和低能量语音，不能当作精确声学切分。

第6句原句：`Please put them beside the blue bench.`

| 第6句 | 时长/秒 | 原始MP3/字节 | 独立生成4次的不同哈希数 |
| --- | ---: | ---: | ---: |
| 现有 | 3.1347 | 22,168 | 未重新生成 |
| 英式Ryan | 2.904 | 17,424 | 1 |
| 美式Guy | 2.760 | 16,560 | 1 |

哈希一致表明本轮该句输出可重复，不保证其他句子、未来版本或长期服务都确定性一致。生成耗时包含当前网络环境，样本量小，不代表SLA。已有MP3供本地播放不需要再次访问微软。

## 音质与教学判断的证据边界

| 项目 | 结论 |
| --- | --- |
| 自然度/听感偏好 | 用户明确选择英式更好；没有虚构模型分数 |
| 逐词发音、重音、语调、漏词 | 没有独立ASR或专家逐词评分；建议人工重点听community garden、Mia/Leo、beside/bench、soil/still wet |
| 内容完整性 | 合成输入与原文逐字相同、音频非空且可完整解码；服务端boundary文本只是服务元信息，不能当作独立识别结果 |
| 解码/播放/文件完整性 | 30个对照素材均解码；浏览器真实播放结果及v2应用复验见下节 |
| Safari/Firefox及真实后台音频输出 | 本轮未测；Chromium状态不能替代所有设备听感 |

## 已实施的版本化更换

1. `content/demo-01/v2/`生成新的课包、来源清单和10段英式音频；`content/demo-01/active.json`显式列出v1/v2并选v2。未覆盖v1，也未把旧作答迁成v2已练习。
2. `ContentPackage/ContentSeeder`同时校验两版；只有新版本新增行，同一事务发布音频、句子、听写exercise与默认版本。旧版本内容哈希不一致即拒绝启动，不静默修复。没有增加Flyway schema或删除数据。
3. 课程API支持可选`versionId`；URL与复习链接携带`version`。课文“内容来源”提供v1/v2入口；新课头说明英式配音，来源中记录实际引擎、角色音色与参数。旧版草稿和复习目标保持旧版上下文。
4. 未将edge-tts变成学习运行时依赖；播放仍从本地Java API读取预生成MP3。浏览器没有API Key或微软直连调用；新音源仍按真实时长做seek/A–B。
5. 主库发布前备份在`.local/backups/edge-tts-main-before.sql.gz`，原学习表与v1内容的14组哈希基线在`.local/tts-evaluation/main-before-db.json`。测试先用隔离库，验证后切回主学习库。

## 验证与证据

- `python scripts/evaluate-edge-tts.py --generate`：26次生成与30个原始/候选文件PCM分析通过。结果`.local/tts-evaluation/{results,generation,repeat-results}.json`；日志`docs/evidence/tts-edge/logs/generation-and-analysis.log`。
- 试听页真实Chromium：30个等响度文件均实际播放；原始MP3切换、四速度、偏好保存/导出、375px无横溢出通过，pageErrors=[]；`browser-check-final.log`。自动化写入的偏好仅为UI测试，已恢复，不作为人工听感证据。
- v1/v2内容完整性与幂等生成：两套各10音源哈希/大小/真实时长/来源关联检查通过；v1哈希不变。
- 前端：typecheck、lint、13项单测、生产构建通过；日志`typecheck-final.log/lint-final.log/web-tests.log/web-build-final.log`。
- Java21/真实MySQL：15项测试、0失败/错误/跳过；覆盖默认v2、显式旧v1、重复发布不增加行、冻结版本拒绝篡改、旧版听写/草稿/恢复点，以及既有事务/幂等；`api-db-test.log`。
- Python本地服务脚本8项测试通过；`script-tests.log`。
- v2正式工作台：十句MP3实际解码且播放时间推进、四速度/seek/句内A–B、逐句草稿、beside/behind差异、同eventId重放、响应丢失后的刷新重试、跳过/暂停不算练习及音源故障提示通过；`v2-core-final.log`，passed=true、pageErrors=[]。
- 恢复专项：暂停位置恢复、快速切句、四快捷键、三种ended循环、断网草稿、多页If-Match冲突与显式解决、禁用存储时保留输入通过；`v2-recovery-complete.log`，passed=true、pageErrors=[]。初次恢复套件因跨页待同步恢复点产生412，保护机制保留冲突；脚本改为等待同步状态并在已有冲突时显式重新载入，最终通过，没有静默覆盖旧revision。
- 跨版本：默认v2、v1草稿与服务端revision不变、显式v1音频实播、旧复习卡返回v1原句通过；`version-history.log`。
- 主学习库：健康接口确认非测试库、默认v2且v1可访问、10句HTTP音频SHA256匹配；发布前后14组学习/旧内容数据哈希完全一致；`main-verification.log/main-activation.json`。Web/API自有PID与cwd核对通过，入口 `http://127.0.0.1:3100/lesson/demo-01?version=demo-01-v2&tab=dictation` 已打开。主库核对先于打开用户工作台，后续正常学习可产生新的恢复记录。

首次系统PCM转换在普通沙箱返回`fmt?`错误，同命令在获准环境通过，未据此推断代码或音源损坏；首次Playwright file协议被工具阻止，改用只绑定127.0.0.1的独立静态试听服务。预览测试的定位器/初始状态失败日志保留，最终通过另记，不冒称首次全部通过。主库激活脚本首次将响应头转换为大小写敏感dict，误判测试库标识；改用HTTPMessage大小写不敏感读取，接口实际返回false，完成后续只读核对，无须重复重启。

## 免费服务、来源与复现

`edge-tts`是第三方Python客户端，调用Edge在线服务；本次未配置订阅、账户密钥或付费API。它并非本项目签约的正式Azure Speech SDK集成，不承诺长期免费或服务保障。版本依据见[PyPI 7.3.1](https://pypi.org/project/edge-tts/7.3.1/)与[项目说明](https://github.com/rany2/edge-tts)。

在线合成会把文本发送给微软；本轮仅发送10句原创文本，没有发送学习草稿、录音、DB密码或个人练习记录。微软对在线朗读文本处理方式的说明见[Microsoft Edge隐私文档](https://learn.microsoft.com/en-us/legal/microsoft-edge/privacy#read-aloud)。

生成工具及参数现在可追溯，但库的[LGPL许可证](https://github.com/rany2/edge-tts/blob/master/LICENSE)不等于本项目已核实在线服务/输出的正式发布授权。沿用local_test_only、pending_review、releaseReady=false，不扩大公开发布范围。

复现（网络操作只在显式`--generate`时发生；默认分析缓存文件）：

```sh
python3 -m venv .local/tts-evaluation/venv
.local/tts-evaluation/venv/bin/python -m pip install -r scripts/tts-evaluation-requirements.txt
.local/tts-evaluation/venv/bin/python scripts/evaluate-edge-tts.py --generate
python3 scripts/tts-comparison-preview.py --serve
python3 scripts/publish-edge-gb-content.py
```

试听服务仅提供`.local/tts-evaluation/preview/`，绑定回环地址；停止它用`python3 scripts/tts-comparison-preview.py --stop`，不停止学习应用。
