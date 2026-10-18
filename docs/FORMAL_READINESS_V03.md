# SafeFlipLab — 正式实验就绪评估 V03（FORMAL_READINESS_V03）

> 生成时间：2026-10-12（GMT+8），按用户"正式实验前工程修复"轮生成。
> 本轮授权范围（用户明确约束）：**修复代码、补充单元测试、静态分析已有实验记录、修订文档**。
> **绝对禁止启动任何新的真实 HighwayEnv episode**（含 smoke / pilot / formal / 任何性能测试名义）。
> 本文档及其引用的一切测试均使用 `FakeAdapter` 或不启动真实 episode 的静态检查；
> 所有真实 episode 计数直接来自既有账本与原始记录。
> **本文件不构成对 formal 的 GO 授权**；formal 仍被 CLI 锁 + 独立安全门双重拒绝执行，待人工 GO。

---

## 0. 本轮工作摘要（与 V02 的关系）

V02（`docs/FORMAL_READINESS_V02.md`）解决了 BLOCKER-1 的**第一阶段**（跨 `master_seed` 隔离），
但独立源码审查发现 V02 之后仍存在一批**工程实现缺口**与**安全/合规缺口**：

1. **Formal 调度未真正实现**：`run_formal_phase` 只创建首个 seed 的驱动器，`run_formal` 恒抛
   `RuntimeError`，8 seed × 2 method × 800 的完整执行**并不存在**。
2. **预算判别会在合法恢复时误报**：以 `after − before == 800` 验证，合法半程/全程恢复时增量 < 800。
3. **账本非原子 / 可绕过上限 / 可重复计费 / 有空数据行**。
4. **正式执行可越权**：`_execute_formal_phase` 可直调，`adapter=None` 会构造**真实**仿真器。
5. **结果记录缺陷**：`audit_results` 误读 discovery 流；`run_pilot` 汇总用过期账本；多 seed manifest 会互相覆盖。
6. **正式配置无冻结漂移校验**：误改预算/种子/节奏不会被拦截。

本轮在**不运行任何真实仿真**的前提下完成上述全部修复（记为 D13–D16），并补齐三条用户额外核查项。
本文件逐项给出**源码证据、测试证据、通过数、尚存阻塞与正式实施状态**。

---

## 1. 已核实的工程状态（本轮末）

| 维度 | 状态 | 证据 |
|---|---|---|
| 运行环境 | Python 3.13.12 托管版 venv；cornercaselab 0.3.0、highway-env 1.10.2、gymnasium 1.2.2 | `python -m safefliplab doctor` → **17/17 PASS, VERDICT: GO** |
| 单元测试 | **146 passed / 0 failed / 0 error**（较 V02 的 106 净增 40，零真实 episode） | `python -m unittest discover -s tests` |
| smoke 真实实验 | 24/24 完成，0 错误 0 中断（历史，未重跑） | 活动账本 + 报告 |
| pilot 真实实验（有效） | 240/240 完成，0 错误 0 中断（历史，未重跑） | 活动账本 + 报告 |
| formal 调度器 | **完整实现**（`_execute_formal_phase`），**未执行** | `safefliplab/experiments.py` |
| formal CLI 锁 | **保留**（`formal` 仍抛 `RuntimeError`） | 实跑：`REFUSED: ... NOT executed by this build` |
| 正式执行安全门 | **新增**（`_require_formal_go`） | 测试 `test_execute_formal_phase_refuses_real_adapter_without_go` |
| 配置冻结校验 | **新增**（`protocol.py`） | 测试 `tests/test_formal_config.py`（20 项） |
| 旧 CornerCaseLab | 未改动 | D1 |
| GitHub 发布 | 未执行 | — |
| 真实 episode（本轮） | **0**（全部为静态 + FakeAdapter 测试） | 账本未新增 formal 行 |

---

## 2. 修复了什么（逐项 · 源码证据 · 测试证据）

### 2.1 任务一 — 补齐真正的 Formal 调度实现（D14）

- **源码证据**：新增 `safefliplab/experiments.py::_execute_formal_phase`，实现
  **8 master seeds × 2 methods**，每 `method×seed` **800 = 400 discovery + 400 audit**；
  提名在 audit 启动前冻结（audit 用 `stream="audit"`）；每 (seed, method) 独立 manifest；
  断点恢复不重复计费。
