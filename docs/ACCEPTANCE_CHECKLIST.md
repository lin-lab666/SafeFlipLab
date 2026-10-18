# ACCEPTANCE_CHECKLIST — SafeFlipLab 逐项验收与人工 GO/NO-GO 判据

> 依据：《SafeFlipLab WorkBuddy 一次性执行总指令》§10「完成前自查」+ §8 阶段 G 交付清单。
> 本清单只写**可核验事实**：真实命令、退出码、文件路径、计数。凡未达标者明确标 `NOT DONE` / `BLOCKED`，
> 不出具「全部通过」结论。
>
> 最后更新：2026-10-15（GMT+8）；本轮为**结构化输出补齐 + F-06 缺陷修复**（D27），
> **零新真实 episode**。

---

## 0. 结论摘要

| 维度 | 结论 | 依据 |
|---|---|---|
| 工程可复现性 | **GO** | `.venv` Python 3.13.14；`doctor` 17/17 PASS |
| 单元测试 | **GO** | **V01 227 项全过**，0 失败 0 错误，EXIT 0（`docs/V13_FINAL_V01_TESTS_20261016.txt`） |
| 真实 smoke（≤24） | **GO（已用满 24/24）** | 账本 + 原始 JSON 指纹 |
| 真实 pilot（≤240） | **GO（已用满 240/240）** | 账本 528 行 = 264 episodes |
| §6 结构化产物 | **本轮补齐 DONE** | `reports/*_episodes.csv|jsonl|anchors|budget_summary|comparisons` |
| 阶段 G 文档 | **本轮补齐 DONE** | 含本文件与 `reports/pilot/REPORT.zh-CN.md` |
| 协议冻结 | **BLOCKED（待人工）** | D4/D5/D6 仍 PROPOSED |
| 科研可行性（formal） | **NO-GO（见独立评审）** | 零碰撞 → 主指标零方差 |
| formal 执行 | **NOT STARTED / AWAITING HUMAN GO** | 双层安全门完好 |
| GitHub 发布 | **NOT STARTED** | 未 init、未 push、未 release |

---

## 1. 环境与可复现性

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 1.1 | 真实 Python 3.13 项目 venv | ✅ `3.13.14` @ `D:\SafeFlipLab\.venv` | `docs/DOCTOR_20261015.txt` |
| 1.2 | PyCharm 可直接打开该目录 | ✅ 标准工程布局 + `pyproject.toml` | `pyproject.toml` |
| 1.3 | 依赖锁定可复现 | ✅ `cornercaselab==0.3.0`(git tag v0.3.0)、`highway-env==1.10.2`、`gymnasium==1.2.2`、`numpy<3`、`matplotlib<4`、`Pillow<13` | `requirements.txt`、`doctor` |
| 1.4 | CLI 可执行且 `--help` 存在 | ✅ `doctor/smoke/pilot/report/formal` | `safefliplab/cli.py` |
| 1.5 | 未改系统 Python / 未提权 / 未改 ACL | ✅ 全部在项目 `.venv` 内 | — |

复现命令：
```powershell
cd D:\SafeFlipLab
.\.venv\Scripts\python.exe -m safefliplab doctor                                 # 必须 GO
.\.venv\Scripts\python.exe -m unittest discover -s tests -v                      # V01 227 项
.\.venv\Scripts\python.exe -m safefliplab report --phase smoke
.\.venv\Scripts\python.exe -m safefliplab report --phase pilot
```

---

## 2. A–G 阶段逐项验收

### 阶段 A｜只读核查 —— **DONE**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 目录/文件/锁/旧运行盘点 | ✅ | `docs/PROGRESS.md` 阶段 A |
| `policy=boundary` 六维 schema 与合法域核实 | ✅ `front_gap∈[18,80]`、`ego_speed∈[20,32]` | `docs/PROTOCOL_V01.md` §2 |
| 碰撞 outcome 语义核实 | ✅ `ego_collision = env.vehicle.crashed` | `safefliplab/adapter.py` |
| ≥5 篇可核验文献 | ✅ 6 项（含 DOI/链接） | `docs/RELATED_WORK.md` |
| 上游许可与来源归属 | ✅ 只读引用，未复制冻结数据 | `docs/PROVENANCE.md`、`docs/ATTRIBUTION.md` |

