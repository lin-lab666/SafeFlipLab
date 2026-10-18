# SafeFlipLab — 正式实验就绪评估 V04（FORMAL_READINESS_V04）

> 生成时间：2026-10-12（GMT+8），按用户"独立源码验收发现问题的定向修复"轮生成。
> 任务性质：**独立源码验收的定向修复**，**不是 formal 启动授权**。
> 本轮授权范围：**修复代码、补充/运行单元测试、静态分析既有记录、修订文档**。
> **绝对禁止启动任何新的真实 HighwayEnv episode**（smoke / pilot / formal / 任何性能测试名义均禁止）；
> **不解除 formal 安全锁；不发布 GitHub；不改动旧 CornerCaseLab；不改写历史结果。**
> 本文档引用的一切测试均使用 `FakeAdapter` 或不启动真实 episode 的静态检查。

---

## 0. 本轮摘要（与 V03 的关系）

V03（`docs/FORMAL_READINESS_V03.md`）补齐了正式调度器、累计预算、账本原子性、安全门与配置冻结校验。
随后**独立源码验收**用独立临时数据复现了**两个真实缺陷**（均在 `FakeAdapter` 之外、仅触及账本/报告）：

1. **`ledger.py` 多实例/多进程预算超额**：同一 CSV 上的两个 `EpisodeLedger` 实例（或两个进程）
   在作用域上限=1 时**各自**成功 `reserve_launch`，磁盘出现 2 次 launch。仅靠每实例自己的
   `threading.Lock` + 内存缓存**无法**跨实例/跨进程同步。
2. **`report.py` 正式报告错误合并主种子**：`load_phase_data` 分组缺 `master_seed` 与 `run_id`，
   2 主种子各 4 条完整条件记录只得到 **1** 个 quartet（应为 2）。

本轮在**不运行任何真实仿真**的前提下修复上述两项（记为 **D17 / D18**），并按用户要求加固
**研究规则冻结与实现一致性**及 `strict_design` 安全边界（记为 **D19**），补齐回归测试。

---

## 1. 复现证据（修复前 → 修复后，均为独立临时数据，零真实 episode）

### 缺陷一：账本多实例预算超额

```
# 修复前（两个独立 EpisodeLedger 实例，作用域上限=1，各自 reserve_launch）
BUG-1 both succeeded: True | launches on disk: 2      # ← 超额（应为 1）

# 修复后（同场景）
first ok: True | second refused: True | launches on disk: 1

# 修复后（跨进程：6 个独立进程竞争同一作用域上限=1）
P0: OK   P1..P5: REFUSED
OK count: 1 | launches on disk: 1
```

### 缺陷二：报告错误合并主种子

```
# 修复前（2 个 master_seed，各 4 条完整条件记录）
quartets found: 1 (expected 2)                        # ← 跨种子被混并

# 修复后
quartets: 2   seeds: [111, 222]
```

两项缺陷均已固化为回归测试（见 §3）。

---

## 2. 修复内容与源码证据

### 2.1 D17 — 账本跨实例/跨进程预算同步（`safefliplab/ledger.py`）

- **进程内共享锁**：新增模块级锁注册表 `_LOCK_REGISTRY` + `_process_lock_for(path)`，按**解析后的
  账本路径**返回同一把 `threading.Lock`。所有指向同一 CSV 的实例**共用同一把锁**，取代原先各自
  独立的 `threading.Lock`。
- **跨进程文件锁**：新增 `_exclusive_file_lock(lock_path, timeout_s)`，对 sidecar 文件
  `episode_ledger.csv.lock` 加 OS 级独占锁：
  - Windows：`msvcrt.locking(..., LK_NBLCK, 1)`（非阻塞 + 轮询重试，超时抛 `LedgerLockTimeout`）；
  - POSIX：`fcntl.flock(LOCK_EX)`。
  - **锁的是 sidecar 文件，绝不触碰账本 CSV**，故**不改写任何历史账本字节**。
