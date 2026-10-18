# SafeFlipLab — ROUND-1 结题验收复核报告（FINAL CLOSEOUT VERIFICATION）

**日期**：2026-10-17（GMT+8）　│　**执行者**：工程执行 AI（成员 A，由总控经平台子 Agent 派发）
**项目根**：`D:\SafeFlipLab`　│　**证据目录**：`D:\SafeFlipLab_AUDIT_2026-10-17\round1\`
**授权依据**：《SafeFlipLab 工程结题工作流》成员 A 任务书（第三节授权范围）
**本轮新增真实仿真**：**0**　│　**未启动 formal**　│　**未重跑 smoke/pilot**　│　
**未改历史账本、冻结配置、原始数据**　│　**未发布**

---

## 0. 结论：**全部验收项 PASS；未发现授权范围内缺陷；无需修复**

| 判定项 | 结果 |
|---|---|
| 独立复算器（141 项断言） | **PASS**（0 MISMATCH，EXIT 0） |
| 清单闸门 `--check` | **PASS**（EXIT 0） |
| doctor | **V01 17/17 GO；V02 7/7 GO**（均零 episode，EXIT 0） |
| 测试套件 | **V01 Ran 227, OK；V02 Ran 143, OK**（均 EXIT 0） |
| 报告幂等性 | **PASS**（58/58 产物：同位置重跑逐字节一致；与项目归档仅差预期的绝对路径前缀） |
| 账本只读复核 | **PASS**（与 `LEDGER_RECONCILIATION_20261016.md` 口径完全一致） |
| 科学数据完整性（隔离副本跑完全部命令后） | **PASS**（账本/配置/原始 JSON 与项目逐字节一致） |
| 授权范围内缺陷 | **无**（因此无修复、无新回归测试、无 D 编号新增缺陷条目） |
| 阻塞项 | **无** |

**一句话**：V01/V02 结题状态**再次得到独立复核确认**；历史文档中的关键计数
（V01 227 / V02 143 / 141 断言 / 528 行账本 / 748 磁盘 JSON）**全部与实际输出一致**。

---

## 1. 执行方式与隔离

| 项 | 值 |
|---|---|
| 隔离副本 | `D:\SafeFlipLab_AUDIT_2026-10-17\isolated_round1\`（46 MB） |
| 复制方式 | Python `shutil.copytree`，ignore `.venv`、`__pycache__`、`*.pyc` |
| `.workbuddy/` | **已包含**（`backups` 仅 612 KB，无需排除；副本内合计 1.4 MB） |
| 可能写文件的命令 | **全部**在隔离副本内运行（测试套件、4 条 report 命令、复算器） |
| 项目内运行的命令 | 仅经验证为只读的：两套 doctor、`build_final_manifest.py --check`、账本只读统计 |
| 解释器 | `/d/SafeFlipLab/.venv/Scripts/python.exe`（Python 3.13.14） |

**为什么复算器也在隔离副本运行**：`scripts/independent_verify_all.py` 尾部会把证据
写入 `docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`（**会写文件**），且 `ROOT` 硬编码为
`D:\SafeFlipLab`。按任务书「可能写文件的命令只能在隔离副本运行」，在副本内将该脚本的
`ROOT` 一行改为副本路径后运行（**仅改副本，项目内脚本未动**；原始副本存于
`round1/DIFFS/independent_verify_all.py.orig`）。

**为什么 report 也在隔离副本运行**：`report` 命令会重写 `reports/` 与 `v02/reports/`。
V01 CLI 的 `PROJECT_ROOT` 与 V02 的 `V02_ROOT` 均按**包位置**解析，故副本内运行只写副本。

---

## 2. 逐项验收结果（原始输出见 `round1/logs/`）

| # | 检查 | 命令（实际执行） | 结果 | EXIT |
|---|---|---|---|---|
| a | 独立复算 | 隔离副本内 `python scripts/independent_verify_all.py`（ROOT 指向副本） | **INDEPENDENT RECOMPUTATION: ALL CHECKS PASS**；`recomputed=` 断言行 **141**，`MISMATCH` **0** | **0** |
| b | 清单闸门 | 项目根 `python scripts/build_final_manifest.py --check` | `MANIFEST COUNT CHECK: PASS (files=200, bytes=3331986, categories=15, key_hash_rows=13)` | **0** |
| c1 | V01 doctor | 项目根 `python -m safefliplab doctor` | `17/17 checks passed`；`VERDICT: GO (interface verified; no episodes launched by doctor)` | **0** |
| c2 | V02 doctor | `v02/` 下 `python -m v02lab doctor` | `7/7 checks passed`；`VERDICT: GO`；冻结协议 hash `d175ec90eecf4e80...` | **0** |
| d1 | V01 测试 | 隔离副本 `python -m unittest discover -s tests -v` | **Ran 227 tests in 45.436s — OK** | **0** |
| d2 | V02 测试 | 隔离副本 `v02/` 下同上 | **Ran 143 tests in 1.851s — OK** | **0** |
| e | 报告幂等性 | 隔离副本内 4 条 `report --phase {smoke,pilot}` × 2 轮 | **58/58** 产物同位置重跑**逐字节一致**；路径归一化后与项目归档 **58/58 一致** | 0 |
| f | 账本复核 | 只读 csv 统计（磁盘 JSON 数**仅取自账本 outcome 行 `raw_path` 列**） | 见 §3，与历史对账报告**完全一致** | 0 |

> **pytest 不可用**：本 venv 未安装 pytest（`No module named pytest`），按任务书规定
> 改用 `unittest discover`。**未修改任何测试**。

> **V01 测试墙钟 45.4 s**（第五轮记录为 317.9 s）：环境性差异（机器/IO 负载），
> 用例数与结果一致（227，OK，无 skipped/FAIL/ERROR）。

---

## 3. 账本只读复核详情（权威 = 账本；磁盘 JSON 数取自 `raw_path` 列）

| 账本 | 数据行 | launch 分布 | outcome 状态 | 重复 key | raw_path→磁盘 |
|---|---:|---|---|---:|---|
| V01 活动 `runs/episode_ledger.csv` | **528** | smoke 24 + pilot 240 | completed 264（smoke 24 / pilot 240） | **0** | **264/264**，双向 1:1 |
| V01 作废备份 `...buggy_pilot_run1` | **488** | smoke 24 + **pilot 220** | completed 244 | **0** | 24 smoke 指向活动目录 + **220 pilot 归档映射**至 `runs/_buggy_pilot_run1/`（55 run 目录），**0 缺失 / 0 未登记** |
| V02 smoke | **48** | smoke 24 | completed 23 + **error 1（D37）** | **0** | 24/24，双向 1:1 |
| V02 pilot | **480** | pilot 240 | completed 240 | **0** | 240/240，双向 1:1 |

| 汇总 | 值 |
|---|---:|
| 有效发起（V01+V02） | **528**（V01 264 = smoke 24 + pilot 240；V02 264 = smoke 24 + pilot 240） |
| V01 作废 pilot | **220**（备份账本总 launch 行 244 = smoke 24 + pilot 220；口径差异非矛盾） |
| 历史真实发起合计 | **748**（= 528 有效 + 220 作废） |
| 磁盘原始 episode JSON（raw_path 派生） | **748**（V01 活动 264 + 作废 220 + V02 264） |
| 孤儿 launch / 重复计费 / 伪造成功 | **0 / 0 / 无** |

**REPRODUCTION_MANUAL §3.3 手动抽查复现**：

```text
528 Counter({'pilot': 480, 'smoke': 48})                                  # V01 活动账本 ✓
240 Counter({'discovery': 216, 'audit': 24})
    Counter({'Shared': 216, 'WideExplore': 12, 'VerifyFirst': 12})       # V02 pilot ✓
