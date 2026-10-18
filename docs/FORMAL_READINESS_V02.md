# SafeFlipLab — 正式实验就绪评估 V02（FORMAL_READINESS_V02）

> 生成时间：2026-10-12（GMT+8），由 Hy3 在"代码修复与研究协议完善"轮生成。
> 本轮授权范围（用户明确约束）：**修复代码、补充单元测试、静态分析已有实验记录、修订文档**。
> **禁止启动任何新的真实 HighwayEnv episode**（含 smoke / pilot / formal / 任何性能测试名义）。
> 本文档及其引用的分析脚本均**未启动任何真实仿真**；所有真实 episode 计数直接来自既有账本与原始记录。
> 本文件**不构成对 formal 的 GO 授权**；formal 仍被代码锁拒绝执行，待人工 GO。

---

## 0. 本轮工作摘要（与上一轮 FINAL_PRE_FORMAL_AUDIT 的关系）

上一轮静态审计（`docs/FINAL_PRE_FORMAL_AUDIT.md`）发现并披露了三件事：
1. **PD-01**：pilot 真实累计 460 episodes，超协议上限 220；
2. **零碰撞风险**：264 个有效 episode 全部 `ego_collision=0`，提示低事件率 / 低功效风险；
3. **BLOCKER-1**：D11 相位隔离修复**不足以支撑正式多 seed**（缺 `master_seed` 维度）。

本轮在**不运行真实仿真**的前提下，完成了：
- **阶段一**：修复跨 `master_seed` 隔离缺陷（源码 + 8 项新单元测试）；
- **阶段二**：D4/D5/D6 研究设计预审 + 基于既有真实记录的"零碰撞 vs 无可见差异"分析；
- **阶段三**：统一文档与账本口径，保留 PD-01 与全部历史原始数据。

---

## 1. 已核实的工程状态

| 维度 | 状态 | 证据 |
|---|---|---|
| 运行环境 | Python 3.13.12 托管版 venv；cornercaselab 0.3.0、highway-env 1.10.2、gymnasium 1.2.2 | `doctor` 17/17 PASS |
| 包实现（A–E） | 完整 | `safefliplab/` 全部模块 |
| 单元测试 | **106 passed / 0 failed / 0 error**（本轮 +8，零真实 episode） | `python -m unittest discover -s tests` |
| smoke 真实实验 | 24/24 完成，0 错误 0 中断 | 活动账本 + 报告 |
| pilot 真实实验（有效） | 240/240 完成，0 错误 0 中断 | 活动账本 + 报告 |
| formal | **未执行**（协议禁止自动执行，且 CLI 锁保留） | `cli.py` / `experiments.run_formal` |
| 旧 CornerCaseLab | 未改动 | D1 |
| GitHub 发布 | 未执行 | — |

---

## 2. 阶段一：修复内容（源码证据）

### 2.1 问题根因（回顾）
`PhaseDriver` 的 resume 隔离键为 `(method, anchor_index, repetition, stream)`，**不含 `master_seed`**，
且 `completed_quartets()` / `_records_for` / `runs_completing_key` 未按 `self.master_seed` 过滤。
正式阶段 8 个 master seed **共享同一账本与同一 `phase="formal"`**，于是 seed A 完成某 quartet 后，
seed B…H 的 `execute_job` 会误把 A 的完成 quartet 当作"已完成"并复用其 Y，**不再发起真实 episode**——
真实唯一 episode 仅约 1/8，彻底破坏 8-seed 独立性。（详见上一轮 §5.4 / `DECISION_LOG D12`。）

### 2.2 实际修改（`safefliplab/experiments.py`）

**(a) `_index_completed` —— 新增 `master_seed` 过滤（叠加既有 `phase` 过滤）：**
```python
if launch.get("phase") != self.phase:
    return
if int(launch.get("master_seed")) != self.master_seed:   # <-- 新增：跨 seed 隔离
    return
key = (self.master_seed, launch["method"], int(launch["anchor_index"]),
       int(launch["repetition"]), launch["stream"])      # <-- 5 元组键
```

