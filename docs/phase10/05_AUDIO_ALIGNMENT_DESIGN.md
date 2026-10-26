# Phase 10A · 05 整课音频、片段与对齐

状态：待审设计。实际依据：V002的sentence/audio约束、`catalog/ContentPackage.checkedAudio`、`CatalogController.lesson/audio`、`study/StudyController.validate`，Web `lib/media/{AudioController,MediaProvider,timeline}.ts[x]`、`components/player/PlayerBar.tsx`、`demo-word-timings.json`。现有词点仅Demo特定音频hash匹配，不等于通用强制对齐。

## 1. 统一音频模型

一条AudioAsset表示一个不可变文件；一条SentenceSegment为 `{sentenceId, assetId, startMs, endMs}`，区间半开 `[startMs,endMs)`、整数毫秒。完整主音频通过lesson_audio关联，多个句子引用同asset。Demo独立句文件适配为start=0、end=文件时长，不拼接、不替换旧文件。

- V002新增迁移取消uq_sentence_audio，替换start=0为start≥0，保留end>start与同版媒体FK；先为FK准备替代非唯一索引，不能盲DROP一个仍被FK依赖的索引。
- end≤asset.duration在导入/发布/读取防御校验；单行CHECK不能查询另表。按同asset句序单调、不重叠；允许静音间隙，不允许句子重叠抢播。多人重叠对话在首版需人工确定可用切点，否则对齐不可发布。
- 完整主音轨可包含片头和间隙，完整播放时不裁掉；逐句模式只播片段。不同独立文件只有“句序拼接进度”，不伪称原整课时间轴。
- 只支持当前audio/mpeg，继续200/206/416。其他编解码另行必要性验证；Range是字节区间，与毫秒定位不同。

## 2. 时间坐标与恢复

前端内部使用 `{assetTimeMs, segmentOffsetMs, lessonPosition}` 明确区分，禁止同一数字依场景猜含义：

`assetTimeMs = startMs + segmentOffsetMs`；`segmentDurationMs = endMs - startMs`。

例：第2句在整课文件[8400,12100)，句内偏移1500表示文件位置9900；不能保存9900后再加8400。

兼容协议：原 `/study/resume.positionMs` 永远表示所选播放句的相对偏移，旧Demo无需改数据；服务校验0≤positionMs≤end-start，移除600000硬阈值并依据受限内容时长校验。新增显式 `playbackCoordinate='segment_offset_v1'`（缺失按旧语义）；完整音轨模式另存 `playbackMode/fullAssetId/assetPositionMs`，验证同版主音轨FK/服务关联，不能将整课位置塞进旧字段。恢复默认暂停；新内容版本不套用旧音频坐标。

全音轨静音处playingSentenceId可空，active segment无匹配时不强行标上一句“正在播”；UI保留聚焦句作为阅读选择。句末位置可等于片段时长，恢复仍暂停，用户播放时按模式重置或前进。

## 3. 播放器最小改造

Track扩为 `{sentenceId,assetId,uri,startMs,endMs}`；AudioController保留单HTMLAudioElement与token淘汰异步请求。

1. 换句同asset：暂停/调整当前片段、seek到start+offset，复用src，不重新下载；换asset等待loadedmetadata及seeked再play，旧token回调不得更新新句。
2. `timeupdate`与前台requestAnimationFrame观察片段end；到边界执行一次带token的endSegment，防重入；同源相邻句不能等待文件ended。ended仅为文件末尾兜底。
3. single到句尾暂停；sentence loop回start；sequence前进到下一段；list末句回首句。整课模式自然播放并据真实asset时间匹配当前句，末尾按整课循环设置处理。
4. A/B内部明确句内偏移，必须0≤A<B≤segmentDuration；换句清空，seek换src不误写旧文件；跨句A/B不作为10C必需项，若同整课音轨实现须另验，跨文件不支持。
5. 变速保留0.75/1/1.25/1.5和preservesPitch；切句保持速率；音频时间坐标不除以速率。录音开始暂停示范音频，拒绝自动播放可点击恢复，不标played/练习。
6. 后台页没有硬实时片段边界保证：visibilitychange暂停片段模式，回前台点击恢复；整体模式可按浏览器能力播放但不得承诺后台精准循环。无AudioWorklet/WebAudio采样级承诺。

`PlayerBar`当前词点、句端、文件时长与进度显示一并改为片段时间；`MediaProvider`保留选句与播句区分；`timeline.matchingWords`需要versionId/assetHash/segment边界匹配，词点用asset绝对毫秒，展示前转句内坐标。无词点时只显示真实进度，不合成伪波形。

## 4. API、完整性与降级