- **保留 CLI 安全锁**：`run_formal` / `run_formal_phase` **未改动**，仍先校验
  `--confirm` + `--max-episodes 12800`，随后**始终抛 `RuntimeError`**，不真正执行。
- **测试证据**：`tests/test_formal_scheduling.py`（11 项，全 `FakeAdapter`）覆盖多 seed 调度、
  分阶段预算、审计隔离、主种子隔离、断点恢复、重复启动、manifest 不覆盖、CLI 锁。

### 2.2 任务一附加 — 累计预算验证（用户额外核查 #1）

- **问题**：原以 `after − before == 800` 验证每次新增，**合法断点恢复时会误报**
  （半程恢复增量 < 800、全程恢复增量 = 0）。
- **源码证据**：`_execute_formal_phase` 改为读取**当前 `method × master_seed` 作用域的累计预算**
  （`launched_count_scope("formal|method|seed")`），判据为 **累计 == 800**；并**单独记录**
  本次新增次数 `new_episodes_this_call`（写入每 slice 与 `manifest_formal_combined.json`）。
  `_run_formal_method` 的守卫同样改用**累计**作用域计数。
- **边界**：`scope_after != FORMAL_BUDGET` → `RuntimeError`（防超支）；并校验
  `scope_before + new_this_call == scope_after`（防漏计）。
- **测试证据**：
  - `test_formal_full_resume_reports_zero_new_per_slice`：全部完成后再次调用，每 slice
    `new_episodes_this_call == 0` 且 `cumulative_episodes == 44`，累计总数仍为 176（不翻倍）；
  - `test_formal_halfway_resume_uses_cumulative_budget`：预完成 1 个 slice 后运行全调度，
    该 slice 记 0 新增、其余各 44，账本总数 176（**非 220**），每 scope 恰 44。

### 2.3 任务一附加 — 正式执行独立安全门（用户额外核查 #2）

- **问题**：`_execute_formal_phase` 可不经 CLI 直接调用，且 `adapter=None` 会构造**真实**
  `ScenarioAdapter`，存在绕过 CLI 锁启动真实 episode 的隐患。
- **源码证据**：新增 `safefliplab/experiments.py::_require_formal_go(adapter, human_go)`，
  在**所有正式执行入口**（`_execute_formal_phase`、`_run_formal_method`）**最先**调用：
  - `human_go=True`（显式人工 GO）→ 放行；
  - 否则适配器必须是显式**测试替身**（`is_test_double=True`，`FakeAdapter` 已加此标记）；
  - 其余情形（`adapter=None` 或非测试适配器）→ **在构造任何仿真器之前**抛 `PermissionError`。
- **测试证据**：`test_execute_formal_phase_refuses_real_adapter_without_go`：
  `adapter=None` 与 `is_test_double=False` 的伪适配器均被拒、且**零 episode 启动**；
  同文件其余 10 项测试证明 `FakeAdapter`（测试替身）路径**仍可**完整跑通（测试能力保留）。

### 2.4 任务一附加 — 正式配置冻结漂移校验（用户额外核查 #3）

- **源码证据**：新增 `safefliplab/protocol.py`：代码级冻结设计 `FROZEN_DESIGN` +
  `frozen_protocol_fingerprint()`；`validate_formal_config()` 一次列出**全部**问题：
  - **种子数量**（须 = `FORMAL_MASTER_SEED_COUNT`）；
  - **唯一性**（重复种子拒绝）；
  - 整型性（bool/float/str 拒绝）；
  - **冻结值 + 顺序**（须严格等于 SHA-256 派生列表 `seeds.formal_master_seeds()`）；
  - **协议指纹**（若 config 声明 `protocol_fingerprint`，须等于冻结指纹）；
  - protocol id、`boundary` 控制器、simulator 节奏、budget 与两方法计划冻结值。
  `_execute_formal_phase` 在**严格模式**强制该校验（缩放集成测试用 `strict_design=False` 仅放宽
  冻结设计比对，仍强制数量/唯一性/整型）。
- **未修改** `configs/formal_v01.json`（未新增字段）。
- **测试证据**：`tests/test_formal_config.py`（20 项）：真实配置合法且指纹匹配；重复/乱序/改值种子、
  改 budget/plan/simulator、错 protocol id、错控制器、指纹不匹配**均被拒**；非严格缩放模式仍强制
  数量/唯一性/整型。