**(b) `_note_outcome` —— 同样的 `master_seed` 过滤：**
```python
if launch_row.get("phase") != self.phase:
    return
if int(launch_row.get("master_seed")) != self.master_seed:  # <-- 新增
    return
```

**(c) `execute_job` —— 查询键升级为 5 元组：**
```python
key = (self.master_seed, job.method, job.anchor_index, job.repetition, job.stream)
```

**(d) `_records_for` —— 迭代键与过滤同步升级：**
```python
for (ms, method, anchor_index, repetition, stream), y in self.completed_quartets().items():
    if ms != self.master_seed:
        continue
    ...
```

**(e) `PhaseReport.quartets` 类型与 `to_dict`、`runs_completing_key` 调用键、`completed_quartets` 文档
同步改为 5 元组**；`run_smoke` 确定性重放的 `runs_completing_key` 调用键同步改为
`(self.master_seed, METHOD_WIDE, 0, 0, STREAM_DISCOVERY)`。

**(f) 未改动**：`doctor`、`ledger`、`runner` 的计费逻辑，以及正式 CLI 锁
（`cmd_formal` 仍须 `--confirm` + `--max-episodes 12800` 才放行，之后仍抛 `RuntimeError` 不真跑）。
正式不可启动保护**完整保留**。

### 2.3 新增及通过的测试

新增 `tests/test_experiments.py::TestMasterSeedIsolation`（**8 项，全部 FakeAdapter，零真实 episode**）：
- `test_seed_b_must_launch_after_seed_a` —— A 完成后，B 必须独立发起自己的 quartet，不得复用 A 的 Y（**核心跨 seed 隔离**）；
- `test_seed_b_legal_resume_no_double_billing` —— 同一 seed 的合法恢复复用已完成 quartet，不重复发起、不重复计费；
- `test_force_reruns_and_bills_again` —— `force=True` 是显式重跑，必须重新计费；
- `test_launch_only_quartet_not_reused_and_re_run_bills_again` —— 仅 launch 无 outcome（中断）已计费但不视为完成，重跑重新计费（无免费重试）；
- `test_error_quartet_billed_and_re_run_costs_again` —— 错误 quartet 已计费且不完整，重跑重新计费（无免费重试）；
- `test_two_seeds_have_mutually_exclusive_completed_views` —— 两 seed 的完成视图互斥；
- `test_formal_budget_exhaustion_blocks_extra_launch_without_free_retry` —— 预算耗尽后首 episode 前即 `BudgetExhausted`，已计费不退还；
- `test_different_run_id_same_key_billed_separately` —— 同 seed/键两次运行（smoke 确定性重放）分别计费、两个 run_id 均入账（D8）。

既有 `TestPhaseIsolation` 因键形变更同步更新为 5 元组断言（1 项）。

**测试结果**：单元测试 **98（上一轮）→ 106 全通过**（0 失败 0 错误，约 7.5 s，零真实 episode）；
`python -m safefliplab doctor` 仍 **17/17 PASS，VERDICT: GO**。

### 2.4 master_seed 隔离是否真正通过测试？

**是。** `test_seed_b_must_launch_after_seed_a` 直接证明：seed A 完成某正式 quartet（4 episodes，写入共享账本）
后，seed B（同 `phase="formal"`、同账本）对**相同 `(method, anchor_index, repetition, stream)` 键**调用
`execute_job` 时，`completed_quartets()` 不返回 A 的 Y，`launched_count` 由 4 增至 8（B 独立发起 4 个新
episode）。其余 7 项分别覆盖合法恢复不重复计费、force 重跑、launch-only、error、不同 run_id、预算耗尽等恢复路径，
均确认**无免费重试、无突破冻结预算**。