### 阶段 B｜可运行独立工程 —— **DONE**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 目标目录布局齐备 | ✅ `safefliplab/ configs/ scripts/ tests/ runs/ reports/ docs/` | 项目根 |
| README 中/英、LICENSE、CITATION、.gitignore | ✅ | `README.zh-CN.md`、`README.md`、`LICENSE`(Apache-2.0)、`CITATION.cff` |
| 未杜撰作者/未擅自公开 | ✅ | `CITATION.cff` |

> 注：`scripts/` 目录存在但为空；审计与取证脚本统一放在 `.workbuddy/tmp_audit/`（本轮新增
> `runid_audit_20261015.py`）。此为**非缺项**（原指令该目录标注「可选」）。

### 阶段 C｜四条件反事实协议与账本 —— **DONE**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 四条件唯一变更（`00/10/01/11`） | ✅ 仅 `front_gap += 2.0 m` / `ego_speed -= 1.0 m/s` | `tests/test_domain.py`、`safefliplab/domain.py` |
| 合法域严格、无 `clip` | ✅ 越界直接报错 | `tests/test_domain.py` |
| 同 repetition 四条件共享 `sim_seed` | ✅ | `tests/test_seeds.py` |
| 真实 `ego_collision` 无插补 | ✅ 缺失记 `unknown`，绝不当 0/1 | `tests/test_report_structured_outputs.py` |
| **先持久化 attempt 再调用仿真器** | ✅ `reserve_launch` 原子预占 | `safefliplab/ledger.py`、`tests/test_ledger_safety.py` |
| 原始日志只增不覆盖 | ✅ | `runs/<run_id>/*.json` |
| 防重复执行 / 并发不超支 | ✅ 8 进程 cap=3 实测 | `docs/F01_LEDGER_ACCEPTANCE_20261013.txt` |

### 阶段 D｜两种方法与独立审计 —— **DONE（含 PROPOSED 待批）**

| 检查项 | 结果 | 证据 |
|---|---|---|
| WideExplore / VerifyFirst 实现 | ✅ | `safefliplab/methods.py` |
| 正式计划精确闭合 800/800 | ✅ | `tests/test_formal_scheduling.py` |
| discovery/audit 严格隔离、无泄漏 | ✅ 文件级 + 代码级 | `tests/test_experiments.py::TestPilotFlow` |
| 跨 `master_seed` 隔离 | ✅ 5 元组隔离键 | `docs/DECISION_LOG.md` D12 |
| VerifyFirst 最终提名排序细化已记录 | ✅ | `docs/PROTOCOL_V01.md` §5（标 PROPOSED）、D5 |
| **D4/D5/D6 人工批准** | ❌ **未批准（阻塞）** | `docs/DECISION_LOG.md` |

### 阶段 E｜统计与图表 —— **DONE**

| 检查项 | 结果 | 证据 |
|---|---|---|
| 4 个配对量 + reverse/rescue 公式 | ✅ 空结果返回 `None` 而非 0 | `safefliplab/stats.py`、`tests/test_stats.py` |
| 未继承 CornerCaseLab Wilson 21/30 | ✅ | `docs/PROTOCOL_V01.md` §4 |
| 绘图只在有真实数据时生成 | ✅ | `tests/test_figure_axes.py` |
| 无 `1e-17` 伪轴、点估计不冒充 CI | ✅ | `docs/DECISION_LOG.md` D22 |
| **§6 结构化产物（5 类）** | ✅ **本轮补齐** | 见 §3 |

### 阶段 F｜单测 + 真实 smoke + 真实 pilot —— **DONE（预算已用满）**

见 §4、§5。

### 阶段 G｜中文交接与科研说明 —— **DONE（本轮补齐 2 项）**

| 交付物 | 状态 |
|---|---|
| `docs/PROGRESS.md` | ✅ |
| `docs/LATEST_HANDOFF.md` | ✅ |
| `docs/DECISION_LOG.md`（D1–D27） | ✅ |
| `docs/PROTOCOL_V01.md` | ✅ |
| `docs/ACCEPTANCE_CHECKLIST.md` | ✅ **本轮新建** |
| `docs/RELATED_WORK.md` | ✅ |
| `README.zh-CN.md` / `README.md` | ✅ |
| `docs/OWNER_GUIDE.zh-CN.md` | ✅ |
| `reports/pilot/REPORT.zh-CN.md` | ✅ **本轮新建** |

---

## 3. §6 结构化产物验收（本轮补齐）

