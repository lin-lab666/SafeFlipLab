# SafeFlipLab — 正式实验前最终研究审计（FINAL_PRE_FORMAL_AUDIT）

> 审计类型：**静态审计（只读）**。本审计**未启动任何真实 smoke / pilot / formal 仿真**。
> 所用手段：账本只读取证、原始记录交叉核验、源代码审查、单元测试（98 项，0 真实 episode）、
> FakeAdapter 复现演示（0 真实 HighwayEnv episode）。
> 所有原始文件均原样保留，未覆盖 / 清空 / 补跑 / 美化任何历史结果。

状态时间：2026-10-12（GMT+8）；审计者：Hy3（接管后静态审计）。

---

## 0. 审计范围与约束

| 项 | 本次处理 |
|---|---|
| 新启动 smoke / pilot / formal 仿真 | **禁止**（用户明确约束） |
| 真实 episode 单元测试 | 允许且已执行（98 项通过，0 真实 episode） |
| 静态代码审查、历史日志核对、文档修订 | 允许且已执行 |
| 原始文件保全 | 全部保留，仅新增本审计文档与 2 个只读分析脚本 |
| 审计结束后 | 停止，不自行执行正式实验 |

证据来源（全部为既有文件，未重新生成实验数据）：
- `runs/episode_ledger.csv`（活动账本，528 行 = 264 launch + 264 outcome）
- `runs/episode_ledger.csv.buggy_pilot_run1`（首次无效 pilot 备份，489 行 = 244 launch + 244 outcome，含 smoke 24 + pilot 220）
- `runs/_buggy_pilot_run1/`（55 个 run 目录）、`runs/manifest_smoke_WideExplore.json`
- `safefliplab/*.py`（adapter / domain / seeds / runner / ledger / methods / experiments）
- `reports/*.md`、`docs/DECISION_LOG.md`、`docs/PROTOCOL_V01.md`、`configs/*.json`
- `tests/*.py`（含 D11 回归测试）

---

## 1. 已核实的工程状态

| 维度 | 状态 | 证据 |
|---|---|---|
| 运行环境 | Python 3.13.12 托管版 venv；cornercaselab 0.3.0、highway-env 1.10.2、gymnasium 1.2.2 | PROGRESS.md；`doctor` 17/17 PASS |
| 包实现（A–E） | 完整 | `safefliplab/` 全部模块 |
| 单元测试 | **98 passed / 0 failed / 0 error**（本次审计复跑，7.4s，0 真实 episode） | `python -m unittest discover -s tests` |
| smoke 真实实验 | 24/24 完成，0 错误 0 中断 | 活动账本 + 报告 |
| pilot 真实实验（有效） | 240/240 完成，0 错误 0 中断 | 活动账本 + 报告 |
| formal | **未执行**（协议禁止自动执行） | `cli.py` / `experiments.run_formal` 仅实现不运行 |
| 旧 CornerCaseLab | 未改动（仅 git 依赖安装复用） | D1 |
| GitHub 发布 | 未执行 | — |

**结论**：工程实现层面就绪（GO）；但正式启动存在下文列出的硬性未决项。

---

## 2. 全部真实 episode 预算总账（完整、含首次无效运行）

### 2.1 总账汇总（按阶段 / 运行尝试）

| 记录位置 | 阶段 | 发起 | 完成 | 错误 | 中断 | 计入有效证据? | 备注 |
|---|---|---:|---:|---:|---:|---|---|
| `runs/episode_ledger.csv`（活动） | smoke | 24 | 24 | 0 | 0 | 是 | 已验收，用满 24 上限 |
| `runs/episode_ledger.csv.buggy_pilot_run1` | pilot（首次，含 D11 bug） | 220 | 220 | 0 | 0 | **否** | 无效，隔离备份，排除出证据 |
| `runs/episode_ledger.csv`（活动） | pilot（修复后重跑） | 240 | 240 | 0 | 0 | 是 | 有效 pilot，用满 240 上限 |
| `runs/episode_ledger.csv`（活动） | formal | 0 | 0 | 0 | 0 | — | 未执行（协议禁止） |