lesson响应新增startMs/endMs/paragraphId、去重audioAssets和可选fullAudioAssetId；兼容旧每句audio结构但由同asset映射生成。TypeScript Sentence目前未声明start/end，必须同时补类型与运行校验，不能仅后端加字段。

`checkedAudio`从Demo正则切为清单白名单+realpath位于content root、拒绝路径穿越/软链接越界、流式大小/hash验证；读取不再每句全量重读共享大音频。导入完整hash，运行缓存须以不可变hash及文件身份/mtime/size失效，不仅按URI永远信任；篡改/丢失仍返回明确媒体错误。

当前任何句音频缺失使整个lesson503。拟新增媒体状态而让合法文本可读：lesson附audio.status=unavailable/code，音频端点继续503、听写提交仍拒绝音源不可用；阅读/写作可以继续。旧错误测试改为“媒体503+文本可见+禁止假听写”，保留损坏检测断言，不能把503直接删掉当成功。

## 5. 强制对齐与人工核验

流水线：合法原音频+校对后原文 → 临时PCM（保留原文件hash/采样率/时长）→ 离线强制对齐候选 → 词/句时间合并 → 人工听查和边界编辑 → 审校JSON → 导入校验。对齐只估计“给定文本在音频的位置”，不是识别准确率、发音评分或学习成绩。

暂不锁定模型/框架，不在10A安装下载；10E用两段自有短音频比较Mac本地资源、覆盖率、可重现性、模型与程序许可。没有合格工具时手工标注是正式可用兜底，不能编造模型置信分。

记录 `alignmentId/tool/version/modelHash/parameters/audioSha256/transcriptSha256/timebase/reviewer/reviewedAt/status`；候选状态auto_draft→needs_review→verified/rejected。每句边界均人工听核、检查截词/漏词/错说话者；低置信/静音/专名重点复核。audioSha256关联实际原音频hash，transcriptSha256关联该音轨覆盖句子的规范化转录hash，不要求两者相等；完整课文与独立句的覆盖区别和transcript-v1见06第4.1节。任何文本或音频hash变化使验证失效，重新审校并新建内容版本。

## 6. 验收与风险

10C使用自有共享音频：含片头静音、句间间隙、非零start、多句同asset、句尾、>10分钟完整文件及Demo旧句文件。验证跨资源/同资源定位、全部循环、变速、A/B、刷新恢复、快速换句/Promise拒绝、DB/媒体故障、Range。

量化目标（提议，未实测）：前台Chrome实播边界与人工核定点误差≤150ms，所有句逐一实听无截词；1.5倍速、连续循环10次及快速切换20次无重复跳句。越界、NaN、end>duration、重叠、错hash全部拒绝；后台暂停策略实测。浏览器不是采样级剪辑器，若目标失败要报告并调整边界策略，不能声称精确无误。音频本身授权仍需独立审核。

### 6.1 边界误差测量协议（补充3）

区分两类误差：①内容对齐质量（人工核定的start/end是否截词/漏词）；②播放器执行误差（已给定边界后实际可听起止偏差）。不能只看currentTime、timeupdate触发或截图就声称可听边界达标。

10C用合法自有可解码测试音轨，在目标边界嵌入已知时间的短音标记，并保留源PCM采样率/标记位置、编码文件hash及编码延迟校准信息。固定设备/输出路径、系统与浏览器版本，记录前台可见、倍速、区间、缓存条件。日志采集performance.now、seek请求/seeked、currentTime、暂停/回跳，作为定位辅助；用获授权的本地输出回录或经验证的浏览器音频捕获取得实际可听输出，不能用渲染调度时间冒充输出。无输出捕获条件时记录NOT VERIFIED，并提供人工听查结果，不能签≤150ms PASS。

以输出中的已知标记建立“源音轨媒体时间→实际输出时间”映射，按0.75/1/1.25/1.5倍速分别校准，分离固定输出延迟和seek/暂停偏差。报告起点偏差、终点超播/提前停止及loop回跳误差（带符号值与绝对值，统一换算源媒体毫秒，同时保留墙钟毫秒）；边界前后音标记须能判断实际截断，不能只测静音。记录测量分辨率/不确定度，不确定度>30ms则不足以签此预算通过。

每种速率、独立/共享音轨、首中末片段各连续10次；逐次记录及汇总最大绝对误差、p95、异常/丢样数，不能用平均值掩盖超限。工程Go为所有有效实测绝对误差≤150ms，另逐句人工听查无截词/漏词；后台只验证暂停策略，不参与精确边界承诺。原始输出、日志、计算方式与失败条件随PHASE_10C报告保存。若失败，调整片段观察/暂停策略后重测，或另行评审预算/实现；HTMLAudioElement仍不是采样级裁剪器。