### 2.5 任务二 — 账本安全与计费（D13）

| 子问题 | 源码证据（`safefliplab/ledger.py`） | 测试证据 |
|---|---|---|
| 多账本实例计数缓存不一致 | 每实例从 CSV 一次性重建计数（`_rebuild_counters`），CSV 为唯一权威 | `TestResumeReopensLedger`（重开账本验证计费） |
| `check_budget`+`record_launch` 非原子 | 新增 `reserve_launch`：预算检查+去重+计费**同一把锁**内完成；runner 改用之 | `test_reserve_honors_per_scope_independence`、`test_reserve_exhaustion_raises_within_scope` |
| 重复 episode_key 先启动后只计一次 | `DuplicateLaunch` 在**仿真前**拒绝同 scope 同 key；`force` 用新 run_id 另计 | `test_reserve_rejects_duplicate_key_before_sim` |
| 新账本写入额外全空数据行 | 仅写表头；`empty_data_rows()` / `diagnose()` 兼容核对；历史账本**不改写** | `test_fresh_ledger_has_header_only_no_empty_row`、`test_pre_fix_empty_row_ledger_reads_compat`、`test_legacy_activity_ledger_reads_compat` |
| formal 8 seed 争抢 phase 总上限 | `budget_scope` 列 + `launched_count_scope()`，scope=`formal\|method\|seed` | `test_reserve_honors_per_scope_independence` |

- **兼容**：旧行无 `budget_scope` 列时回退为 phase 作用域；活动账本计数不受空行/旧列影响。
- **历史账本**：`runs/episode_ledger.csv`（528 数据行）与
  `runs/episode_ledger.csv.buggy_pilot_run1`（489 数据行）**原样保留、未改写**。

### 2.6 任务三 — 研究结果记录修复（D14）

| 子问题 | 源码证据 | 测试证据 |
|---|---|---|
| `audit_results` 误读 discovery 数据 | `_records_for(..., stream=...)` 增加流过滤；`audit_results` 只聚合 `audit` 流 | `test_formal_audit_isolation_audit_stream_only`（valid_n=3，非 1+3）、`TestPilotFlow::test_pilot_audit_isolation` |
| pilot 汇总用过期账本 | `run_pilot` 汇总改用**重新打开的持久化账本** | `TestResumeReopensLedger::test_pilot_resume_reopens_ledger_and_no_repeat_calls` |
| 多主种子 manifest 互相覆盖 | `write_formal_manifest` 写 `manifest_formal_{method}_seed{seed}.json`（唯一路径） | `test_per_seed_method_manifests_do_not_overwrite`（4 个 seed/method manifest 全互异） |

### 2.7 任务四 — 测试补强

- **修复 smoke/pilot 恢复测试的陈旧账本漏检**：`TestResumeReopensLedger` **每次重新打开账本**
  校验实际计费，并断言 `FakeAdapter` **未被重复调用**（`len(adapter.calls)`）。
- **新增完整多种子 Formal 调度 / 分阶段预算 / 审计分离 / 故障中断 / 唯一运行 ID / 重复启动 /
  报告一致性**测试：见 `tests/test_formal_scheduling.py`、`tests/test_ledger_safety.py`、
  `tests/test_formal_config.py`。
- 全部测试仅用 `FakeAdapter` 或不启动真实 episode 的静态检查。

### 2.8 任务五 — 研究协议保护

- **PD-01 保留**：pilot 真实累计 **460**（220 无效 + 240 有效），**超上限 220**，全文如实披露，
  未掩盖、未重定义预算（详见 §5）。
- **D4/D5/D6 仍为 PROPOSED**，本构建**不代用户批准**（详见 §7）。
- **主终点保持 `ego_collision`**；TTC 等次要终点**仅提供预注册方案**，未擅自修改正式协议。
- **未修改** `PROTOCOL_V01`、`configs/formal_v01.json` 的科研规则内容；正式 CLI 锁与安全门保留。

---

## 3. 新增及通过的测试数量