### 2.2 跨阶段真实消耗（含被排除证据的运行）

- **smoke**：24 / 上限 24 → 偏差 **0**
- **pilot（累计真实发起）**：220（首次无效）+ 240（修复后）= **460** / 上限 240 → 偏差 **+220**
- **formal**：0 / 上限 12800 → 偏差 **0**（尚未启动）
- **全部阶段真实发起合计**：24（smoke）+ 460（pilot 累计）= **484** episodes

> 注意：smoke 的 24 行同时出现在活动账本与 buggy 备份 CSV 中（buggy 备份是重跑前的整本快照），
> 属同一批 smoke，不可重复计入。去重后真实唯一 episode = 484；pilot 累计 = 460。

### 2.3 首次无效 pilot 的 220 episodes 处置（按用户要求）

- **不计入有效统计**：活动账本已清空 pilot 行并重跑，有效证据仅 240。
- **保留在真实预算消耗**：协议规定"所有已发起 episode（含失败、中断、无效）计费"。220 已永久保留于
  `runs/episode_ledger.csv.buggy_pilot_run1` 与 `runs/_buggy_pilot_run1/`（55 个 run 目录），**不从预算中删除**。
- 这 220 正是 pilot 累计 460 超过 240 上限的 +220 来源。

### 2.4 时间线（来自账本 `started_utc`）

| 运行 | 阶段 | 最早启动 (UTC) | 最晚启动 (UTC) | 发起数 |
|---|---|---|---|---:|
| 1 | smoke（活动） | 2026-10-12T05:16:59Z | 2026-10-12T05:17:21Z | 24 |
| 2 | pilot 首次（buggy） | 2026-10-12T05:32:23Z | 2026-10-12T05:35:10Z | 220 |
| 3 | pilot 修复后（有效） | 2026-10-12T05:45:05Z | 2026-10-12T05:48:02Z | 240 |

---

## 3. ⚠️ PROTOCOL DEVIATION — 实验预算偏离（必须披露）

| 字段 | 内容 |
|---|---|
| **偏离编号** | PD-01 |
| **标题** | pilot 阶段真实累计发起 **460** episodes，超过协议上限 **240**，偏离 **+220**（达上限的 192%） |
| **原因 (Cause)** | 首次 pilot 运行存在阶段隔离 bug（D11）：仅发起 220 且锚集合错误（跳过 WideExplore 0/1/2、VerifyFirst 0/1），该运行**无效**。无效运行必须丢弃并重新干净运行；修复 bug 后重跑 pilot 又发起 240。两次累计 460。 |
| **发生时间 (When)** | 首次 buggy pilot 启动 2026-10-12T05:32:23Z（~05:35:10Z 结束）；修复后 valid pilot 启动 2026-10-12T05:45:05Z（~05:48:02Z 结束）。时序见 §2.4。 |
| **影响范围 (Scope)** | 仅 pilot 阶段预算。smoke（24，正）与 formal（0，未启）未受影响。有效科学样本仍为修复后干净的 240 episodes（位于 pilot 上限内）。 |
| **是否取得额外授权 (Extra authorization)** | **否**。首次 pilot 在"继续 pilot ≤240"授权下发起（单次 220 未超 cap，但因 bug 无效）；修复后重跑 240 是本构建在发现 bug 后的工程修复决策，**未就额外的 220 预算消耗取得用户单独授权**。既有授权仅覆盖"pilot ≤240"的单次运行，未覆盖"因 bug 重跑而累计 460"。 |
| **对研究有效性的影响 (Validity)** | 有效 pilot 为干净 240/240 重跑，科学有效性未受损；但累计预算超支 220 属程序 / 合规偏离。 |
| **对最终报告的影响 (Final report)** | 最终报告（含正式）必须如实披露：(a) 本偏离；(b) 仅有 240 有效 pilot episodes（非 460）；(c) 首次 220 已隔离保留但排除出证据。**不得通过事后重新定义预算掩盖偏离**。 |
| **处置 (Handling)** | 保留全部原始文件（活动账本、buggy 备份、55 个 run 目录）；不覆盖 / 不清空 / 不补跑 / 不美化。新增 D11 回归测试；建议在正式前人工复核跨 master_seed 隔离（见 §5.4）。 |