- **锁内持久化核对（权威）**：新增 `_resync_from_disk()`：在锁内自 `_consumed_bytes` 起**增量**重读
  磁盘 CSV（只消费完整行，`\r\n` 安全，set 幂等），再以**磁盘权威状态**做预算与去重判断。
  `reserve_launch` 现为：`进程锁 + 文件锁 → 增量核对 → 预算检查 → 去重检查 → 原子追加`，
  全部在同一临界区内；`record_launch` / `record_outcome` 亦在锁内核对后追加。
- **失败即安全**：锁超时抛 `LedgerLockTimeout`（宁失败，不越权写入）。

**源码证据锚点**：`_process_lock_for`、`_exclusive_file_lock`、`_resync_from_disk`、
`_ingest_row`、`_reset_counters`、`reserve_launch`（锁内核对段）、`_append_rows_unlocked`、
`LedgerLockTimeout`。

### 2.2 D18 — 正式报告主种子 / run_id 隔离（`safefliplab/report.py`）

- **quartet 分组键升级**：`(master_seed, method, anchor_id, repetition, stream)` + **`run_id`**。
  四个条件必须来自**同一 run**（同一配对 `sim_seed`）；**禁止不同种子或不同 run 批次**的
  Y00/Y10/Y01/Y11 混并。原键 `(method, anchor_id, repetition, stream)` 已废弃。
- **重复运行单列**：同 key 的二次完整运行（如 smoke 确定性重放）记为 `replay_quartets`，
  `is_replay=True`，**排除出主统计**，明示"不作为额外独立科学证据"。
- **不完整 quartet 如实记录**：四条件未在同一 run 内全部完成的 key 进入 `incomplete`，
  逐 run 逐条件记录其状态（含 `error`/`interrupted`/`missing`），不计入分子分母。
- **完善正式报告**：新增
  - 每个 `master_seed × method` 的**独立结果**（discovery/audit 分别汇总）；
  - 每个 `master_seed × method` 的**独立审计结果**（audit 流，按提名 anchor）；
  - 两方法每主种子的 **paired contrast**（`mean_delta_both/gap/speed/interaction`，按流分离）；
  - **跨主种子探索性汇总**（池化 + 每种子均值 + 跨种子均值/样本标准差 + "仅探索性"声明）；
  - **discovery 与 audit 严格分离**（所有汇总与图表均按 stream 分列）；
  - 失败/中断/不完整/重放专节，如实记录。
- **图表**：森林图与 discovery→audit 对比图按 `master_seed` 分组建模，避免跨种子平均。

**源码证据锚点**：`_group_key`、`load_phase_data`（`y_by_run`/`status_by_run`）、`PhaseData`
（`replays`/`incomplete`）、`_build_per_seed_method`、`_build_cross_seed`、`write_report` 新增表格与专节。

### 2.3 D19 — 研究规则冻结 + 实现一致性 + 安全边界（`protocol.py` / `experiments.py`）

- **冻结规则描述**：`FROZEN_DESIGN` 现纳入 `wide_explore.nomination_rule`、
  `verify_first.selection_rule` / `nomination_pool` / `nomination_rule`，文本与
  `configs/formal_v01.json` **逐字一致**。修改规则描述 → 冻结设计漂移被拒，且改变
  `formal_config_fingerprint`。
- **实现一致性交叉核验**：新增结构化 `FROZEN_RULES`（有序 `(字段, 方向)` 规范）与
  `validate_method_rules()`，用合成 `AnchorRecord` 电池对照 `safefliplab.methods` 的
  `wide_nomination_key` / `verify_select_key` / `verify_final_key` 输出。
  **"改描述不改实现"或"改实现不改描述"都会触发核查**。该校验在 `validate_formal_config`
  中**始终**执行（含 `strict_design=False`）。
- **安全边界**：`_execute_formal_phase` 中 `strict_design=False` **仅允许显式测试替身**
  （`is_test_double=True`）；非测试适配器（含 `adapter=None`）一律 `PermissionError`，
  **禁止用 `strict_design=False` 运行真实正式仿真**。