---

## 3. 全部真实 episode 预算总账（含首次无效运行，未删除）

### 3.1 总账汇总（按阶段 / 运行尝试）

| 记录位置 | 阶段 | 发起 | 完成 | 错误 | 中断 | 计入有效证据? | 备注 |
|---|---|---:|---:|---:|---:|---|---|
| `runs/episode_ledger.csv`（活动） | smoke | 24 | 24 | 0 | 0 | 是 | 已验收，用满 24 上限 |
| `runs/episode_ledger.csv.buggy_pilot_run1` | pilot（首次，含 D11 bug） | 220 | 220 | 0 | 0 | **否** | 无效，隔离备份，排除出证据 |
| `runs/episode_ledger.csv`（活动） | pilot（修复后重跑） | 240 | 240 | 0 | 0 | 是 | 有效 pilot，用满 240 上限 |
| `runs/episode_ledger.csv`（活动） | formal | 0 | 0 | 0 | 0 | — | 未执行（协议禁止） |

### 3.2 跨阶段真实消耗（含被排除证据的运行）

- **smoke**：24 / 上限 24 → 偏差 0。
- **pilot（累计真实发起）**：220（首次无效）+ 240（修复后）= **460** / 上限 240 → 偏差 **+220**（达上限 192%）。
- **formal**：0 / 上限 12800 → 偏差 0（尚未启动）。
- **全部阶段真实发起合计**：24 + 460 = **484** episodes。
- 首次无效 220 已永久保留于 `runs/episode_ledger.csv.buggy_pilot_run1` 与 `runs/_buggy_pilot_run1/`
  （55 个 run 目录），**不从预算中删除**，符合"所有已发起 episode（含失败/中断/无效）计费"。

### 3.3 对账本行数口径差异（440 / 489 / 528）的说明

| 账本文件 | 数据行数 | 含义 | 口径 |
|---|---:|---|---|
| `runs/episode_ledger.csv`（活动） | **528** | 264 episodes（smoke 24 + 有效 pilot 240） | 当前权威账本 |
| `runs/episode_ledger.csv.buggy_pilot_run1` | **489** | 244 episodes（整本快照：smoke 24 + buggy pilot 220） | 首次无效运行留痕 |
| （旧文档所写）"440 行" | 440 | 仅 buggy pilot 自身 220 × 2 | 旧版漏算同快照内 smoke 48 行 |

三者均为真实账本，**差异纯属"是否含 smoke 行 / 是否含表头"的口径**，不存在数据丢失或篡改。
本轮已统一更正 `DECISION_LOG D11`、`LATEST_HANDOFF`、`FINAL_PRE_FORMAL_AUDIT` 中的行数表述。

### 3.4 ⚠️ PROTOCOL DEVIATION — PD-01（保留，不掩盖）

- **标题**：pilot 阶段真实累计发起 **460** episodes，超协议上限 **240**，偏离 **+220**。
- **原因**：首次 pilot 因 D11 阶段隔离 bug 无效，必须丢弃重跑；修复后重跑又发起 240。两次累计 460。
- **是否取得额外授权**：**否**。既有授权仅覆盖"pilot ≤240"的单次运行，未覆盖"因 bug 重跑而累计 460"。
- **对研究有效性的影响**：有效 pilot 为干净 240/240 重跑，科学有效性未受损；但累计预算超支 220 属程序 / 合规偏离。
- **处置**：保留全部原始文件；不覆盖 / 不清空 / 不补跑 / 不美化；**不得通过事后重新定义预算掩盖偏离**。
- **结论**：PD-01 仍为**未决合规事件**，须在正式与最终报告中如实披露。

---

## 4. 首次 pilot bug 的原因与协议影响

- **现象**：首次 `run_pilot` 实际只发起 220 episodes（应为 240），且 discovery 跳过了与 smoke 共享
  `(method, anchor_index, repetition, stream)` key 的前几个锚（WideExplore 0/1/2、VerifyFirst 0/1）。