| 文件 | 行数（pilot） | 核验要点 |
|---|---|---|
| `reports/pilot_episodes.csv` | 240 数据行 | 每已计费 episode 一行；`billed=1`；列宽固定 |
| `reports/pilot_episodes.jsonl` | 240 行 | 与 CSV 同集合，可重读 |
| `reports/pilot_anchors.csv` | 27 行 | 每 (seed, method, stream, anchor) 的 Y 计数/分母/比率/4 差值 |
| `reports/pilot_budget_summary.csv` | 1 行 | cap 240 / launched 240 / unused 0 |
| `reports/pilot_comparisons.csv` | 2 行 | audit 行 `computable=1` 但 `meets_formal_anchor_requirement=0`（pilot 仅 3 锚 < 正式 5 锚） |

smoke 阶段同构（`reports/smoke_*`）。

**自洽核验（机器可查）**：`denominator == n_complete_quartets`；`rate_c == Y{c}_count / denominator`；
`unused_slots == cap - launched`；pilot anchors 行数 27 = WideExplore 15 锚 discovery + 3 锚 audit +
VerifyFirst 6 锚 discovery + 3 锚 audit。全部通过（`tests/test_report_structured_outputs.py`）。

图表（真实数据才有）：
- `reports/pilot/figure_1_paired_condition_outcomes.png`
- `reports/pilot/figure_2_forest_delta_both.png`
- `reports/pilot/figure_3_discovery_to_audit.png`
- `reports/pilot/figure_4_margin_forest_ttc.png`（标注 NON-PROTOCOL）

---

## 4. 单元测试验收