**源码证据锚点**：`WIDE_NOMINATION_RULE`、`VERIFY_SELECTION_RULE`、`VERIFY_NOMINATION_RULE`、
`FROZEN_RULES`、`_reference_rule_key`、`_rule_battery`、`validate_method_rules`、
`validate_formal_config`（`issues.extend(validate_method_rules())`）、
`experiments._execute_formal_phase`（strict_design 守卫段）。

---

## 3. 新增及通过的测试数量

| 测试文件 | 项数 | 内容 |
|---|---:|---|
| `tests/test_ledger_concurrency.py`（新增） | **5** | 两独立实例竞争上限 1（仅 1 成功）；陈旧实例仍被拒；跨实例重复 key 被拒；表头唯一且仅追加；**6 进程**竞争恰 1 成功 |
| `tests/test_report_multiseed.py`（新增） | **7** | 2 主种子 → 2 quartet；无跨种子混并；cross-run_id 记为 replay 且排除主证据；不完整 quartet 如实记录不计入；discovery/audit 分离；每 seed×method 结构与独立审计；池化汇总与逐种子条目并存 |
| `tests/test_protocol_rules.py`（新增） | **11** | 规则文本与冻结一致；规则文本漂移被拒；指纹覆盖规则文本；实现漂移被检出并经 `validate_formal_config` 暴露；`strict_design=False` 对非测试替身/None 拒绝、对测试替身放行 |
| `tests/ledger_proc_worker.py`（新增，非测试） | — | 跨进程测试用的账本 worker（不含仿真器） |

- **单元测试：V03 的 146 → 本轮 169 全通过**（0 失败 / 0 错误；**+23**；零真实 episode）。
- 真实测试输出已保存：`docs/V04_TEST_RESULTS.txt`（`Ran 169 tests ... OK`）。
- 既有 146 项**全部保持通过**（账本/报告/协议重构无回归）。

---

## 4. master_seed 隔离是否真正通过测试？

**是。** 本轮从两个层面强化并验证：

1. **报告层**：`tests/test_report_multiseed.py::test_two_master_seeds_yield_two_quartets` 直接证明
   2 个主种子（各 4 条完整条件记录）→ **2** 个 quartet（修复前为 1）；
   `test_no_cross_seed_mixing` 证明 quartet 的 `master_seed` 与 `run_id` 严格对应、互不混并；
   `test_cross_run_id_is_a_replay_not_primary` 证明同 key 的二次运行**不会**被算作额外独立证据。
2. **账本层**：`budget_scope = formal|method|master_seed` 使 8 seed×2 method 各自独立受限
   （沿用 D13，未回归）；`tests/test_ledger_concurrency.py` 证明**跨实例/跨进程**也不会绕过作用域上限。

再加 V02/V03 的 `TestMasterSeedIsolation`（8 项）与 `test_master_seed_isolation_in_formal`，
master_seed 隔离在**代码与单测层面**已通过。

> **诚实边界**：以上均为代码/单测层面结论；真实 8-seed 独立性只有在真正执行 formal 时才会被物理验证，
> 本轮不启动 formal，故不对真实运行下结论。

---

## 5. 是否还有预算恢复与实验独立性问题？

### 5.1 预算恢复（resume）
- **合法恢复不误报、不重复计费**：沿用 V03 的累计预算判据（`launched_count_scope`）+ `new_episodes_this_call`；
  半程/全程恢复测试仍通过。
- **无免费重试 / 不突破冻结预算**：`error` / 中断 / launch-only 均计费且不视为完成；预算耗尽在
  首个 episode 前抛 `BudgetExhausted`，已计费不退还。
- **新增保证**：跨实例/跨进程的预算判断改为**锁内以磁盘权威状态**核对，杜绝"两执行者各通过检查后各自计费"。

