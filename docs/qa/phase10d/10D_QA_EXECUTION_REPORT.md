# Phase 10D-QA 执行报告（第一轮：QA-PREP）

日期：2026-10-31（Asia/Shanghai）。执行者：独立 QA 会话（非 10D-CORE 开发者）。

## 1. 基线与环境

- 主工作树：`/Users/wangshiqi/Project/NorthstarEnglish`，branch=main，HEAD=`ff0dbe1f8b89a1817c2f5a0e7ba0755d5f971188`，含大量未提交 10D-CORE 业务变更（knowledge 包、V012.01–07、前端 KnowledgeConcepts 等）。QA 全程只读访问，未修改、未复制进 QA 分支。
- QA worktree：`/Users/wangshiqi/.codex/worktrees/northstar-10d-qa/NorthstarEnglish`，原有 detached HEAD@ff0dbe1（干净）。本会话在其上创建分支 `test/10d-qa`（任务书建议名与路径已存在冲突：任务书建议 `../NorthstarEnglish-10D-QA` 不在沙箱可写范围，且同名 QA worktree 已存在；按任务书"报告冲突并使用经确认的现有工作区"处理）。
- 个人库 3308、个人服务 3100/8085：全程未触碰。未运行任何针对个人库的查询或写入。
- CORE 契约未冻结（无候选 SHA/OpenAPI 冻结声明），QA-EXEC 未开始。

## 2. 实际执行的命令（均 exit 0，cwd=主工作树除注明外）

| 命令 | 结果 |
| --- | --- |
| `git worktree list && git status --short && git branch --show-current && git rev-parse HEAD` | 确认基线与并行变更 |
| `git -C <qa-worktree> switch -c test/10d-qa`（提权） | 分支创建成功 |
| 读取 docs/phase10 03/04/07/08/09/10D 计划、PHASE_10C_2_R1、PHASE_10D_1 | 审计输入 |
| 读取 V012_01–07 SQL、knowledge 包 4 个 Java、ExerciseController/QuizReviewController 接入点、V011_01 唯一键 | 静态审计 |
| `shasum -a 256`（V012 迁移 + knowledge Java + 提交路径 + CORE 测试） | `evidence/sha256-baseline.txt` |
| `python3 -c json.load(...)`（3 个 fixture JSON） | JSON OK |
| `python3 -m py_compile`（qa/phase10d/tools/verify_qa_bundle.py，复制后执行） | 见 §4 |

未运行：Maven、npm、Playwright、任何 MySQL 语句（无隔离库授权与冻结候选）。

## 3. 本轮产出

- `docs/qa/phase10d/`：TEST_PLAN / FIXTURE_SPEC / RISK_REGISTER / EXECUTION_REPORT / BUG_REPORT / ACCEPTANCE。
- `qa/phase10d/`：fixtures（课程 A/B 登记文件、canonical_key 矩阵）、sql（negative_cases、invariant_checks）、tools（verify_qa_bundle.py）。
- 静态审计发现 1×P1 + 6×P2（全部 STATIC，见 BUG_REPORT）；D02 全部 BLOCKED_BY_CORE。

## 4. 结果判定

- QA-PREP：完成。
- D01 运行时验收：NOT VERIFIED（BLOCKED_BY_CORE：等待冻结候选 SHA、隔离库授权与 fixture 播种）。
- D02：BLOCKED_BY_CORE（实现不存在）。
- 本轮结论：**BLOCKED（QA-PREP 完成，等待 CORE 冻结候选与集成授权）**。

## 5. CORE 冻结时需提供

1. 固定 Git 提交或候选 SHA + 未提交文件逐文件 SHA-256（当前工作树含未提交变更，仅 commit SHA 不足以复现候选）。
2. 隔离库运行/授权说明（QA 不使用 grant-study.py；需专用授权入口）。
3. QA-BUG-001..007 的修复决定（修复或书面说明不改的理由）。