| 指标 | 值 |
|---|---|
| 命令 | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` |
| 通过 | **225** |
| 失败 | **0** |
| 错误 | **0** |
| 跳过 | **0** |
| 退出码 | **0** |
| 墙钟 | 273.7 s（Windows `fsync`/临时目录缓慢，与代码无关） |
| 证据 | `docs/V09_TEST_RESULTS_20261015.txt` |

里程碑：98 → 106 → 146 → 169 → 183 → 190 → 209 → **225（本轮 +16）**。

本轮新增：
- `tests/test_run_id_label.py`（5 项）—— F-06 回归
- `tests/test_report_structured_outputs.py`（11 项）—— §6 结构化产物 + 未完成尝试语义

---

## 5. 真实实验与预算验收

| 阶段 | 上限 | 已发起 | 完成 | 错误 | 中断 | UNKNOWN | 未用 slots |
|---|---:|---:|---:|---:|---:|---:|---:|
| smoke | 24 | **24** | 24 | 0 | 0 | 0 | 0 |
| pilot | 240 | **240** | 240 | 0 | 0 | 0 | 0 |
| formal | 12800 | **0** | 0 | 0 | 0 | 0 | 12800 |

- 权威来源：`runs/episode_ledger.csv`（528 数据行 = 264 launch + 264 outcome；header 为 20 列旧式）。
- 全部 264 个 completed episode 的 `ego_collision=0`、`termination=goal`。
- **不计入有效证据**：首次 pilot 的 220 个无效 episode（阶段隔离 bug）已隔离于
  `runs/_buggy_pilot_run1/` 与 `runs/episode_ledger.csv.buggy_pilot_run1`，仅作审计留痕。
- **未发生任何偷偷重试**：runner 启动即计费，错误立即上浮。

---

## 6. 本轮新发现缺陷（F-06）验收

| 项 | 内容 |
|---|---|
| 现象 | 66 个 `run_id` 中 **2 个**（均在 smoke）内嵌方法名 `WideExplore`，而 `method` 列/原始记录为 `VerifyFirst` |
| 判定依据 | `sim_seed` 为 SHA-256 且**含 method**：实测 `1524636909` 与 `VerifyFirst` 复现一致，`WideExplore` 应为 `3812604799` |
| 全账本核验 | **528/528 行** `sim_seed` 与 `method` 列一致；**0 处不一致** |
| 影响 | 仅 `run_id` 字符串命名；Y 值、`sim_seed`、锚、条件、统计量、pilot、formal **均不受影响** |
| 处置 | 修复 `_new_run_id()` 取显式 method；**历史账本不改写**，缺陷作为历史事实披露 |
| 证据 | `.workbuddy/tmp_audit/runid_audit_20261015.txt`；`docs/DECISION_LOG.md` D27 |
| 连带修复 | `load_phase_data` 不再静默丢弃「只有 launch、无 outcome」的已计费尝试（改记 `unknown` 并计入 `incomplete`） |

---

## 7. 正式评估（formal）前准备验收

| # | 检查项 | 结果 | 证据 |
|---|---|---|---|
| 7.1 | 8 个 SHA-256 主种子已冻结，非结果挑选 | ✅ `3451794858, 3280522798, 3404856911, 4151677968, 565867193, 2023892289, 4034206253, 3582183474` | `configs/formal_v01.json` |
| 7.2 | 配置漂移校验 | ✅ `validate_formal_config` | `tests/test_formal_config.py` |
| 7.3 | 每 (method, seed) 独立 800 预算作用域 | ✅ | `tests/test_ledger_safety.py` |
| 7.4 | 保护性 CLI 双保险 | ✅ 需 `--confirm` **且** `--max-episodes 12800`；之后仍抛错 | `safefliplab/cli.py` |
| 7.5 | 独立安全门 `_require_formal_go` | ✅ 在构造任何仿真器**之前**拒绝非测试替身 | `tests/test_formal_scheduling.py` |
| 7.6 | `formal_started = false` | ✅ 账本 formal 行数 0 | 账本 |
| 7.7 | 冻结协议 hash 核对 | ✅ 协议指纹校验通过 | `safefliplab/protocol.py` |
| 7.8 | **D4/D5/D6 等 PROPOSED 规则人工批准** | ❌ **未批准** | `docs/DECISION_LOG.md` |

---

## 8. 明确的缺项与阻塞（NOT DONE / BLOCKED）

| # | 缺项 | 状态 | 说明 |
|---|---|---|---|
| 8.1 | formal 12,800 次真实 episode | **NOT DONE（协议禁止）** | 必须人工 `GO FORMAL`；本轮未启动任何 episode |
| 8.2 | D4 `sim_seed` 完整映射批准 | **BLOCKED** | PROPOSED，待人工签字 |
| 8.3 | D5 tie-break 顺序与方向批准 | **BLOCKED** | PROPOSED，待人工签字 |
| 8.4 | D6 pilot 内部配额批准 | **BLOCKED** | PROPOSED，待人工签字 |
| 8.5 | 零碰撞/主指标零方差处置（BLOCKER-3） | **BLOCKED** | 独立评审建议对 formal 为 **NO-GO**；是否改用连续终点需人工裁决 |
| 8.6 | 有效样本权重（D5/D10 `valid_n`）确认 | **BLOCKED** | 待人工确认 |
| 8.7 | PD-01（首次 pilot 累计超上限 220）接受 | **BLOCKED** | 已披露保留，未用重定义预算掩盖 |
| 8.8 | GitHub 发布 | **NOT STARTED（禁止）** | 未 init、未 push、未 release |
| 8.9 | V02 提案（含 B-01…B-12） | **PROPOSED / 未批准** | 本轮未启动任何 V02 真实 episode |

---

## 9. 人工 GO / NO-GO 判据

### 9.1 允许 `GO FORMAL` 的前置条件（全部满足才可授权）

1. [ ] 逐项批准 D4 / D5 / D6，或改用书面指定的替代规则；
2. [ ] 对 BLOCKER-3 作出裁决：接受“主指标可能零方差”并预注册替代/次要终点，**或**改用 V02 连续终点设计；
3. [ ] 确认 PD-01（首次 pilot 220 无效 episode）接受为已披露事故；
4. [ ] 确认 `valid_n` 权重与提名规则的最终顺序；
5. [ ] 授权前重跑 `doctor`（须 17/17 GO）并复核 `configs/formal_v01.json` 未被修改；
6. [ ] 提供明确书面 `GO FORMAL`（本期工作之外）。

### 9.2 建议 NO-GO 的情形

- 若要求在**现有 V01 二元碰撞主指标**下直接执行 formal：**建议 NO-GO**。
  理由：现有 264 个真实 episode 全部零碰撞，主指标 `delta_both` 方差为 0，
  两方法提名将完全退化到 tie-break，**无法回答“谁更强”**（详见
  `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`）。

### 9.3 若授权 GO，formal 启动方式（仅作记录，**本轮严禁执行**）

```powershell
.\.venv\Scripts\python.exe -m safefliplab formal --confirm --max-episodes 12800
.\.venv\Scripts\python.exe -m safefliplab report --phase formal
```

---

## 10. 签署

| 角色 | 结论 | 日期 |
|---|---|---|
| WorkBuddy（工程/测试/审计） | A–G 获授权范围内 **DONE**；formal 相关项 **BLOCKED** | 2026-10-15 |
| 人工审核（用户） | ☐ GO FORMAL　☐ NO-GO　☐ 需补充信息 | ______ |