### 5.2 实验独立性
- **跨 phase**：`phase` 过滤（D11）。
- **跨 master_seed**：隔离键 5 元组（D12）+ 报告分组含 `master_seed`（D18）。
- **跨 method / stream**：隔离键含 `method`、`stream`；audit 与 discovery 种子不同，报告严格分离。
- **跨 run_id**：不同 `run_id` 的同一 quartet key **分别计费**（D8），报告按 `run_id` 分桶并单列 replay（D18）。
- **跨实例/跨进程**：进程内共享锁 + 跨进程文件锁 + 锁内核对（D17）。
- **结论**：**未发现尚存的预算恢复或实验独立性问题**（在 FakeAdapter / 静态检查层面）。

---

## 6. 零碰撞的研究风险与原始任务书 GO/NO-GO 条件

> 沿用 V02/V03 的六点核查（真实 HighwayEnv 记录核验），本轮**未新增真实 episode**，结论不变。

1. `ego_collision` 来自**真实** HighwayEnv（抽查 12/12 一致；smoke 确定性重放一致）。✅
2. `front_gap+2.0` / `ego_speed−1.0` 真实改变场景（12/12 正确；3/3 quartet 仅两字段不同）。✅
3. 四条件共享同一 `sim_seed`（`inconsistent_sim_seed_keys=0`）。✅
4. `boundary` 控制器与适配正确（12/12 `controller_policy=boundary`）。✅
5. 全部零碰撞 → dev_seed 样本下碰撞主终点**无方差**（预期描述性结果）；真正担忧在**设计层面**
   （低事件率 → 低功效）。⚠️
6. **"全零碰撞" ≠ "四条件无可见差异"**：对既有真实记录的只读分析（66 个完整 quartet）显示，
   66/66 全部零碰撞，但 **100%（66/66）在过程级指标上仍可观察条件差异**（TTC/reward/轨迹哈希各 66/66，
   `policy_steps` 21/66），干预应用正确率 66/66。**含义**：本实验在**过程级指标**上能检测干预效应；
   唯一无方差的是**碰撞主终点**本身。

**GO/NO-GO 条件（对照原始任务书）**：
- 未触发任务书所列**接口/技术失败**类停止条件（doctor 17/17 GO；无接口错误）。
- 未触发"无效实验立即安全停止"条件（本轮零真实 episode）。
- **研究设计层面** NO-GO 风险仍在：零碰撞 → 碰撞主终点**低功效**，须人工裁决（§8 BLOCKER-3）。
- **主终点保持 `ego_collision` 不变**；TTC / 近撞等**仅作预注册方案**，未擅自改动正式协议。

---

## 7. D4 / D5 / D6 的建议与未批准状态

> **三项均为 PROPOSED，未经用户批准；本构建不代表用户批准任何一项。正式前必须逐项取得书面批准。**

- **D4（sim_seed 映射）**：审查结论**健全**——实现 `seeds.sim_seed_for` 与该规则一致；含 `method`
  与 `stream`、不含条件代码（四条件共享）、含 `repetition`；8 个 formal seed 由
  `SHA256(canonical_json(["SafeFlipLab-v01","formal-master",i]))` 派生，**稳定、确定、独立、非结果挑选**。
  **建议**：可批准，仅需人工书面确认。
- **D5（tie-break）**：本轮已把其**描述**冻结进 `FROZEN_DESIGN` 并与 `methods.py` **逐条核对**
  （D19）：WideExplore 提名 `(-delta_both, first_seen, anchor_id)`；VerifyFirst 选 20
  `(-delta_both, -delta_gap, -delta_speed, first_seen, anchor_id)`；最终提名
  `(-mean_delta_both, -valid_n, first_seen, anchor_id)`。
  **边界情形**：零有效样本 → `select_top` 仅保留 `valid_n>0`，无合格锚抛 `MethodError`（不提名）；
  **建议预注册**"0 合格锚"处理（报错中止 / 跳过 / 报告缺失）；部分无效仅累积完整 quartet；
  并列由 `anchor_id` 确定性打破；缺失观察排除出分子分母。**建议预注册** `valid_n` 的权重（主键 or 辅助键）。
- **D6（pilot 缩放）**：每方法 120（WideExplore 15+3×5；VerifyFirst 6+3×3+3×5），精确闭合 240，
  **仅描述性**。**重要边界**：D6 **不追溯性声称**原始授权已覆盖 PD-01 历史超支——+220 是 buggy
  重跑造成的程序偏离，与 D6 结构无关，**不得用 D6 为超支背书**。