- **根因（D11）**：`completed_quartets()` / `_records_for` 未按 `self.phase` 过滤，smoke 已完成 quartet
  被 pilot 的 resume 误认为"已完成"，跳过对应 discovery 锚、少跑 20 episodes。
- **协议影响**：该运行既未用满预算、也未测试应有锚集合 → **无效**。修复（按 phase 隔离）后重跑得到
  有效 240/240。首次 220 已隔离备份、**保留于真实预算消耗**（计入 PD-01 的 +220）。
- **本轮回看**：D11 修复虽解决了 smoke↔pilot 误复用，但**未覆盖跨 master_seed**——这正是本轮回填的 BLOCKER-1。

---

## 5. 有效 pilot 结果及其局限

- **规模**：240/240 完成，0 错误 0 中断；WideExplore 120 / VerifyFirst 120；discovery 120 / audit 120；
  WideExplore discovery 锚 0–14 全覆盖、VerifyFirst 0–5；提名（真实）各 3 个 × 5 audit。
- **碰撞**：全部 240 completed 的 `ego_collision=0`（dev_seed 样本下两种干预均未致本车碰撞）。
- **局限（必须如实陈述）**：
  1. **dev_seed 非证据**：pilot 为描述性 / 管道验证，结论不得外推到正式评估；
  2. **审计证据有限**：每个提名仅审计 5 个 quartet，远小于正式的 20（D10-3），pilot 的 audit 结论
     **不得**外推为正式结论；
  3. **零方差**：因全部零碰撞，`delta_both/gap/speed`、interaction、reverse、rescue 在该样本内全为 0，
     没有任何碰撞方差可供差异检测（见 §6）。

---

## 6. 零碰撞的六点核查（含关键新发现：零碰撞 ≠ 无可见差异）

> 样本：有效 smoke 24 + 有效 pilot 240 = 264 个 completed episodes，账本 `ego_collision` 全为 0。
> 本节 (1)–(5) 沿用上一轮核查结论（均从真实 HighwayEnv 记录核验）；(6) 为本轮**新增静态分析**。

1. **ego_collision 来自真实 HighwayEnv**：抽查 12/12 原始记录字段与账本一致；smoke 确定性重放
   `all_conditions_match=true`。✅
2. **front_gap+2.0 / ego_speed−1.0 真实改变场景**：12/12 正确，3/3 quartet 仅两字段不同。✅
3. **四条件共享同一 sim_seed**：账本 `inconsistent_sim_seed_keys = 0`，`stream` 区分 discovery/audit。✅
4. **boundary 控制器与适配正确**：12/12 原始记录 `controller_policy=boundary`，跨条件/方法/种子/阶段一致。✅
5. **全部零碰撞是否说明缺乏可检测风险差异**：在当前 dev_seed 样本下，确实无法检测碰撞方差；属预期描述性
   结果；但**真正的担忧在设计层面**（低事件率 → 低功效），协议未预注册最低事件率 / 功效检查。⚠️
6. **（本轮新增）"全部零碰撞" 是否等于 "四条件完全没有可观察差异"？** —— **否**。
   基于既有真实原始记录的只读分析（`.workbuddy/phase2_analysis.py`，零真实 episode，覆盖 66 个完整 quartet）：
   - 66/66 个 quartet 全部零碰撞；
   - **但 100%（66/66）在过程级指标上存在条件差异**：
     - TTC（`min_forward_ttc_sampled_s`）差异：66/66；
     - 奖励（`reward_sum`）差异：66/66；
     - 轨迹哈希（`trace_sha256_rounded_9dp`）差异：66/66；
     - 策略步数（`policy_steps`）差异：21/66；
   - 干预应用正确率 **66/66**（front_gap+2.0、ego_speed−1.0 均正确施加，0 不一致）。
   - **含义**：本实验在 TTC / 奖励 / 轨迹等过程级指标上**能够**检测干预效应；唯一无方差的是
     **碰撞主终点**本身。因此"全零碰撞"与"四条件无可见差异"不是一回事——前者是低事件率问题，
     后者才是实验无能力问题（本实验不存在后者）。