> 本偏离**不构成对有效 pilot 科学结论的否定**，但属于必须向人工评审透明披露的合规事件。

---

## 4. 全部有效结果均无碰撞 — 六点核查

> 样本：有效 smoke 24 + 有效 pilot 240 = 264 个 completed episodes，账本 `ego_collision` 全为 0。

### 4.1 ego_collision 是否确实来自真实 HighwayEnv 仿真？
**是，确认。**
- `adapter.run_episode` 调用 `cornercaselab.simulator.evaluate(...)` 并读取 `result["ego_collision"]`（bool），`runner` 写入账本 `ego_collision = 1 if result["ego_collision"] else 0`。
- 原始记录含 `trace_sha256_rounded_9dp`、`policy_steps`、`min_forward_ttc_sampled_s`、`reward_sum` 等**仅真实 HighwayEnv 才产生的字段**。
- 本审计抽查 12 个有效 pilot 原始 JSON：**12/12 含真实字段**；其 `result.ego_collision` 与账本 `ego_collision` **12/12 一致**（0 不匹配）。
- smoke 确定性重放 `determinism_check.all_conditions_match = true`（四条件 trace 哈希完全一致）→ 真实可复现。

### 4.2 front_gap +2.0m 与 ego_speed −1.0m/s 是否真实改变了对应初始场景？
**是，确认。**
- `condition_scenario()` 对 10/11 加 2.0m、01/11 减 1.0m/s；越界即抛错（绝不 clip，D3）。
- 抽查 12 个原始记录的 `conditioned_scenario` 相对 `anchor.scenario`：**12/12 正确**（00 不变、10 仅 +2.0 gap、01 仅 −1.0 speed、11 两者）。
- 3/3 完整 quartet 验证：四条件**仅在这两个字段上不同**，其余六维完全一致。

### 4.3 四个条件是否使用同一配对 sim_seed，其他条件是否保持一致？
**是，确认。**
- `sim_seed_for` 派生标签**不含条件代码**（四条件共享），且含 `master_seed` / `method` / `stream` / `anchor_id` / `repetition`（`seeds.py`，与 D4 一致）。
- 账本核查：每个 quartet key（`run_id, anchor_id, repetition, stream`）的 4 个 launch 行 `sim_seed` 完全一致 → 活动账本与 buggy 账本 `inconsistent_sim_seed_keys = 0`。
- `stream` 区分 discovery / audit，保证审计种子绝不与 discovery 重复（D4 / D8）。

### 4.4 boundary 控制器与场景适配是否正确？
**是，确认。**
- `adapter` 冻结 `CONTROLLER_POLICY = "boundary"`，调用 `evaluate(scenario, sim_seed, policy="boundary", settings=SimSettings(25s, 15Hz, 5Hz))`。
- `fingerprint()` 固定 `controller_policy=boundary`、`cornercaselab_version=0.3.0`、`highway_env_version=1.10.2`、`gymnasium_version=1.2.2`。
- 抽查 12/12 原始记录的 `adapter_fingerprint.controller_policy = "boundary"`；在所有条件 / 方法 / 种子 / 阶段保持一致（D2）。