> **注**：D19 的规则冻结**不是**对 D5 的批准——冻结的是"当前 PROPOSED 规则的文本与实现"，用于防止
> 悄悄漂移；批准与否仍由用户决定。

---

## 8. 尚未解除的 BLOCKER

| BLOCKER | 类别 | 状态 | 解除条件 |
|---|---|---|---|
| BLOCKER-1 跨 master_seed + 跨实例/进程隔离 | 技术 | V02–V04 已修复并测试（D12–D19）；**待人工复核后关闭** | 用户审阅 D12–D19 与相关回归测试并确认 |
| BLOCKER-2 D4/D5/D6 批准 | 合规 | **未解除**（PROPOSED） | 用户书面批准三项规则（含 D5 边界与 `valid_n` 权重） |
| BLOCKER-3 零碰撞/低事件率研究风险 | 研究 | **未解除** | 用户裁决（预注册次要终点 / 接受零结果 / 调整干预可检测性） |

**非阻塞但必须披露**：PD-01（pilot 真实累计 **460**，超上限 **+220**）。

---

## 9. 正式实验的实施状态

- **代码层面**：正式调度器完整实现（`_execute_formal_phase`，8 seed × 2 method × 800），
  报告/账本/协议校验均已加固，并通过 169 项 FakeAdapter 单测。
- **可执行性**：**被双层保护拒绝执行**（本轮实跑确认 CLI 仍 `REFUSED`）：
  1. **CLI 锁**：`python -m safefliplab formal --confirm --max-episodes 12800` → `RuntimeError`；
  2. **独立安全门**：任何直接调用且未传 `human_go=True`、适配器又非测试替身的路径，在构造任何
     仿真器前抛 `PermissionError`；`strict_design=False` 亦仅限测试替身（D19）。
- **本轮真实 episode**：**0**；`runs/episode_ledger.csv` **未新增任何行**（smoke 24 / pilot 240 /
  formal 0，528 数据行保持不变）。
- **是否具备启动 formal 的充分依据**：**否**（工程就绪，但 BLOCKER-2、BLOCKER-3 未解除）。

---

## 10. 最终建议：GO / NO-GO / BLOCKED

> **整体建议：BLOCKED（不启动 formal）**，直至以下三项全部解除：

- **BLOCKER-1（技术）**：D12–D19 已完成并测试通过；**待人工复核后关闭**。
- **BLOCKER-2（合规）**：D4 / D5 / D6 PROPOSED 规则取得人工书面批准。
- **BLOCKER-3（研究）**：人工裁决零碰撞 / 低事件率风险——基于 §6(6) 的"过程级指标可检测、
  仅碰撞主终点无方差"发现，建议**预注册碰撞率之外的次要终点**（TTC / 近撞 / 最小间距），
  或确认"零结果为可接受的信息性结论"，或在必要时调整干预可检测性。

**工程本身可 GO**；但 formal 启动仍需人工 GO + 上述 BLOCKER 解除，先 `python -m safefliplab doctor`
复核，再 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 11. 需要人工批准 / 审核的全部事项

1. 审阅并确认 **D17（跨实例/跨进程账本预算同步）**、**D18（报告主种子/run_id 隔离）**、
   **D19（规则冻结 + 实现一致性 + strict_design 边界）** 的修复方案与回归测试（**BLOCKER-1**）。
2. 批准 / 驳回 **D4** sim_seed 完整映射（审查结论：健全，建议批准）。
3. 批准 / 驳回 **D5** tie-break（含两单因素顺序/方向）及 `valid_n` 在提名中的权重；
   并预注册"0 合格锚"时的处理策略。
4. 确认 **D6** pilot 缩放仅作描述性验证，且**不追溯性声称**已覆盖 PD-01 历史超支。
5. 裁决零碰撞 / 低事件率研究设计风险（**BLOCKER-3**）：是否预注册功效 / 最低事件率，或接受零结果，
   或调整干预；建议把 TTC / 近撞等次要终点纳入预注册。