---

## 7. 阶段二：D4 / D5 / D6 详细审查（均为 PROPOSED，未经用户批准）

> 以下审查结论仅供建议；**D4/D5/D6 仍保持待人工批准状态，本构建不代表用户批准任何一项。**

### D4 — sim_seed 映射
- 规则：`sim_seed = SHA256([protocol,"seed",master_seed,"sim",method,stream,anchor_id,repetition])`；
  含 `method`、`stream`，**不含条件代码**（四条件共享）；含 `repetition`。
- 审查（静态）：实现 `seeds.sim_seed_for` 与之一致；8 个 formal master seed 由
  `SHA256(canonical_json(["SafeFlipLab-v01","formal-master",i]))` 派生，**稳定、确定、独立、非结果挑选**
  （本轮已复算确认与 `configs/formal_v01.json` 完全一致）。配对正确性经账本核验
  `inconsistent_sim_seed_keys=0`。
- **建议**：D4 设计健全，可批准；仅需人工最终书面确认。

### D5 — tie-break 细节
- WideExplore 提名：`(-delta_both, first_seen, anchor_id)`（任务书已给）。
- VerifyFirst 选 20：`(-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id)`（PROPOSED：gap 先于
  speed、均降序；任务书未指定两单因素顺序/方向）。
- VerifyFirst 最终提名：`(-mean_delta_both, -valid_n, first_seen, anchor_id)`（PROPOSED）。
- **边界情形处理**（实现已具备，需预注册确认）：
  - **零有效样本**：`select_top` 仅保留 `valid_n>0` 的记录；若某 seed 无合格锚 → 抛 `MethodError`（不提名）。
    **建议预注册**：明确"0 合格锚"时的处理（报错中止该 seed / 跳过该 seed / 报告缺失），避免正式运行中途崩溃。
  - **部分无效 quartet**：`AnchorRecord` 仅累积完整 quartet，缺失观察绝不当 0/1，均值只在完整 quartet 上计算。✅
  - **并列（ties）**：排序键含 `anchor_id` 作为最终确定性 tie-breaker → 全确定。✅
  - **缺失观察**：同上，缺口排除出分子分母，不虚构。✅
- **D10-2 关切**：`valid_n` 在最终提名中作为第二排序键，可能与"先看效应量"直觉冲突。
  **建议预注册**：明确 `valid_n` 是主排序键还是辅助键，以及其与 `mean_delta_both` 的相对优先级。

### D6 — pilot 结构缩放
- 每方法 120 episodes（WideExplore 15+3×5；VerifyFirst 6+3×3+3×5），精确闭合 240，仅作描述性验证。
- **审查**：`methods.py` / `configs/dev_v01.json` 一致；`run_pilot` 强制计划精确闭合（否则 `RuntimeError`）。
- **重要边界**：D6 是 **dev_seed 描述性**缩放，**不追溯性声称**原始授权已覆盖历史超支——PD-01 的 +220 是
  buggy 重跑造成的程序偏离，与 D6 的结构设计无关，不得用 D6 为超支背书。

### D4/D5/D6 未批准状态
**三项均为 PROPOSED，未经用户批准，正式前必须逐项取得书面批准。** 本构建不代用户批准。

---

## 8. 阶段三：文档与账本核对（一致性结论）