### 4.5 所有有效样本为零碰撞，是否说明当前实验缺乏可检测的风险差异？
**谨慎结论：在当前 dev_seed 样本下，确实无法检测任何风险差异；但这是预期的描述性结果，真正的担忧在正式设计层面。**
- 264 个有效 episode 全部 `ego_collision=0` → `delta_both/gap/speed`、`interaction`、`reverse`、`rescue` 在该样本内**全为 0**，没有任何碰撞方差可供差异检测。
- 协议已声明 dev_seed 与 pilot 为**描述性 / 管道验证，非证据**，故该零方差本身不构成错误。
- **研究设计风险（需人工关注）**：若正式 8 seed × 800 = 12,800 episodes 下，`boundary` 控制器在本域的碰撞基线率同样接近 0，则本研究在统计上可能**不足以检测两种干预的效应**（低事件率 → 低功效）。协议**未预注册最低事件率 / 功效 / 可检测效应量检查**。这属于设计权衡而非代码 bug，须在投入 12,800 episodes 前由人工决策（见 §7 BLOCKER-3）。

### 4.6 是否触发原任务书要求的技术 GO/NO-GO 停止条件？
**否（按书面协议）。**
- `PROTOCOL_V01 §7` 停止条件为：(a) 接口 / 语义不可比 → NO-GO；(b) smoke/pilot 关键技术失败 → BLOCKED；(c) formal 未经人工 GO → 仅实现 / 准备。
- "零碰撞"不在其中；且接口正常、0 错误 / 0 中断，技术 GO/NO-GO 条件**未被触发**。
- 但 §4.5 提出的研究设计风险需人工裁决（见 §7），不自动触发协议停止条款。

---

## 5. 正式运行安全审计 — D4 / D5 / D6 / D11 审查

### 5.1 D4 — sim_seed 映射（PROPOSED，待批准）
- 规则：`sim_seed = SHA256([protocol, "seed", master_seed, "sim", method, stream, anchor_id, repetition])`；含 `method` 与 `stream`，**不含条件代码**（四条件共享），含 `repetition`。
- 审查：`seeds.sim_seed_for` 与之一致；`tests` 覆盖 `shared_across_conditions` / `audit_fresh` / `repetitions_differ`。理由充分。
- 状态：**PROPOSED，未经用户批准**。正式前需人工 GO。

### 5.2 D5 — tie-break 细节（PROPOSED，待批准）
- WideExplore：`(-delta_both, first_seen, anchor_id)`（任务书已给）。
- VerifyFirst 选 20：`(-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id)`（任务书未指定两单因素顺序 / 方向，PROPOSED 取 gap 先于 speed、均降序）。
- VerifyFirst 最终提名：`(-mean_delta_both, -valid_n, first_seen, anchor_id)`。
- 审查：`methods.py` 实现一致，`select_top` 确定性。理由合理；但 **`valid_n` 权重可能与"先看效应量"直觉冲突**（D10-2），需人工确认。
- 状态：**PROPOSED，未经用户批准**。

### 5.3 D6 — pilot 结构缩放（PROPOSED，已用于 pilot）
- 每方法 120 episodes：WideExplore 15 disc + 3 提名 ×5 audit；VerifyFirst 6 stage1 + 3 选 ×3 追加 + 3 提名 ×5 audit。精确闭合 240。
- 审查：`methods.py` / `configs/dev_v01.json` 一致；`run_pilot` 强制计划精确闭合（否则 `RuntimeError`）。
- 状态：用于 pilot 已验证（有效 240/240）。仅作描述性 / 管道验证，**对正式 800/800 冻结设计无直接影响**。
- 已知限制（D10-3）：pilot 每个提名仅审计 5 quartet（远小于正式 20），pilot audit 结论**不得外推为正式结论**（已在报告边界声明落实）。

### 5.4 D11 — 阶段隔离修复 + **跨 master_seed 隔离（关键缺陷）**
- **D11 修复（已确认正确且必要）**：`_index_completed` / `_note_outcome` 加入
  `if launch.get("phase") != self.phase: return`，阻断 smoke↔pilot 误复用。回归测试 `TestPhaseIsolation` 通过。根因与处置见 `DECISION_LOG D11`。