6. 对 pilot 预算偏离 **+220（PD-01）** 的知悉与处置确认（披露，不掩盖）。
7. 确认正式执行的双层保护（CLI 锁 + `_require_formal_go` + `strict_design` 边界）符合研究治理要求。
8. **显式 GO**：在 BLOCKER 解除后运行 `python -m safefliplab formal --confirm --max-episodes 12800`。

---

## 12. 人工审核前还需要什么（本构建已提供 / 待用户补充）

- ✅ 已提供：账本跨实例/跨进程预算同步（D17）+ 5 项回归测试（含真实多进程竞争）；
- ✅ 已提供：报告主种子/run_id 隔离与完善报告（D18）+ 7 项回归测试；
- ✅ 已提供：规则冻结/实现一致性/strict_design 边界（D19）+ 11 项测试；
- ✅ 已提供：真实测试结果 `docs/V04_TEST_RESULTS.txt`（`Ran 169 tests ... OK`）；
- ✅ 已提供：复现证据（§1，修复前→修复后）；
- ✅ 已提供：本文件 `docs/FORMAL_READINESS_V04.md` 与更新的 `docs/DECISION_LOG.md`（D17–D19）；
- ⏳ 待用户：逐项审批 D4/D5/D6、裁决 BLOCKER-3、复核 D12–D19 与 PD-01；
- ⏳ 待用户：决定是否将次要终点（TTC / 近撞）写入 `PROTOCOL_V01` 的预注册分析计划。

---

## 13. 本轮修改文件清单

**新增（非历史结果）**：
- `safefliplab/protocol.py`（V03 新增，本轮扩展：规则冻结 + `validate_method_rules`）；
- `tests/test_ledger_concurrency.py`、`tests/test_report_multiseed.py`、`tests/test_protocol_rules.py`；
- `tests/ledger_proc_worker.py`（跨进程测试 worker，非测试模块）；
- `docs/V04_TEST_RESULTS.txt`、`docs/FORMAL_READINESS_V04.md`。

**修改**：
- `safefliplab/ledger.py`（D17：进程内共享锁 + 跨进程文件锁 + 锁内增量核对 + `LedgerLockTimeout`）；
- `safefliplab/report.py`（D18：分组含 `master_seed`+`run_id`、replay/incomplete 单列、完善报告）；
- `safefliplab/protocol.py`（D19：`FROZEN_RULES` + `validate_method_rules` + 规则纳入 `FROZEN_DESIGN`）；
- `safefliplab/experiments.py`（D19：`strict_design=False` 仅限测试替身）；
- `docs/DECISION_LOG.md`（新增 D17–D19）。

**副作用（新文件，不改写历史账本）**：
- `runs/episode_ledger.csv.lock`（D17 的 sidecar 锁文件；**不含账本内容，未改动 CSV 任何字节**）。

---

## 14. 原始文件保全声明

**保留（未改写）的原始文件**：
- `runs/episode_ledger.csv`（**528 数据行**，smoke 24 / pilot 240 / formal 0）、
  `runs/episode_ledger.csv.buggy_pilot_run1`（**489 数据行**）；
- `runs/_buggy_pilot_run1/`、`runs/manifest_*.json`、`runs/<run_id>/` 原始 episode JSON；
- `reports/*`（smoke/pilot 报告、`*_quartets.csv`、`figure_*.png`、`*_summary.json`）；
- `configs/formal_v01.json`（**本轮未修改**）、`configs/dev_v01.json`；
- `docs/PROTOCOL_V01.md` 等科研规则原文。

**声明**：本轮**未启动任何真实 smoke/pilot/formal episode**、**未发布 GitHub**、**未改动旧 CornerCaseLab**、
**未解除 formal 安全锁**、**未改写历史结果**（账本 528/489 行、报告、种子、审计记录原样保留）；
一切测试均用 `FakeAdapter` 或静态检查；全篇结论基于既有真实记录与真实测试输出。