- **PD-01 保留**：pilot 实际累计 460、超 220，全文如实披露，未掩盖、未重定义预算。
- **行数口径统一**：活动账本 528 / buggy 备份 489（旧"440"已更正为 buggy-pilot-only 口径说明）。
- **测试数量一致**：所有文档已统一为 **106 passed**（98 原有 + 8 新增 `TestMasterSeedIsolation`）。
- **阻塞项一致**：BLOCKER-1 标记为"已修复待人工确认"；BLOCKER-2（D4/D5/D6）、BLOCKER-3（零碰撞研究风险）
  仍待人工裁决。
- **真实运行状态一致**：smoke 24/24、有效 pilot 240/240、formal 0，无任何补跑或重定义。
- **正式 CLI 安全锁**：`cmd_formal` 仍须 `--confirm` + `--max-episodes 12800` 才放行，之后仍抛
  `RuntimeError` 不真跑；**本轮未解除该保护**。
- **原始数据保全**：全部 episode、历史账本（活动 + buggy 备份）、报告、随机种子、审计记录**原样保留**，
  未覆盖、未清空、未补跑、未美化。

---

## 9. 是否具备启动 formal 的充分技术与研究依据？

| 判定项 | 状态 | 说明 |
|---|---|---|
| 工程 / 代码就绪 | **GO** | 106 测试通过；smoke 24、pilot 240 有效；doctor 17/17 |
| 跨 master_seed 隔离（BLOCKER-1） | **已修复，待人工确认** | D12 修复 + `TestMasterSeedIsolation` 8 项通过；工程层面已解除 |
| 规则就绪（D4/D5/D6） | **NO-GO** | 仍 PROPOSED，协议要求正式前人工 GO |
| 研究设计就绪（BLOCKER-3） | **NO-GO** | 零碰撞/低事件率风险未裁决；建议预注册次要终点（TTC/近撞） |
| 预算合规 | 历史偏离已记录 | PD-01 已披露（不可撤销；不影响技术判断，但须披露） |

**结论**：目前**仍不具备**充分依据启动 formal。工程与隔离缺陷已解决，但**规则批准**与**研究设计裁决**
两项硬条件未决。

---

## 10. 最终建议：GO / NO-GO / BLOCKED

> **整体建议：BLOCKED（不启动 formal）**，直至以下三项全部解除：

- **BLOCKER-1（技术，已修复待确认）**：跨 `master_seed` 隔离已通过 D12 修复 + `TestMasterSeedIsolation`
  回归测试解决；待人工确认修复方案与回归测试后正式关闭。
- **BLOCKER-2（合规）**：D4 / D5 / D6 PROPOSED 规则取得人工书面批准（尤其 D5 的 `valid_n` 权重、零合格锚处理）。
- **BLOCKER-3（研究）**：人工裁决零碰撞 / 低事件率风险——基于 §6(6) 的"过程级指标可检测、仅碰撞主终点无方差"
  发现，建议**预注册碰撞率之外的次要终点**（TTC / 近撞 / 最小间距），或确认"零结果为可接受的信息性结论"，
  或在必要时调整干预可检测性。

**非阻塞但必须披露**：PD-01（pilot 超支 +220）在正式与最终报告中如实记录，不掩盖。

**工程本身可 GO**；但 formal 启动仍需：人工 GO + 上述 BLOCKER 解除后，先 `python -m safefliplab doctor`
复核，再 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 11. 尚未解除的 BLOCKER 清单

| BLOCKER | 状态 | 解除条件 |
|---|---|---|
| BLOCKER-1 跨 master_seed 隔离 | 已代码修复 + 测试通过，**待人工确认** | 用户审阅 D12 修复与 `TestMasterSeedIsolation` 并确认 |
| BLOCKER-2 D4/D5/D6 批准 | 未批准（PROPOSED） | 用户书面批准三项规则 |
| BLOCKER-3 零碰撞/低事件率研究风险 | 未裁决 | 用户裁决研究设计（预注册次要终点 / 接受零结果 / 调整干预） |

---

## 12. 需要人工批准 / 审核的全部事项