| 测试文件 | 项数 | 内容 |
|---|---:|---|
| `tests/test_formal_config.py`（新增） | 20 | 真实配置冻结校验 + 各类漂移拒绝 + 缩放模式结构守卫 |
| `tests/test_formal_scheduling.py` | 11 | 多 seed 调度、分阶段/半程/全程恢复、累计预算、审计隔离、主种子隔离、重复启动、manifest、安全门、CLI 锁 |
| `tests/test_ledger_safety.py` | 9 | 原子预占、去重、作用域独立、空行修复与兼容、resume 重开账本 |
| `tests/test_experiments.py` | 含 `TestMasterSeedIsolation`(8) + `TestPhaseIsolation` 等 | 见 V02 |
| 其余既有套件 | — | domain/methods/stats/seeds/runner/ledger/report_cli |

- **单元测试：V02 的 106 → 本轮 146 全通过**（0 失败 0 错误）。
- 关键新增用例：`test_formal_halfway_resume_uses_cumulative_budget`、
  `test_formal_full_resume_reports_zero_new_per_slice`、
  `test_execute_formal_phase_refuses_real_adapter_without_go`、
  `test_full_scaled_formal_scheduling`、`test_per_seed_method_manifests_do_not_overwrite`、
  `test_reserve_rejects_duplicate_key_before_sim`、`test_fresh_ledger_has_header_only_no_empty_row`、
  以及 `tests/test_formal_config.py` 全部 20 项。

---

## 4. master_seed 隔离是否真正通过测试？预算恢复与实验独立性是否仍有问题？

### 4.1 master_seed 隔离
**是。** `TestMasterSeedIsolation::test_seed_b_must_launch_after_seed_a` 直接证明：seed A 完成某正式
quartet（4 episodes，写入共享账本）后，seed B（同 `phase="formal"`、同账本）对**相同
`(method, anchor_index, repetition, stream)` 键**执行 `execute_job` 时，`completed_quartets()` 不返回
A 的 Y，`launched_count` 由 4 增至 8（B 独立发起 4 个新 episode）。另有 7 项覆盖合法恢复不重复计费、
`force` 重跑、launch-only、error、不同 `run_id`、预算耗尽，均确认**无免费重试、无突破冻结预算**。
本轮 `test_master_seed_isolation_in_formal` 进一步在多 seed 全调度中验证各 seed 完成视图互斥。

### 4.2 预算恢复（resume）问题
- **法恢复误报**：已修复（§2.2），累计预算判据 + `new_episodes_this_call` 记录；
  半程/全程恢复测试均通过。
- **合法恢复重复计费**：无。重跑同一命令仅复用已完成 quartet、不新增 launch
  （`TestResumeReopensLedger` 重开账本核验计费 + `FakeAdapter` 未重复调用）。
- **免费重试 / 突破冻结预算**：无。`error` / 中断 / launch-only 均计费且不视为完成；
  `reserve_launch` 在预算耗尽时于首个 episode 前抛 `BudgetExhausted`，已计费不退还。

### 4.3 实验独立性问题
- **跨 phase**：D11 修复（既有 `phase` 过滤）。
- **跨 master_seed**：D12 修复（5 元组隔离键 + `master_seed` 过滤）。
- **跨 method / stream**：隔离键含 `method`、`stream`；audit 与 discovery 种子不同、
  且 `audit_results` 只读 audit 流。
- **跨 run_id**：不同 `run_id` 的同一 quartet key（确定性重放）**分别计费**（D8），
  且按 `run_id` 分桶、不混淆完成视图。
- **结论**：**未发现尚存的实验独立性问题**（在 FakeAdapter 集成测试层面）。

> **诚实边界**：以上均为**代码 / 单测层面**结论。真实 8-seed 独立性只在真正执行 formal 时才会被
> 物理验证；本轮不启动 formal，故不对真实运行下结论。

---

## 5. 全部真实 episode 预算总账（含首次无效运行，未删除）

> 本节与 V02 §3 一致，**未因本轮而改变**（本轮零真实 episode）。

| 记录位置 | 阶段 | 发起 | 完成 | 错误 | 中断 | 计入有效证据? | 备注 |
|---|---|---:|---:|---:|---:|---|---|
| `runs/episode_ledger.csv`（活动） | smoke | 24 | 24 | 0 | 0 | 是 | 用满 24 上限 |
| `runs/episode_ledger.csv.buggy_pilot_run1` | pilot（首次，含 D11 bug） | 220 | 220 | 0 | 0 | **否** | 无效，隔离备份，排除出证据 |
| `runs/episode_ledger.csv`（活动） | pilot（修复后重跑） | 240 | 240 | 0 | 0 | 是 | 有效 pilot，用满 240 上限 |
| `runs/episode_ledger.csv`（活动） | formal | 0 | 0 | 0 | 0 | — | 未执行（协议禁止） |