- **但 D11 修复不充分于正式阶段（本审计新发现）**：
  - resume / `completed_quartets()` 的隔离键为 `(method, anchor_index, repetition, stream)`，**不含 `master_seed`**，也未按 `self.master_seed` 过滤。
  - 正式阶段 8 个 master seed **共享同一账本与同一 `phase="formal"`**。
  - **本审计用 FakeAdapter 复现证明**（脚本 `demo_masterseed_isolation.py`）：
    - seed A 完成 formal WideExplore anchor0/rep0/discovery（发起 4 episodes）；
    - seed B 以相同 `(method, anchor, rep, stream)` 调用 `execute_job` 时，`completed_quartets()` 返回 seed A 的 Y，**不再发起新 episode**（`launched_count` 仍为 4）。
    - → **跨 master_seed 隔离 BROKEN**。
  - **后果**：正式一旦跑完 seed0，后续 7 个 seed 的同名 `(method, anchor, rep, stream)` 键会被误判"已完成"并复用 seed0 结果；实际只会真正运行 **1 个 seed** 的数据，其余 7 个 seed 结果为复制，彻底破坏 8-seed 独立性，且 12,800 名义 episode 中真实唯一 episode 仅约 1,600。
  - `run_id` 虽作为 bucket 存在，但 `completed_quartets` 取最早 `run_id`，不提供跨 seed 保护。
- **审计结论**：D11 修复**不足以支撑正式多 seed**。正式前必须：
  1. 在隔离键与 `completed_quartets` / `_records_for` / `runs_completing_key` / 确定性重放中**加入 `master_seed`**（按 `self.master_seed` 过滤）；
  2. 新增回归测试 `TestMasterSeedIsolation`（A 完成后 B 对同一 key 必重新发起、不复用）；
  3. 人工复核跨 seed 断点恢复语义。

### 5.5 其他正式安全属性
| 属性 | 结论 | 证据 |
|---|---|---|
| 断点恢复（D7） | 具备（**但缺跨 seed 维度**，见 5.4） | `TestSmokeFlow.test_smoke_is_resumable_without_double_billing` 等 |
| 预算上限 | 具备 | `ledger.check_budget` 每 episode 前检查；`BudgetExhausted`；formal 强制 `--confirm --max-episodes 12800` 否则 `PermissionError` |
| 重复任务检测 | 具备 | 同 `episode_key` 不重复计费；不同 `run_id` 同 quartet（重放）分别计费（D8） |
| audit 数据隔离 | 具备 | 提名仅用 discovery 记录；audit 用 `stream="audit"` 全新 sim_seed，不反馈 nomination（`test_pilot_audit_isolation`） |
| 失败 / 中断记账 | 具备 | launch 即计费；error/interrupted 记 outcome 且 `ego_collision` 缺失保持缺失（不假设 0/1）；launch 无 outcome 仍计费、Y 缺失 |

**小结**：除 **跨 master_seed 隔离（5.4）** 外，正式安全属性均具备；该缺陷为正式**硬阻塞**。

---

## 6. 目前是否具备启动 formal 的充分技术与研究依据？

| 判定项 | 状态 | 说明 |
|---|---|---|
| 工程 / 代码就绪 | GO | 98 测试通过，adapter/ledger/doctor 17/17，smoke 24、pilot 240 有效 |
| 跨 master_seed 隔离 | **NO-GO** | D11 修复不充分（§5.4），硬阻塞 |
| 规则就绪（D4/D5/D6） | **NO-GO** | 仍为 PROPOSED，协议要求正式前人工 GO |
| 研究设计就绪 | **NO-GO** | 零碰撞样本提示低事件率 / 低功效风险，未做预注册功效检查（§4.5 / §7 BLOCKER-3） |
| 预算合规 | 历史偏离已记录 | pilot 已偏离 +220（PD-01，不可撤销；不影响本次 formal 技术判断，但须披露） |

