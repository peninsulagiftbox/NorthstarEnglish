# Phase 10C-1 证据入口

2026-10-30 定向补验：报告见 `docs/progress/PHASE_10C_1_R.md`，可分享摘要见 `../phase10c1-r/README.md`。本地原始补验记录位于 `reacceptance/`；C01 NOT VERIFIED、C04 PASS（隔离范围）。历史原始材料不改写。

开发及隔离工程验收完成，详细结果见 `docs/progress/PHASE_10C_1.md`。C01声学150ms、逐句人工听查及原生后台项仍为 **NOT VERIFIED**，不将编译、截图或元素采样当作声音签收。

## 本地证据索引

- `preflight-local.json` / `personal-final-readonly.json`：真实个人009.15、43表、进程/原构建、history及备份/媒体核验；仅GET/SELECT/SHOW，不启动Spring。
- `execution-commands.jsonl`：逐命令argv/cwd/时间/真实退出码/log SHA-256；原失败保留。`migrations/commands.jsonl`及子目录为隔离SQL/容器/UUID门禁和恢复原始日志索引。
- `frozen-migrations.json`：23份历史迁移与6份新增迁移hash；新增首次实施后未再编辑。
- `migrations/*acceptance*.json`：旧备份升级、空库、三类故障、另一新目标恢复、实际备份工具和最终候选恢复/续学/重启。最新带时间戳的restored-runtime acceptance对应最终候选；早期记录保留。
- `audio-fixtures.json` / `audio-license-review.json`：原创文本/本机个人用途系统合成音、自制标记、源/解码PCM及MP3 hash、时长、标记样本位置、本机安装许可2.F依据。原始音频仅保留`.local/phase10c1/audio`，不分发系统声音素材。
- `phase10c1-browser-smoke.js.result.json`：真实播放器交互、10轮循环、20次同轨及20次异文件切换、长轨恢复；1609条元素诊断只作排错。
- `phase10c1-navigation-smoke.js`及`full-learning-loop.js`对应日志：真实请求延迟切版及Demo学习闭环。`output-capture-probe.webm/json`：实际浏览器输出捕获/解码能力探测，未完成测量校准。
- `boundary-acceptance.json`：明确无合格声学测量数据，统计为null，NOT VERIFIED。
- `candidate-inputs.json` / `delivery-audit.json`：最终JAR/BUILD_ID、131份构建输入、日志hash、停止的隔离目标/保留卷、个人原服务未部署证明。

私人SQL/逐值行快照/录音放受限`.local`。本目录只公开README和.gitignore；原始日志、机器身份、输出音频及私人数据索引按.gitignore留在本机。没有上传原件或把合成规则夹具的reviewer当真人审核。

## 未完成手工验收

1. 在身份已核验的隔离副本上固定系统/浏览器/设备/输出路径，先校准输出回录、编码延迟、已知PCM标记及测量不确定度。捕获探测成功不等于测量链合格。
2. 按05_AUDIO_ALIGNMENT_DESIGN第6.1节，四速率×共享/独立×首中末各连续10次；保留输出、带符号起止/loop误差、媒体/墙钟ms、最大/p95/丢样、不确定度。不得用1609条currentTime采样替代。全部有效绝对误差≤150ms且不确定度≤30ms才可签量化PASS。
3. 逐句人工听查12句、独立句、首尾/静音，记录截词/漏词及审校人/时间；源PCM标记与MP3编码后的媒体坐标先完成校准。
4. 实体Chrome/Safari播放单句/循环后最小化或切换应用，确认真实document.hidden时暂停、回前台不自动续播；完整音轨按浏览器能力播放，不承诺后台精确循环。
5. 旧Demo实体麦克风：允许→录制→停止→回放→刷新再播→人工自评；拒绝权限→提示/跳过→继续文本/写作；检查示范音与录音互斥。本轮未执行真人设备流程。

本轮隔离API/Web和7个MySQL容器已停止、卷及失败现场保留。重跑前应重新核验既有目标身份/端口并仅启动本轮资源；不可将测试工具指向个人库。个人部署另行审核。