- **pilot 真实累计**：220（无效）+ 240（有效）= **460** / 上限 240 → 偏离 **+220**（达上限 192%）。
- **全部阶段真实发起合计**：24 + 460 = **484** episodes。
- **行数口径**：活动账本 **528** 数据行（264 episodes）；buggy 备份 **489** 数据行（244 episodes：
  整本快照含 smoke 24 + buggy pilot 220）。旧文档"440"仅统计 buggy pilot 自身 220×2，已更正。
- **⚠️ PROTOCOL DEVIATION PD-01（保留，不掩盖）**：
  - 原因：首次 pilot 因 D11 阶段隔离 bug 无效，必须丢弃重跑；修复后重跑再发起 240。
  - **是否取得额外授权**：**否**——既有授权仅覆盖"pilot ≤240"单次运行，未覆盖"因 bug 重跑累计 460"。
  - 影响：有效 pilot 为干净 240/240 重跑，科学有效性未受损；但累计超支 220 属**程序/合规偏离**。
  - 处置：保留全部原始文件；不覆盖/不清空/不补跑/不美化；**不得事后重定义预算掩盖偏离**。
  - 结论：PD-01 仍为**未决合规事件**，须在正式与最终报告中如实披露。

---

## 6. 零碰撞的研究风险与 GO/NO-GO 条件

> 沿用 V02 §6 的六点核查（真实 HighwayEnv 记录核验）与本轮结论。

1. `ego_collision` 来自**真实** HighwayEnv（抽查 12/12 一致；smoke 确定性重放一致）。✅
2. `front_gap+2.0` / `ego_speed−1.0` 真实改变场景（12/12 正确，3/3 quartet 仅两字段不同）。✅
3. 四条件共享同一 `sim_seed`（`inconsistent_sim_seed_keys=0`）。✅
4. `boundary` 控制器与适配正确（12/12 `controller_policy=boundary`）。✅
5. 全部零碰撞 → 在 dev_seed 样本下无法检测碰撞方差（预期描述性结果）；真正担忧在**设计层面**
   （低事件率 → 低功效）。⚠️
6. **"全零碰撞" ≠ "四条件无可见差异"**：基于既有真实记录的只读分析（66 个完整 quartet）——
   66/66 全部零碰撞，但 **100%（66/66）在过程级指标上仍可观察条件差异**（TTC 66/66、reward 66/66、
   轨迹哈希 66/66、`policy_steps` 21/66），干预应用正确率 66/66。**含义**：本实验在过程级指标上
   **能**检测干预效应；唯一无方差的是**碰撞主终点**本身。

**GO/NO-GO 条件（对照原始任务书）**：
- 未触发任务书所列的**接口/技术失败**类 GO/NO-GO 停止条件（doctor 17/17 GO；无接口错误）。
- 未触发任务书所列的"**无效实验立即安全停止**"条件（本轮零真实 episode）。
- **研究设计层面**的 NO-GO 风险仍在：零碰撞 → 碰撞主终点**低功效**；须由人工裁决（见 §8 BLOCKER-3）。

---

## 7. D4 / D5 / D6 的建议与未批准状态

> **三项均为 PROPOSED，未经用户批准；本构建不代表用户批准任何一项。正式前必须逐项取得书面批准。**

- **D4（sim_seed 映射）**：审查结论**健全**——实现 `seeds.sim_seed_for` 与该规则一致；含 `method`
  与 `stream`、不含条件代码（四条件共享）、含 `repetition`；8 个 formal seed 由
  `SHA256(canonical_json(["SafeFlipLab-v01","formal-master",i]))` 派生，**稳定、确定、独立、非结果挑选**
  （本轮 `test_formal_config.py::test_real_config_is_valid_and_frozen` 复算确认与 config 完全一致）。
  **建议**：可批准，仅需人工书面确认。