**结论**：目前**不具备**充分依据启动 formal。技术与研究依据均存在未决硬项。

---

## 7. 最终建议：GO / NO-GO / BLOCKED

> **整体建议：BLOCKED（不启动 formal）**，直至以下三项全部解除：

- **BLOCKER-1（技术）**：修复 D11 跨 master_seed 隔离缺陷（隔离键加入 `master_seed` + 按 `self.master_seed` 过滤），并通过新增 `TestMasterSeedIsolation` 回归测试。
- **BLOCKER-2（合规）**：D4 / D5 / D6 PROPOSED 规则取得人工书面批准（尤其 D5 的 `valid_n` 权重，D10-2）。
- **BLOCKER-3（研究）**：人工裁决零碰撞 / 低事件率风险——预注册最低事件率或功效检查，或确认"零结果为可接受信息性结论"，或在必要时调整干预可检测性。

**非阻塞但必须披露**：pilot 预算偏离 +220（PD-01），在正式与最终报告中如实记录，不掩盖。

**工程本身可 GO**：98 测试通过、smoke 24、pilot 240 有效、真实 HighwayEnv 证据充分。

**明确**：本构建**不**启动 formal；待人工 GO 且上述 BLOCKER 解除后，运行
`python -m safefliplab doctor` 复核，再 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 8. 需人工批准的事项清单

1. 批准 / 驳回 **D4** sim_seed 完整映射（PROPOSED）。
2. 批准 / 驳回 **D5** tie-break（含两单因素顺序 / 方向）及 `valid_n` 在提名中的权重（D10-2）。
3. 确认 **D6** pilot 缩放仅作描述性验证（已知，影响有限）。
4. 裁决零碰撞 / 低事件率研究设计风险（**BLOCKER-3**）：是否预注册功效 / 最低事件率，或接受零结果，或调整干预。
5. 批准 **D11 跨 master_seed 隔离修复方案**与回归测试（**BLOCKER-1**），并确认跨 seed 断点恢复语义。
6. 对 pilot 预算偏离 **+220（PD-01）** 的知悉与处置确认（披露，不掩盖）。
7. 最终显式 **GO**：在 BLOCKER 解除后运行 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 9. 原始文件保全确认

**保留（未改动）的原始文件**：
- `runs/episode_ledger.csv`（528 行）、`runs/episode_ledger.csv.buggy_pilot_run1`（489 行 = smoke 24 + pilot 220）
- `runs/_buggy_pilot_run1/`（55 个 run 目录）
- `reports/*`（smoke_report.md / pilot_report.md / *_quartets.csv / figure_*.png / *_summary.json）
- `docs/*`（DECISION_LOG / PROGRESS / LATEST_HANDOFF / PROTOCOL_V01 / RELATED_WORK / PROVENANCE / ATTRIBUTION / OWNER_GUIDE）
- `configs/*`、`safefliplab/*`、`tests/*`、`runs/manifest_*.json`

**本次审计新增（非历史结果）**：
- `docs/FINAL_PRE_FORMAL_AUDIT.md`（本文件）
- `.workbuddy/audit_analysis.py`（只读取证脚本，0 真实 episode）
- `.workbuddy/demo_masterseed_isolation.py`（FakeAdapter 复现 D11 跨 seed 缺陷，0 真实 episode）

**声明**：本次审计未覆盖、清空、补跑或美化任何历史结果；所有真实 episode 计数均直接来自既有账本与原始记录。

---

## 附录 B：V02 修复更新（2026-10-12 接续轮，静态只读 + 代码修复）

> 本附录在**不修改 §0–§9 任何结论**的前提下，记录接续轮对 §5.4 所述硬阻塞的修复。
> 本轮授权范围：修复代码、补充单元测试、静态分析已有记录、修订文档。**未启动任何真实
> smoke / pilot / formal 仿真**，未发布 GitHub，未改动旧 CornerCaseLab。