```

**科学数据完整性**（隔离副本跑完测试+报告后 vs 项目）：
`runs/` 490↔490、`v02/runs/` 272↔272，内容差异 **0**；4 个账本 + 3 个冻结/开发配置
SHA-256 全部 **SAME**。⇒ 本轮所有写操作都被限制在隔离副本内。

---

## 4. 报告幂等性详情

- 比对范围：`reports/` + `v02/reports/` 全部 **58** 个文件
  （49 个由 4 条 report 命令再生 + 6 个 `.pre_margin_backup` 备份 + 3 个手工维护文档）。
- **检查 A（权威判据）**：隔离副本内同一位置重跑一轮，**58/58 逐字节相同**。
- **检查 B**：将隔离产物中的绝对路径前缀归一化后与项目归档比对，**58/58 相同**。
- **必要的细微说明（非缺陷）**：8 个产物（4×`<phase>_summary.json`、4×`<phase>_report.md`）
  会嵌入自身输出路径的**绝对路径**；因此**跨目录**的原始字节比对必然出现前缀差异。
  同位置重跑（检查 A）不受影响。第五轮「32 个产物」的表述是当时的比较范围快照；
  本轮实际比较范围为 **58** 个文件，全部通过。

---

## 5. 与历史文档计数的核对（主张 → 本轮实测）

| 历史文档主张 | 本轮实测 | 判定 |
|---|---|---|
| V01 测试 227 | Ran 227 tests, OK | **一致** |
| V02 测试 143 | Ran 143 tests, OK | **一致** |
| 独立复算 141 项断言 | 141 行 `recomputed=`，0 MISMATCH | **一致** |
| V01 doctor 17/17；V02 7/7 | 17/17；7/7 | **一致** |
| V01 账本 528 行 = 264 episodes | 528 行（264 launch + 264 outcome） | **一致** |
| V02 账本 smoke 24 / pilot 240 | 24 / 240（smoke 含 1 error = D37） | **一致** |
| 有效合计 528；历史发起 748 = 磁盘 JSON 748 | 528；748；748 | **一致** |
| 作废 pilot 220（备份总 launch 244） | 220（244 = 24 + 220） | **一致** |
| 清单文件总数 198/199/200（历轮快照） | 本轮 `--check` 时 **200**（会随后续文档增长；**判据为 `--check` PASS，非固定字面量**） | **机制一致** |

---

## 6. 本轮未发现缺陷；无修复清单

- 6 项验收**全部一次通过**；定位根因与修复流程（任务书第四节）**未被触发**。
- 因此：**无代码/脚本/文档修复、无新回归测试、无 diff**（`round1/DIFFS/` 仅含
  隔离副本脚本 ROOT 补丁及其原始副本，属执行方式记录，非项目修改）。
- 本项目冻结历史保持：V01 formal **永久 NO-GO**；V02 **探索性/描述性研究，已结题**；
  两终点方向不一致（M1 正 Δ / M2 负 Δ）**保留并公开**；**不产出 p 值、不作显著性声明**；
  MDE=0.10 s **仅为样本量规划示例**。
- **本轮零新增真实仿真**；未启动 formal/smoke/pilot；未改历史账本任何一行；
  未改 `configs/formal_v01.json` 与 `v02/configs/v02_frozen_v1.json`；未发布。
  （V02 协议冻结的历史声明保持不变：**项目负责人自主冻结，非外部评审**。）

## 7. 需人工新授权的工作（不阻塞结题；与第五轮 §9 相同，G-1…G-10）

新增真实仿真 / 启动 formal / 重跑 smoke-pilot / 修改冻结配置或历史数据 /
改动上游 CornerCaseLab / GitHub 发布或投稿 / 付费服务与全局权限 /
获取上游 `PROTOCOL_TODO.md` 与源码 / 安排外部同行评审 / 提高端点保真度——
**全部需人工新授权**，本轮**均未发生**。

---

## 8. 交付物与证据索引

| 类别 | 文件 |
|---|---|
| 本报告 | `docs/FINAL_CLOSEOUT_2026-10-17.md` |
| 命令日志 | `round1/logs/step3a_independent_verify_all.txt`、`step3b_manifest_check.txt`、`step3c_doctor_v01.txt`、`step3c_doctor_v02.txt`、`step3d_tests_v01.txt`、`step3d_tests_v02.txt`、`step3e_report_*_run{1,2}.txt`、`step3f_ledger_reconciliation.txt` |
| 哈希与对账 | `round1/hashes/ledger_reconciliation.txt`、`idempotency_table.txt`、`scientific_data_integrity.txt`、三个快照 JSON |
| 决策追加 | `docs/AUTONOMOUS_DECISIONS.md` D49 |
| 交接/进度 | `docs/LATEST_HANDOFF.md`（第六节速览）、`docs/AUTONOMOUS_PROGRESS.md`（第六轮） |
| 清单 | `docs/FINAL_ARTIFACT_HASHES.csv` / `docs/FINAL_ARTIFACT_COUNTS.md` / `docs/FINAL_DELIVERY_MANIFEST.md`（已重生成；`--check` **PASS**） |