- **D5（tie-break）**：WideExplore 提名 `(-delta_both, first_seen, anchor_id)`（任务书已给）；
  VerifyFirst 选 20 `(-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id)`（PROPOSED）；
  最终提名 `(-mean_delta_both, -valid_n, first_seen, anchor_id)`（PROPOSED）。
  **边界情形**：零有效样本 → `select_top` 仅保留 `valid_n>0`，无合格锚则抛 `MethodError`（不提名）——
  **建议预注册**"0 合格锚"处理（报错中止 / 跳过 / 报告缺失）；部分无效 quartet 仅累积完整 quartet；
  并列由 `anchor_id` 最终确定性打破；缺失观察排除出分子分母。**建议预注册** `valid_n` 的权重
  （主键 or 辅助键）及其与 `mean_delta_both` 的优先级（D10-2）。
- **D6（pilot 缩放）**：每方法 120（WideExplore 15+3×5；VerifyFirst 6+3×3+3×5），精确闭合 240，
  **仅描述性**。**重要边界**：D6 **不追溯性声称**原始授权已覆盖 PD-01 历史超支——+220 是 buggy
  重跑造成的程序偏离，与 D6 结构无关，不得用 D6 为超支背书。`run_pilot` 强制计划精确闭合（否则 `RuntimeError`）。

---

## 8. 尚未解除的 BLOCKER

| BLOCKER | 类别 | 状态 | 解除条件 |
|---|---|---|---|
| BLOCKER-1 跨 master_seed 隔离 | 技术 | V02 D12 修复 + 本轮 D13–D16 加固；**待人工复核后关闭** | 用户审阅 D12–D16 与相关回归测试并确认 |
| BLOCKER-2 D4/D5/D6 批准 | 合规 | **未解除**（PROPOSED） | 用户书面批准三项规则（含 D5 边界与 `valid_n` 权重） |
| BLOCKER-3 零碰撞/低事件率研究风险 | 研究 | **未解除** | 用户裁决（预注册次要终点 / 接受零结果 / 调整干预可检测性） |

**非阻塞但必须披露**：PD-01（pilot 超支 +220）。

---

## 9. 正式实验的实施状态

- **代码层面**：正式调度器**已完整实现**（`_execute_formal_phase`），并通过 FakeAdapter 集成测试
  （多次重复运行结果一致、恢复正确、预算正确、审计隔离正确、主种子隔离正确）。
- **可执行性**：**被双重保护拒绝执行**：
  1. **CLI 锁**：`python -m safefliplab formal --confirm --max-episodes 12800` → `RuntimeError`（本轮实跑确认）；
  2. **独立安全门**：任何直接调用 `_execute_formal_phase` 且未传 `human_go=True`、适配器又非测试替身的代码，
     在构造任何仿真器前抛 `PermissionError`。
- **本轮真实 episode**：**0**；`runs/episode_ledger.csv` 未新增任何 formal 行。
- **是否具备启动 formal 的充分依据**：**否**（工程就绪，但 BLOCKER-2、BLOCKER-3 未解除）。

---

## 10. 最终建议：GO / NO-GO / BLOCKED

> **整体建议：BLOCKED（不启动 formal）**，直至以下三项全部解除：

- **BLOCKER-1（技术）**：D12 + D13–D16 已完成并测试通过；**待人工复核后关闭**。
- **BLOCKER-2（合规）**：D4 / D5 / D6 PROPOSED 规则取得人工书面批准。
- **BLOCKER-3（研究）**：人工裁决零碰撞 / 低事件率风险——基于 §6(6) 的"过程级指标可检测、
  仅碰撞主终点无方差"发现，建议**预注册碰撞率之外的次要终点**（TTC / 近撞 / 最小间距），
  或确认"零结果为可接受的信息性结论"，或在必要时调整干预可检测性。

**工程本身可 GO**；但 formal 启动仍需：人工 GO + 上述 BLOCKER 解除后，先 `python -m safefliplab doctor`
复核，再 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 11. 需要人工批准 / 审核的全部事项

1. 批准 / 驳回 **D4** sim_seed 完整映射（审查结论：健全，建议批准）。
2. 批准 / 驳回 **D5** tie-break（含两单因素顺序/方向）及 `valid_n` 在提名中的权重（D10-2）；
   并预注册"0 合格锚"时的处理策略。
3. 确认 **D6** pilot 缩放仅作描述性验证，且**不追溯性声称**已覆盖 PD-01 历史超支。
4. 裁决零碰撞 / 低事件率研究设计风险（**BLOCKER-3**）：是否预注册功效 / 最低事件率，或接受零结果，
   或调整干预；建议把 TTC / 近撞等次要终点纳入预注册。