### B.1 BLOCKER-1（跨 master_seed 隔离）已解除（代码 + 测试）

- 修复见 `safefliplab/experiments.py`（详见 `docs/DECISION_LOG.md D12`）：
  resume 隔离键由 4 元组升级为 **5 元组** `(master_seed, method, anchor_index, repetition, stream)`，
  `_index_completed` / `_note_outcome` 在既有 `phase` 过滤外新增 `master_seed` 过滤。
- 新增 `tests/test_experiments.py::TestMasterSeedIsolation`（**8 项**，全用 FakeAdapter，零真实 episode），
  覆盖：A 完成后 B 必须独立发起（跨 seed 隔离）、同 seed 合法恢复不重复计费、force 重跑、launch-only、
  error、不同 run_id、预算耗尽。既有 `TestPhaseIsolation` 因键形变更同步更新。
- 单元测试 **98 → 106 全通过**（0 失败 0 错误，约 7.5 s，零真实 episode）。
- `python -m safefliplab doctor` 仍 **17/17 PASS，VERDICT: GO**；正式 CLI 锁
  （`--confirm` + `--max-episodes 12800` 才放行、之后仍 `RuntimeError` 不真跑）**未改动**。
- **结论**：§5.4 / §7 中的 BLOCKER-1 已通过代码与测试解除，待人工确认修复方案与回归测试后正式关闭。

### B.2 预算 / 记账口径复核（回应 §2 与 440/489 行差异）

- 活动账本 `runs/episode_ledger.csv` = **528 数据行** = 264 episodes（smoke 24 + 有效 pilot 240）。
- buggy 备份 `runs/episode_ledger.csv.buggy_pilot_run1` = **489 数据行** = 244 episodes
  （整本快照含 smoke 24 + buggy pilot 220）。本审计正文 §0 写"489 行"为含 smoke 的整本快照；
  而 `DECISION_LOG.md D11` 旧版与 `LATEST_HANDOFF` 旧版所写"440 行"仅统计 buggy pilot 自身
  （220 × 2），漏算同快照内 smoke 的 48 行——二者均为真实账本，差异纯属口径，无数据丢失/篡改。
  已统一更正各文档为：活动 528 / buggy 489。

### B.3 零碰撞 vs 无可见差异（静态分析，66 个完整 quartet）

仅从既有真实原始记录（`.workbuddy/phase2_analysis.py`，零真实 episode）分析：
- 66 个完整 quartet **全部零碰撞**；但 **100%（66/66）在 TTC / 奖励 / 轨迹哈希上存在条件差异**
  （TTC 差异 66/66、reward 差异 66/66、轨迹哈希差异 66/66、policy_steps 差异 21/66）。
- 干预应用正确率 **66/66**（front_gap+2.0、ego_speed−1.0 均正确施加，0 不一致）。
- **含义**："全部零碰撞" **不等于** "四条件完全没有可观察差异"。本实验在过程级指标上
  **能**检测干预效应；唯一无方差的是**碰撞主终点**本身。正式设计应据此预注册次要终点
  （TTC / 近撞）或接受零结果，详见 `docs/FORMAL_READINESS_V02.md`。

### B.4 当前状态一览（接续轮末）

| 项 | 状态 |
|---|---|
| 工程 / 代码就绪 | GO（106 测试通过；smoke 24、pilot 240 有效） |
| 跨 master_seed 隔离（BLOCKER-1） | **已解除（待人工确认修复）** |
| D4 / D5 / D6 规则 | 仍 **PROPOSED，未经用户批准** |
| 零碰撞 / 低事件率研究风险（BLOCKER-3） | 仍待人工裁决（建议预注册次要终点） |
| PD-01（pilot 累计 460，超 220） | 已披露、保留于总账、不掩盖 |
| 正式不可启动保护 | 保留（`cmd_formal` 锁未改动） |
| 是否启动 formal | **否**（本构建不执行；待人工 GO + BLOCKER 解除） |