1. 批准 / 驳回 **D4** sim_seed 完整映射（审查结论：健全，建议批准）。
2. 批准 / 驳回 **D5** tie-break（含两单因素顺序/方向）及 `valid_n` 在提名中的权重（D10-2）；
   并预注册"0 合格锚"时的处理策略。
3. 确认 **D6** pilot 缩放仅作描述性验证，且**不追溯性声称**已覆盖 PD-01 历史超支。
4. 裁决零碰撞 / 低事件率研究设计风险（**BLOCKER-3**）：是否预注册功效 / 最低事件率，或接受零结果，
   或调整干预；基于 §6(6) 建议把 TTC / 近撞等次要终点纳入预注册。
5. 确认 **D12 跨 master_seed 隔离修复方案**与 `TestMasterSeedIsolation` 回归测试（**BLOCKER-1**），
   并确认跨 seed 断点恢复语义。
6. 对 pilot 预算偏离 **+220（PD-01）** 的知悉与处置确认（披露，不掩盖）。
7. 最终显式 **GO**：在 BLOCKER 解除后运行 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 13. 人工审核前还需要什么（本构建已提供 / 待用户补充）

- ✅ 已提供：`TestMasterSeedIsolation` 8 项测试（证明跨 seed 隔离与恢复语义）；
- ✅ 已提供：`.workbuddy/phase2_analysis.py` 只读分析（66 quartet 的零碰撞 vs 可见差异证据）；
- ✅ 已提供：源码修复（`experiments.py` D12）+ 统一后的文档（DECISION_LOG / PROGRESS / LATEST_HANDOFF /
  OWNER_GUIDE / FINAL_PRE_FORMAL_AUDIT 附录 B）；
- ⏳ 待用户：逐项审批 D4/D5/D6、裁决 BLOCKER-3、确认 D12 与 PD-01；
- ⏳ 待用户：决定是否将次要终点（TTC / 近撞）写入 `PROTOCOL_V01` 的预注册分析计划。

---

## 14. 原始文件保全声明

**保留（未改动）的原始文件**：
- `runs/episode_ledger.csv`（528 数据行）、`runs/episode_ledger.csv.buggy_pilot_run1`（489 数据行）；
- `runs/_buggy_pilot_run1/`（55 个 run 目录）、`runs/manifest_*.json`；
- `reports/*`（smoke_report.md / pilot_report.md / *_quartets.csv / figure_*.png / *_summary.json）；
- `docs/*`（DECISION_LOG / PROGRESS / LATEST_HANDOFF / PROTOCOL_V01 / RELATED_WORK / PROVENANCE /
  ATTRIBUTION / OWNER_GUIDE / FINAL_PRE_FORMAL_AUDIT）；
- `configs/*`、`safefliplab/*`、`tests/*` 中既有内容。

**本轮新增 / 修改（非历史结果）**：
- 修改 `safefliplab/experiments.py`（D12 跨 seed 隔离修复）；
- 修改 `tests/test_experiments.py`（新增 `TestMasterSeedIsolation` 8 项 + 更新 `TestPhaseIsolation`）；
- 新增只读分析脚本 `.workbuddy/phase2_analysis.py`、`.workbuddy/audit_analysis.py`、`.workbuddy/demo_masterseed_isolation.py`；
- 修订 `docs/DECISION_LOG.md`（D12 + 行数口径）、`docs/PROGRESS.md`、`docs/LATEST_HANDOFF.md`、
  `docs/OWNER_GUIDE.zh-CN.md`、`docs/FINAL_PRE_FORMAL_AUDIT.md`（附录 B）；
- 本文件 `docs/FORMAL_READINESS_V02.md`。

**声明**：本轮**未启动任何真实 episode**、**未发布 GitHub**、**未改动旧 CornerCaseLab**、**未运行 formal**；
全部真实 episode 计数直接来自既有账本与原始记录；历史结果原样保留，未覆盖、清空、补跑或美化。