5. 审阅并确认 **D12（跨 master_seed 隔离）** 与 **D13–D16（账本原子性 / 累计预算 / 安全门 /
   配置冻结校验）** 的修复方案与回归测试（**BLOCKER-1**）。
6. 对 pilot 预算偏离 **+220（PD-01）** 的知悉与处置确认（披露，不掩盖）。
7. 确认正式执行的双层保护（CLI 锁 + `_require_formal_go`）符合研究治理要求。
8. 最终显式 **GO**：在 BLOCKER 解除后运行 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 12. 人工审核前还需要什么（本构建已提供 / 待用户补充）

- ✅ 已提供：完整正式调度器（8 seed × 2 method × 800）与其 FakeAdapter 集成测试；
- ✅ 已提供：累计预算验证 + 半程/全程恢复测试（证明合法恢复不误报、不超支）；
- ✅ 已提供：正式执行独立安全门（未获人工 GO 不得启动真实 episode）与其拒绝路径测试；
- ✅ 已提供：`protocol.py` 配置冻结漂移校验（数量/唯一性/冻结值/顺序/协议指纹）与 20 项测试；
- ✅ 已提供：账本原子预占 / 去重 / 空行修复 / 作用域计费 + 9 项测试；
- ✅ 已提供：只读分析证据（`.workbuddy/phase2_analysis.py` 等，零真实 episode）；
- ✅ 已提供：统一后的文档（DECISION_LOG D13–D16 / PROGRESS / LATEST_HANDOFF / OWNER_GUIDE /
  FINAL_PRE_FORMAL_AUDIT 附录 C）；
- ⏳ 待用户：逐项审批 D4/D5/D6、裁决 BLOCKER-3、复核 D12–D16 与 PD-01；
- ⏳ 待用户：决定是否将次要终点（TTC / 近撞）写入 `PROTOCOL_V01` 的预注册分析计划。

---

## 13. 原始文件保全声明

**保留（未改写）的原始文件**：
- `runs/episode_ledger.csv`（528 数据行）、`runs/episode_ledger.csv.buggy_pilot_run1`（489 数据行）；
- `runs/_buggy_pilot_run1/`（55 个 run 目录）、`runs/manifest_*.json`、`runs/<run_id>/` 原始 episode JSON；
- `reports/*`（smoke_report.md / pilot_report.md / *_quartets.csv / figure_*.png / *_summary.json）；
- `configs/formal_v01.json`（**本轮未修改**）、`configs/dev_v01.json`；
- `docs/PROTOCOL_V01.md` 等科研规则原文。

**本轮新增 / 修改（非历史结果）**：
- 新增 `safefliplab/protocol.py`（冻结设计 + 配置漂移校验）；
- 修改 `safefliplab/experiments.py`（`_execute_formal_phase` 完整调度、累计预算、`_require_formal_go`、
  流隔离修复、pilot 汇总修复、`write_formal_manifest`）；
- 修改 `safefliplab/ledger.py`（`reserve_launch` / `DuplicateLaunch` / `budget_scope` /
  `empty_data_rows` / `diagnose` / 表头-only 初始化）；
- 修改 `safefliplab/runner.py`（改用 `reserve_launch` 并透传 `budget_scope`）；
- 修改 `tests/fakes.py`（`FakeAdapter.is_test_double=True`）；
- 新增测试 `tests/test_ledger_safety.py`、`tests/test_formal_scheduling.py`、`tests/test_formal_config.py`；
- 修订 `docs/DECISION_LOG.md`（D13–D16）、`docs/PROGRESS.md`、`docs/LATEST_HANDOFF.md`、
  `docs/OWNER_GUIDE.zh-CN.md`、`docs/FINAL_PRE_FORMAL_AUDIT.md`（附录 C）；
- 本文件 `docs/FORMAL_READINESS_V03.md`。

**声明**：本轮**未启动任何真实 smoke/pilot/formal episode**、**未发布 GitHub**、**未改动旧 CornerCaseLab**、
**未解除 formal 安全锁**；全部真实 episode 计数直接来自既有账本与原始记录；历史结果原样保留，
未覆盖、清空、补跑或美化。