> 完整就绪评估见 `docs/FORMAL_READINESS_V02.md`。

---

## 附录 C｜2026-10-12 本轮（V03）增量：调度补齐与安全加固

依独立源码审查，本轮完成 D13–D16（详见 `docs/DECISION_LOG.md`），全部静态 + FakeAdapter 单测、
**零真实 episode**。本附录只增量记录，不改写任何历史结论或数据。

### C.1 本轮修复与证据

| 项 | 问题 | 修复（源码证据） |
|---|---|---|
| Formal 完整调度（D14） | `run_formal_phase` 只创建首个 seed 驱动器，未实现 8×2×800 | `experiments.py::_execute_formal_phase` 补齐；CLI 锁（`run_formal`）仍抛 `RuntimeError` |
| 预算判别（D14） | `after−before==800` 在合法恢复时误报 | 改为 **`method×master_seed` 累计预算=800** 判据 + 单记 `new_episodes_this_call` |
| audit 混流（D14） | `audit_results` 误读 discovery 流 | `_records_for(..., stream=...)` 过滤；audit 只聚合 audit 流 |
| pilot 汇总（D14） | 用子驱动器运行前的过期账本 | `run_pilot` 汇总改用重开的持久化账本 |
| 账本原子性（D13） | `check_budget`+`record_launch` 非原子，可绕过上限 | `ledger.py::reserve_launch` 单锁内完成检查+去重+计费 |
| 重复计费（D13） | 同 key 可重复启动而只计费一次 | `DuplicateLaunch` 在仿真前拒绝（`force` 用新 run_id 另计） |
| 空数据行（D13） | 新账本写一整行全空数据行 | 仅写表头；`empty_data_rows()/diagnose()` 兼容核对；历史账本不改写 |
| 作用域计费（D13） | formal 8 seed 争抢 phase 总上限 | `budget_scope` 列 + `launched_count_scope()`，scope=`formal\|method\|seed` |
| 正式执行越权（D15） | `_execute_formal_phase` 可直调且 `adapter=None` 会用真实仿真器 | `_require_formal_go`：无 `human_go=True` 时非测试替身在构造仿真器**前**抛 `PermissionError` |
| 配置漂移（D16） | 误改预算/种子/节奏可悄悄进入正式 | `protocol.py::validate_formal_config`：数量/唯一性/冻结值/顺序/协议指纹 + budget/plan/simulator |

### C.2 测试与状态（本轮末）

- **新增/修正测试**：`tests/test_formal_config.py`（20）、`tests/test_formal_scheduling.py`（11）、
  `tests/test_ledger_safety.py`（9）；合计 **146 单测全通过**（0 失败 0 错误）。
- `doctor` **17/17 PASS，VERDICT: GO**；正式 CLI 锁**未解除**（`formal` 仍抛 `RuntimeError`）。
- **未做**：未启动任何真实 smoke/pilot/formal；未发布 GitHub；未改旧 CornerCaseLab；
  未修改 `configs/formal_v01.json`；未改动任何历史 episode / 账本 / 报告。

### C.3 BLOCKER 一览（本轮末）

| BLOCKER | 类别 | 状态 |
|---|---|---|
| BLOCKER-1 跨 master_seed 隔离 | 技术 | D12 已修复 + 本轮 D13–D16 加固；**待人工复核后关闭** |
| BLOCKER-2 D4/D5/D6 批准 | 合规 | **未解除**（仍 PROPOSED） |
| BLOCKER-3 零碰撞/低事件率 | 研究 | **未解除**（待人工裁决，建议预注册次要终点） |

> 完整就绪评估见 `docs/FORMAL_READINESS_V03.md`。
