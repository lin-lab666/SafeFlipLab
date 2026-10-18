# DECISION_LOG — SafeFlipLab 技术决策记录

> 记录所有对任务书的实现级决策。凡任务书未精确定义的，标注 **PROPOSED**，
> 未经用户正式批准不得视为已冻结；不得静默修改科研规则。

## D1. cornercaselab 的获取方式（已决断：依赖安装）

- **事实核验**：`cornercaselab` 不在 PyPI（`pypi.org/pypi/cornercaselab/json`
  返回 Not Found，2026-10-12 核验）；GitHub `lin-lab666/CornerCaseLab` 存在
  tag `v0.3.0`（Apache-2.0）。
- **决定**：以 `git+https://github.com/lin-lab666/CornerCaseLab@v0.3.0`
  安装进项目 venv，按公开接口导入使用；不复制、不改写其源码。
- **理由**：任务书要求"优先复用已发布、许可允许的公共仿真接口"；安装依赖
  是最忠实的复用方式，且版本可钉死、可复现。

## D2. 控制器选择（已决断：boundary）

- 任务书写"policy=boundary"。cornercaselab 0.3.0 的 `POLICIES =
  ("reactive", "boundary", "cruise")`；`boundary` 即任务书指定的冻结控制器。
- 四条件、两方法、所有种子、所有阶段统一使用 `boundary`，不做任何调整。

## D3. anchor 合法域（已决断：收紧边界 + 拒绝采样）

- 干预 `front_gap += 2.0` 与 `ego_speed -= 1.0` 要求 anchor 域在上游边界内
  收紧：front_gap ≤ 78，ego_speed ≥ 21。
- generator 用统一拒绝采样：顺序抽取上游均匀样本，不合法即拒绝，直到获得
  合法 anchor；记录消耗的均匀抽取次数（`stream_draws`）。拒绝发生在仿真前，
  不消耗 episode 预算。
- 四条件构造时若越界直接抛错（Scenario 的 `__post_init__` 校验），
  **绝不 clip**。

## D4. sim_seed 映射（PROPOSED，待批准）

- 任务书要求"同一 anchor 同一 repetition 四条件共享一个稳定派生的 sim_seed"，
  但未给出完整映射。
- **PROPOSED**：`sim_seed = SHA256([v01, "seed", master_seed, "sim", method,
  stream, anchor_id, repetition])`。含 method（两方法数据流互相独立）、
  含 stream（audit 种子绝不与 discovery 重复）；不含条件代码（四条件共享）；
  含 repetition（VerifyFirst 的 3 个追加 quartet 与 audit 的 20 个 quartet
  互不相同）。

## D5. tie-break 细节（PROPOSED，待批准）

- WideExplore 提名：`(-delta_both, first_seen, anchor_id)`——任务书已给。
- VerifyFirst 选 20：任务书给"delta_both 降序，并列时以其他两个单因素差值
  为第二/第三排序键，最后 first_seen、anchor_id"，但未指定两个单因素顺序
  与方向。**PROPOSED**：`(-delta_both, -delta_gap, -delta_speed, first_seen,
  anchor_id)`。
- VerifyFirst 最终提名：任务书列举"均值 delta_both、有效样本数、first_seen、
  anchor_id 等冻结排序规则"但未给完整次序。**PROPOSED**：
  `(-mean_delta_both, -valid_n, first_seen, anchor_id)`。

## D6. pilot 结构缩放（PROPOSED，待批准）

- 任务书规定 smoke ≤ 24、pilot ≤ 240，但未规定 pilot 内部配额。
- **PROPOSED**：每方法 120 episodes，保持正式结构。WideExplore：
  15 discovery + 3 提名 × 5 audit；VerifyFirst：6 stage-1 + 3 选 × 3 追加 +
  3 提名 × 5 audit。精确闭合 240，无部分计划。
- pilot 数字只作管道与描述性验证，dev_seed 下不构成正式证据。

## D7. 断点恢复（已决断：基于证据的恢复，非自动补跑）

- 任务书/交接手册要求：没有证据支持安全 resume 前不得重复运行命令补跑。
- **决定**：driver 启动时从账本一次性加载已完成 quartet；对同一
  (phase, method, anchor, repetition, stream) 已完整的 quartet 直接复用账本
  中的真实 Y（不重新发起、不虚构）；未完成/失败的 job 才重新发起（重新计费）。
  该行为有单元测试覆盖（`tests/test_experiments.py`）。
- 硬杀导致的"有 launch 无 outcome"条目仍计费，Y 保持缺失。

## D8. 账本设计（已决断）

- 两行类型共享 `episode_key`：`launch`（启动即计费）+ `outcome`
  （completed/error/interrupted）。行不可变、只追加。
- `completed` 必须带 `ego_collision ∈ {0,1}`，否则拒绝写入（防止静默污染统计）。
- 同一 episode_key 重复 launch 不重复计费；不同 run_id 的同一 quartet key
  （重放）分别计费——这正是 smoke 的确定性重放检查。

## D9. 图表与报告（已决断）

- 三类图（四条件配对结果、每 anchor 风险差森林图、discovery→audit 对比）
  只在存在真实完整数据时生成；无数据时报告明示"无真实数据"且不出图。
- 报告数字全部来自 `runs/episode_ledger.csv` 与原始 episode 记录。

## D10. 未决 / 待人工审核项

1. D4、D5、D6 的 PROPOSED 规则需用户批准后才可进入 formal。
2. 有效样本数在提名中的权重（D5）可能与"先看效应量"的直觉冲突，需确认。
3. pilot 的审计 quartet 数（5）远小于正式的 20，审计证据强度有限，
   不得解释为正式结论。

## D11. pilot 阶段隔离 bug（已决断：修复并重跑）

- **现象（2026-10-12 接管后复算验证）**：首次 `run_pilot` 实际只发起 **220** episodes（应为 240），
  且 discovery 跳过了与 smoke 共享 `(method, anchor_index, repetition, stream)` key 的前几个锚
  （WideExplore 0/1/2、VerifyFirst 0/1），audit 不受影响（15/方法）。
- **根因**：`PhaseDriver.completed_quartets()` 与 `_records_for()`（经由 `_index_completed` /
  `_note_outcome`）**未按 `self.phase` 过滤**。smoke 阶段已在这些 key 上完成 quartet，
  pilot 的 resume 逻辑误将其认作"已完成"，跳过对应 discovery 锚、少跑 20 episodes。
- **影响**：首次 pilot 既未用满预算，也未测试应有锚集合 → **该运行无效**。
- **修复**：在 `_index_completed` 与 `_note_outcome` 中加入
  `if launch.get("phase") != self.phase: return` 的相位隔离；并新增回归测试
  `tests/test_experiments.py::TestPhaseIsolation::test_completed_quartet_from_other_phase_is_not_resumed`。
- **处置**：首次无效运行移至 `runs/_buggy_pilot_run1/`（55 个 run 目录）与
  `runs/episode_ledger.csv.buggy_pilot_run1` 作审计留痕；活动账本保留 smoke 行、
  清空 pilot 行后**重新干净运行** pilot，得到有效 **240/240、0 错误 0 中断** 的结果。
- **账本行数口径说明（重要）**：`runs/episode_ledger.csv.buggy_pilot_run1` 实际为
  **489 数据行**（= 244 episodes × 2 行 + 1，含当时整本快照里的 smoke 24 + buggy pilot 220）。
  本 DECISION_LOG 上一版写"440 行"只统计了 **buggy pilot 自身**（220 × 2 = 440），
  漏算了同快照内的 smoke 24（48 行）。活动账本 `runs/episode_ledger.csv` 为 **528 数据行**
  （= 264 episodes × 2，即 smoke 24 + 有效 pilot 240）。三者均为真实账本，差异仅来自
  "是否包含 smoke 行 / 是否含表头" 的口径，不存在数据丢失或被篡改。
- **formal 关联**：本修复同样保护 formal（否则 formal 会误读 smoke/pilot 行）。建议在启动
  formal 前由人工复核该隔离语义是否满足"跨 master seed 的断点恢复"要求。

## D12. 跨 master_seed 隔离修复（已决断：修复并通过回归测试，待人工复核）

- **背景**：在 2026-10-12 的正式前静态审计（`docs/FINAL_PRE_FORMAL_AUDIT.md §5.4`）中发现，
  D11 的相位隔离**不足以支撑正式多 seed**：`PhaseDriver` 的 resume 隔离键为
  `(method, anchor_index, repetition, stream)`，**不含 `master_seed`**，且
  `completed_quartets()` / `_records_for()` / `runs_completing_key()` 未按 `self.master_seed`
  过滤。正式阶段 8 个 master seed 共享同一账本与同一 `phase="formal"`，因此 seed A 完成某 quartet
  后，seed B 的 `execute_job` 会误把 A 的完成 quartet 当作"已完成"并复用其 Y，导致 seed B…H
  不再发起真实 episode —— 真实唯一 episode 仅约 1/8，彻底破坏 8-seed 独立性。这是正式硬阻塞。

- **修复（`safefliplab/experiments.py`）**：
  1. `_index_completed` 与 `_note_outcome` 在既有 `phase` 过滤之外，**新增
     `if int(launch.get("master_seed")) != self.master_seed: return`** 过滤，
     使一个 driver 只索引属于自身 `(phase, master_seed)` 的完成 quartet。
  2. resume 隔离键升级为 **5 元组**
     `(master_seed, method, anchor_index, repetition, stream)`：
     `completed_quartets()` 的键、`execute_job` 的查询键、`_records_for` 的迭代键、
     `PhaseReport.quartets` 的键与 `to_dict` 序列化同步更新；`run_smoke` 的确定性重放
     `runs_completing_key` 调用键同步改为 5 元组。
  3. 既有的 `phase` 隔离（D11）保留，二者叠加。
  4. `doctor`、`ledger`、`runner`、正式 CLI 锁（`cmd_formal` 仍必须先 `--confirm` 且
     `--max-episodes 12800` 才放行，之后仍抛 `RuntimeError` 不真正运行）**均未改动**，
     正式不可启动保护完整保留。

- **回归测试**：新增 `tests/test_experiments.py::TestMasterSeedIsolation`（8 项，全用
  `FakeAdapter`，零真实 episode）：
  - `test_seed_b_must_launch_after_seed_a`：A 完成后，B 必须独立发起自己的 quartet，
    不得复用 A 的 Y（跨 seed 隔离）。
  - `test_seed_b_legal_resume_no_double_billing`：同一 seed 的合法恢复复用已完成 quartet，
    不重复发起、不重复计费。
  - `test_force_reruns_and_bills_again`、`test_launch_only_quartet_not_reused_and_re_run_bills_again`、
    `test_error_quartet_billed_and_re_run_costs_again`：覆盖 `force` 重跑、launch-only（中断）、
    `error` 三类恢复路径——均按"已计费、未完成不复用、重跑重新计费"语义，无免费重试、无突破冻结预算。
  - `test_two_seeds_have_mutually_exclusive_completed_views`：两 seed 的完成视图互斥。
  - `test_formal_budget_exhaustion_blocks_extra_launch_without_free_retry`：预算耗尽后首 episode
    前即 `BudgetExhausted`，已计费不退还。
  - `test_different_run_id_same_key_billed_separately`：同一 seed/键的两次运行（smoke 确定性重放）
    分别计费、两个 run_id 均入账（D8）。
  - 既有 `TestPhaseIsolation` 因键形变更同步更新为 5 元组断言。

- **结果**：单元测试由 98 → **106 全通过**（0 失败 0 错误，约 7.5 s，零真实 episode）；
  `python -m safefliplab doctor` 仍 **17/17 PASS，VERDICT: GO**，正式锁完好。
  BLOCKER-1（跨 master_seed 隔离）**已通过代码与测试解除**，待人工在对本修复方案与回归测试
  确认后正式关闭。

## D13. 账本安全与计费加固（已决断：原子预占 + 去重 + 空行修复 + 作用域计费）

- **背景**：独立源码审查发现三处账本安全/计费问题。
- **决定（`safefliplab/ledger.py`）**：
  1. **原子预占**：新增 `reserve_launch(...)`，把"预算检查 + 重复拒绝 + 计费写入"
     合入**同一把锁**。旧路径 `check_budget()` 与 `record_launch()` 分离，两线程/两进程
     可同时通过检查后各自启动，从而绕过上限；runner 已改用 `reserve_launch`。
  2. **重复启动拒绝**：同一 `episode_key` 在**同一预算作用域**内二次启动，在任何仿真
     动作之前抛 `DuplicateLaunch`，杜绝"实际启动多次却只计费一次"；`force` 重跑用新
     `run_id`（新 key），照常重新计费（无免费重试）。
  3. **空行修复**：新建账本只写**表头**，不再写入一整行全空数据行（旧实现会留下幽灵行，
     破坏行数口径）。**不改写历史账本**；提供 `empty_data_rows()` / `diagnose()` 兼容读取
     与独立核对（含合成"pre-fix 空行"账本的兼容测试）。
  4. **作用域计费**：新增 `budget_scope` 列与 `launched_count_scope()`。smoke/pilot 作用域
     =phase；formal 作用域=`formal|method|master_seed`，使 8 seed × 2 method 各自独立受限，
     不再争抢 phase 总上限。
- **兼容**：旧行无 `budget_scope` 列时回退为 phase 作用域；活动账本计数不受空行影响。

## D14. 正式调度器补齐 + 结果记录修复（已决断）

- **背景**：`run_formal_phase` 只创建第一个 seed 的驱动器，`run_formal` 始终抛
  `RuntimeError`，未实现 8 seed × 2 method × 800 的完整执行；且存在 audit 混流、
  pilot 汇总用过期账本等问题。
- **决定**：
  1. **完整正式调度**：新增 `_execute_formal_phase`（8 seed × 2 method，每 method×seed
     800 = 400 discovery + 400 audit；提名冻结后再启动 audit；每 (seed, method) 独立
     manifest 不互相覆盖；断点恢复不重复计费）。**CLI 安全锁保留**：`run_formal`/
     `run_formal_phase` 仍抛 `RuntimeError`，不真正执行。
  2. **累计预算验证**：正式调度以**当前 `method × master_seed` 作用域的累计预算**
     （=800）为判据，并**另行记录本次新增次数** `new_episodes_this_call`。旧的
     `after − before == 800` 判别会在**合法断点恢复**时误报，已废弃。
  3. **audit 隔离修复**：`_records_for(..., stream=...)` 增加流过滤；`audit_results` 只
     聚合 `audit` 流，绝不把提名锚的 discovery quartet 混入其审计汇总。
  4. **pilot 汇总修复**：`run_pilot` 汇总改用**重新打开的持久化账本**，不再使用在
     子驱动器运行前构建的过期内存视图（否则会低报）。
- **测试**：新增 `tests/test_formal_scheduling.py`（多 seed 调度、分阶段预算、审计隔离、
  主种子隔离、半程恢复、全部完成后再次调用、重复启动、manifest 不覆盖、CLI 锁）。

## D15. 正式执行独立安全门（已决断：未获人工 GO 不得启动真实 episode）

- **背景**：`_execute_formal_phase` 可不经 CLI 直接调用，且 `adapter=None` 会构造**真实**
  `ScenarioAdapter`，存在绕过 CLI 锁启动真实 episode 的隐患。
- **决定**：新增 `_require_formal_go(adapter, human_go)`，在**所有正式执行入口**
  （`_execute_formal_phase`、`_run_formal_method`）最先调用：
  - 显式人工 GO（`human_go=True`）放行；
  - 否则适配器必须是显式**测试替身**（`is_test_double=True`，`FakeAdapter` 已加此标记），
    以便离线集成测试；
  - 其余情形（`adapter=None` 或非测试适配器）在构造任何仿真器之前抛 `PermissionError`。
- **结果**：CLI 锁 + 独立安全门双层保护；FakeAdapter 测试能力保留。

## D16. 正式配置冻结漂移校验（已决断）

- **背景**：`configs/formal_v01.json` 是正统研究设计记录，误改（预算、种子、节奏）不得
  悄悄进入真实 12,800 episode 运行。
- **决定（`safefliplab/protocol.py`）**：声明代码级冻结设计 `FROZEN_DESIGN` 与
  `frozen_protocol_fingerprint()`；`validate_formal_config()` 一次列出**全部**问题：
  种子数量、**唯一性**、整型性、**冻结值/顺序**（须等于 SHA-256 派生列表）、
  protocol id、`boundary` 控制器、simulator 节奏、budget 与两方法计划尺寸、
  **协议指纹**（若 config 声明 `protocol_fingerprint` 则须匹配冻结指纹）。
  `_execute_formal_phase` 在严格模式下强制该校验（缩放集成测试用 `strict_design=False`
  仅放宽冻结设计比对，仍强制数量/唯一性/整型）。
- **不修改** `configs/formal_v01.json`（未新增字段）。新增 `tests/test_formal_config.py`
  覆盖：真实配置合法且指纹匹配、重复/乱序/改值种子、改预算/计划/节奏、错 protocol id、
  错控制器、指纹不匹配等均被拒。

## D17. 账本跨实例/跨进程预算同步（已决断）

- **背景（独立源码验收复现的真实缺陷）**：两个 `EpisodeLedger` 实例同时打开同一 CSV，
  在作用域上限=1 时**各自** `reserve_launch` 成功，磁盘出现 **2** 次 launch（超额）。
  根因：每实例只有自己的 `threading.Lock` + 私有内存缓存；两实例都缓存"作用域为空"，
  各自通过检查。跨进程同理。
- **决定（`safefliplab/ledger.py`）**：
  1. **进程内共享锁**：按解析后的账本路径维护模块级锁注册表，所有指向同一 CSV 的实例
     共用同一把 `threading.Lock`。
  2. **跨进程文件锁**：对 sidecar `<ledger>.lock` 加 OS 级独占锁（Windows `msvcrt.locking` /
     POSIX `fcntl.flock`），不触碰账本 CSV 本身，因此**不改写任何历史账本字节**。
  3. **锁内持久化核对**：在锁内**增量**重读磁盘 CSV（自上次消费字节起），再以**磁盘权威状态**
     做预算与去重判断，最后原子追加。`_consumed_bytes` 增量核对 + set 幂等，兼顾正确与性能。
  4. 获取锁超时抛 `LedgerLockTimeout`（宁失败不越权）。
- **证据**：新增 `tests/test_ledger_concurrency.py`（5 项）：两个独立实例竞争上限 1 → 仅 1 成功、
  磁盘仅 1 行；陈旧实例仍被拒；跨实例重复 key 被拒；表头唯一且仅追加；**6 个独立进程**竞争
  → 恰 1 个 `OK`、其余 `REFUSED`、磁盘恰 1 行。

## D18. 正式报告主种子 / run_id 隔离（已决断）

- **背景（独立源码验收复现的真实缺陷）**：`report.load_phase_data` 分组键为
  `(method, anchor_id, repetition, stream)`，**缺 `master_seed` 与 `run_id``。构造 2 主种子各 4 条
  完整条件记录，只得到 **1** 个 quartet（应为 2）——跨种子 Y 值被混并。
- **决定（`safefliplab/report.py`）**：
  1. quartet 分组键升级为 `(master_seed, method, anchor_id, repetition, stream, run_id)`；
     四条件必须来自**同一 run**（同一配对 `sim_seed`），禁止跨种子/跨批次混并。
  2. **重复运行**（同 key 的二次完整运行，如 smoke 确定性重放）单列为 *replay*，**不作独立科学证据**。
  3. **不完整 quartet**（四条件未在同一 run 内完成）如实记录（含每 run 每条件状态），不计入分子分母。
  4. 正式报告新增：每 `master_seed × method` 的**独立结果**与**独立审计**（按提名 anchor）；
     两方法每主种子的 **paired contrast**（discovery/audit 分离）；**跨主种子探索性汇总**
     （含跨种子均值/样本标准差与"仅探索性"声明）；**discovery 与 audit 严格分离**。
- **证据**：新增 `tests/test_report_multiseed.py`（7 项）：2 种子 → 2 quartet；无跨种子混并；
  cross-run_id 记为 replay 且排除出主证据；不完整 quartet 如实记录且不计入；discovery/audit 分离；
  每 seed×method 结构与独立审计结果；池化方法/流汇总与逐种子条目并存。

## D19. 研究规则冻结 + 实现一致性 + 安全边界（已决断）

- **背景**：`protocol.py` 未冻结 `nomination_rule`/`selection_rule` 等研究规则描述，修改规则描述
  （config 文本）不会触发任何核查；且 `strict_design=False` 可被用于非测试替身。
- **决定（`safefliplab/protocol.py` + `experiments.py`）**：
  1. **冻结规则描述**：`FROZEN_DESIGN` 纳入 `wide_explore.nomination_rule`、
     `verify_first.selection_rule`/`nomination_pool`/`nomination_rule`；其文本与
     `configs/formal_v01.json` **逐字一致**。任何规则描述改动 → 冻结设计漂移被拒，且改变
     `formal_config_fingerprint`。
  2. **实现一致性交叉核验**：新增 `validate_method_rules()`，用结构化 `FROZEN_RULES`（有序
     `(字段,方向)` 规范）对照 `safefliplab.methods` 的 `wide_nomination_key` / `verify_select_key` /
     `verify_final_key` 在合成 AnchorRecord 电池上的输出。**改描述不改实现、或改实现不改描述，
     都会触发核查**。该校验在 `validate_formal_config` 中**始终**执行（含非严格模式）。
  3. **安全边界**：`_execute_formal_phase` 中 `strict_design=False` **仅允许显式测试替身**
     （`is_test_double=True`）；非测试适配器一律 `PermissionError`，禁止用它运行真实正式仿真。
- **不修改**任何既有研究规则内容；D4/D5/D6 仍为 PROPOSED，不代表用户批准。
- **证据**：新增 `tests/test_protocol_rules.py`（11 项）：规则文本与冻结一致；规则文本漂移被拒；
  指纹覆盖规则文本；实现漂移被检出并经 `validate_formal_config` 暴露；`strict_design=False`
  对非测试替身/None 拒绝、对测试替身放行。

## D20. 探索性连续安全裕度分析（PROPOSED，非协议指标；零新 episode）

- **背景（2026-10-13 接续核验轮）**：BLOCKER-3 记录"66 个完整 quartet 全部零碰撞，但 100% 在
  TTC/奖励/轨迹上仍可观察条件差异"。逐条抽查原始 episode 记录证实：干预
  `front_gap += 2.0` 使同一 anchor 的 `min_forward_ttc_sampled_s` 从 1.339 s 降到 0.917 s
  （更接近碰撞，但碰撞二元值仍为 0）。碰撞二元指标在该样本下恒为 0，无法显示任何条件差异，
  需要**不消耗任何新 episode 预算**的描述性补充来如实呈现"全零碰撞 ≠ 无可见差异"。
- **决定（新增 `safefliplab/margins.py`，`report.py` 增加一节与第 4 张图）**：
  1. 从**账本 `raw_path` 指向的已存在原始 episode JSON** 重读
     `min_forward_ttc_sampled_s` / `reward_sum` / `policy_steps` / `sim_time_s`；
     **不启动任何新仿真、不重跑历史、不修改账本与原始记录**。
  2. quartet 隔离规则与主统计**完全一致**：`(master_seed, method, anchor_id, repetition,
     stream)` + 单一 `run_id` 四条件齐全；同 key 的二次完整运行（smoke 确定性重放）按
     replay 排除，不计入独立证据（与 `report.load_phase_data` 的 primary/replay 语义一致）。
  3. 输出逐 quartet 配对差 `ΔTTC(both)=TTC(11)−TTC(00)`、`ΔTTC(gap)`、`ΔTTC(speed)`，
     按 (method, stream) 汇总，写入 `reports/<phase>_margins.csv` 与报告 JSON。
  4. **报告与图明确标注"非协议指标 / 非正式证据"**；负 ΔTTC 表示"更接近碰撞但不等于碰撞"，
     不得外推为真实道路安全结论；缺失记录不插补。
- **这不是对冻结协议指标的修改**：主指标仍是碰撞二元 Y；本分析只是从已付费数据中提取的
  描述性补充，用于人工评估 formal GO 前了解零碰撞样本中的连续裕度行为。
- **证据（真实 dev_seed 数据，零新 episode）**：
  - smoke：WideExplore/discovery（n=3）ΔTTC(both)=−0.2158；VerifyFirst/discovery（n=2）=−0.2786。
  - pilot：**全部 4 个 (method, stream) 组的 mean ΔTTC(both) 均为负**：
    WideExplore/discovery −0.0383、WideExplore/audit −0.2158、
    VerifyFirst/discovery −0.1799、VerifyFirst/audit −0.2158。
    方向一致指向"组合干预降低连续前向 TTC 安全裕度"，但**样本量小、单 dev_seed、
    未经独立审计放大**，不得作为正式证据或稳定反转宣称。
  - 新增 `tests/test_margins.py`（14 项，全合成账本/原始记录，零真实 episode）：
    完整 quartet 配对差、不完整排除、原始缺失计数、跨 run 不混并、同 key 二次运行记 replay、
    phase 隔离、无账本、汇总分组、CSV 形状、报告集成（有/无数据）。

## D21. F-01 账本格式兼容与安全拒绝（已修复 + 独立验收；零新 episode）

- **背景（2026-10-13 独立科研审计轮）**：真实 `runs/episode_ledger.csv` 的**表头与全部数据行
  均为 20 列**（早于 `budget_scope` 列），而当前代码追加 21 字段行。若重读时第 21 字段被丢弃，
  则新进程/断点恢复时 `launched_count_scope("formal|method|seed")` 为 0，**分作用域正式预算
  失效**（可重复花费每个 (method, seed) 的 800 预算）。此为 D17 跨进程预算同步的遗留缺口。
- **决定（`safefliplab/ledger.py`）**：
  1. **读取侧前缀映射（只读，不改写历史账本）**：新增 `resolve_fieldnames()`。表头与 `COLUMNS`
     完全一致 → 原样；为 `COLUMNS` 的**严格前缀**（遗留 20 列）→ 补齐为完整 `COLUMNS`，
     使新行的第 21 字段映射到 `budget_scope`（遗留 20 字段行则回退到 phase 作用域）。
  2. **不兼容即安全拒绝**：表头既非 `COLUMNS` 亦非其严格前缀（多余列 / 乱序列 / 未知列 /
     同宽异名）→ 抛 `LedgerFormatError`，**绝不逐列猜测**（否则可能静默丢列、漏计预算）。
  3. **行宽守卫**：数据行字段数 **多于** 已解析表头列数 → 抛 `LedgerFormatError`
     （拒绝丢弃多余字段）；先解析校验、后推进 `_consumed_bytes` 与计数器，拒绝时不污染状态。
- **独立验收（`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`，仅用临时账本，真实账本只读）**：
  1. 遗留 20 列表头 → 追加 21 字段 scoped 行 → 关闭 → 重开：scope/phase 计数正确、上限生效；
  2. `budget_scope` 落盘（第 21 字段）并在重开后恢复；
  3. 每 (method, seed) 作用域重开后相互独立（A 达上限不影响 B/C）；
  4. **8 个 OS 进程**共享一份遗留账本、cap=3 → 恰好 3 成功 5 拒绝，无超支，scope 保留；
  5. 中断无 outcome 仍计费；重复 key 在任何仿真前被拒；新 run_id 强制重跑再次计费（无免费重试）；
  6. 4 类不兼容表头全部 `LedgerFormatError` 安全拒绝；遗留前缀为对照放行。
- **回归测试**：`tests/test_ledger_legacy_acceptance.py`（15 项）覆盖上述 6 场景；
  跨进程 worker `tests/ledger_proc_worker.py` 扩展支持自定义 cap/scope。
- **证据**：真实账本打开前后读取 `smoke=24 / pilot=240` 不变、文件字节数不变（只读）。
- **状态**：F-01 代码缺陷**已修复并独立验收**；**待人工复核**后与 D12–D19 一并关闭 BLOCKER-1。
  本项**不修改**任何研究规则、主指标或冻结配置。

## D22. 图表标题溢出修复（F-05，已修复 + 回归测试；零新 episode）

- **背景**：`figure_2/3/4` 的长英文标题以单行 `fontsize=9` 绘制，`tight_layout` 不计入标题宽度，
  导致标题右侧被画布裁切（如 "…no C"、"…no CI estima"）。
- **决定（`safefliplab/report.py`）**：新增 `_wrap_title(text, width=70)`，将标题按词换行；
  四张图统一 `ax.set_title(_wrap_title(...), fontsize=9)`，并在 `savefig` 使用
  `bbox_inches="tight"` 作为兜底，确保完整呈现。
- **同时复核**（延续 D9/F-02/F-03）：图 2/3/4 均为**点估计**（无置信区间），
  零方差数据下 `_sane_value_axis` 保证轴范围为 ±0.5 且无 `1e−17` 偏移；图 4 明确标注
  `NON-PROTOCOL`。
- **回归测试**：`tests/test_figure_axes.py` 新增 `TestTitleWrap`（4 项）：长标题必换行且每行≤宽度、
  换行保词、短标题不变、真实图 3 标题含换行。

## D23. 复审统计解释修订（R1/R2/R3；纯文档，零新 episode）

- **背景**：`INDEPENDENT_SCIENTIFIC_REVIEW.md` 外部复核后指出三处统计解释问题。
- **决定（仅修订 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`，不改代码/配置/账本）**：
  1. **R1（rule of three 独立性假设）**：撤回"每条件 60 episode 全零 ⇒ 95% 上界 ≈ 5%"。
     该式要求 iid Bernoulli；pilot 中锚内 repetition 非独立重采样、同 quartet 四条件共享配对种子、
     anchor 由确定性拒绝流生成 ⇒ 假设不成立。改按分层单元计数（episode 60 / anchor 15 /
     audit 3），**只作"0 次碰撞观测"的描述**，不作频率量级宣称。
  2. **R2（VerifyFirst 排序键）**：修正早前稿"tie-break 链（单因素差、valid_n）从未被触发"。
     逐键分解：stage-1 三枚 delta 键恒并列于 0，实际仅 `(first_seen, anchor_id)` 生效；
     **最终提名阶段 `valid_n` 是第一枚生效的判别键**（stage-2 锚 `valid_n=4` vs 其余 `=1`）。
     VerifyFirst 的"先验证再复测"结构在 `valid_n` 上可见，但其内容仍退化为流内序号。
  3. **R3（TTC 跨种子确定性适用范围）**：新增 §3.3.1，明确该结论**仅对已采样 pilot 锚**成立，
     **不外推**到 lead 非自由流、ramp 更早并入的未来 anchor，**亦不外推**到碰撞事件
     （碰撞在全 pilot 未观察，无证据支持其种子无关）。
- **证据**：只读复核脚本 `.workbuddy/tmp_audit/rev_data.py` → `docs/REVISION_ANALYSIS_20261013.txt`。
- **状态**：**已完成**；不改任何研究规则内容；未宣布任何批准。

## D24. V02 预注册研究提案与独立标准账本方案（PROPOSED；零新 episode）

- **背景**：V01 主指标零方差、提名退化、repetition 不重采样 ego–lead（评审 §2.2/§3.4），
  12,800 可能无法产出方法间结论。用户要求设计 V02 并对比。
- **决定（新增 `docs/V02_RESEARCH_PROPOSAL.md`；**全部条目 PROPOSED，未实现任何代码**）**：
  1. **假设 H1a–H1c（单因素与交互）、H2（方法比较）、H3（二元事件，次）、H4（扰动有效性）**；
  2. **终点**：连续前向安全裕度 M1（最小前向 TTC）/ M2（低于阈值时间占比）为 co-primary，
     碰撞 B1 降为次终点（仅 G3 通过时检验）；终点/阈值/方向全预注册；
  3. **有效随机扰动 P1–P4**：锚内有界扰动（lead 初速/目标速度、初始间距、lead 减速事件、
     ego 初速），四条件共享同次扰动抽样；**G4 可证伪前置检查**（锚内方差 > 0 且闭合序列随
     repetition 变化）否则 NO-GO；
  4. **独立审计**沿用"提名先于审计、种子分离、不回灌"，审计使用同一扰动分布；
  5. **公平预算**等额，样本量由技术 pilot 设计分析确定（不照搬 800）；
  6. **统计**：独立单元=anchor，锚级 cluster bootstrap + 锚级置换检验 + 多重性控制；
     零事件只报告计数、不套 rule of three（呼应 D23 R1）；
  7. **L-01 独立 canonical 21 列标准账本**：`runs/formal/episode_ledger.csv` 与旧账本
     **物理分离**、创建即 canonical 表头、严格模式读取、固定行宽、schema 指纹、
     首行即含 budget_scope、旧账本只读不变（§9 in V02）；**仅设计，未实现**；
  8. **技术 GO/NO-GO 门槛 G1–G8**（可复现/干预有效/终点方差/扰动有效/阴性对照/仿真器稳定/
     账本安全/统计有效），任一硬门槛失败即 NO-GO；
  9. **V01 vs V02 对比表**与**与 CornerCaseLab v0.3.0 的贡献差异**（后者差异表述需人工核验）。
- **边界**：不修改 `configs/formal_v01.json`；不开始 V02 编程；不运行任何真实 episode；
  V01 历史数据在 V02 中仅作管道验证，不作 V02 证据。
- **状态**：PROPOSED，**待人工批准**；未宣布任何批准；未选择主指标；未选择 §6 方案。

## D25. V02 定向方法学修订（v2）+ 协议评审清单（PROPOSED；纯文档，零新 episode、零代码变更）

- **背景**：外部复核对 V02 初稿提出七项方法学问题（反转/交互混同、co-primary 争议、锚内标签
  置换不可交换、H2 指标含糊、扰动/门槛/预算粗糙、未披露设计事后性、与 CornerCaseLab 重叠未审）。
- **决定（仅修订/新增文档，**未改源码、未改 `configs/formal_v01.json`、未运行任何真实 episode**）**：
  1. **修订 `docs/V02_RESEARCH_PROPOSAL.md`（v2）**：
     - **假设拆分**：H-R（安全反转，方向性，单因素 + 联合）与 **H-I（非加性交互）** 分离；
       交互**主尺度 = 线性 `I_lin`**、次尺度 = 对数 `I_log`；新增"稳定反转判定门槛"与
       "反转 × 交互 2×2"关系表（§2）。
     - **终点结构**：**单一主终点 M1（连续最小前向 TTC）+ 关键次要 M2（固定序列门控）**，替代
       v1 co-primary，并论证理由（§3.2）；新增 **M1 五态处理**（T1 正常 / T2 无闭合速度→右截断 /
       T3 全程无候选→先验安全类别 + (a)(b) 敏感性 / T4 间歇候选 / T5 提前终止→终态事件 vs
       技术缺失），`None ≠ 安全`、不隐式插补（§3.4）。
     - **统计推断重设计**：声明**四条件标签不可交换**（固定 2² 析因内设计），**禁止锚内标签置换**，
       改用**锚级配对符号翻转/随机化检验**（依据扰动随机化，非标签交换；交互锐零 = 精确可加性）
       + 锚级 cluster bootstrap（与交换性解耦）+ **max-T 随机化**控制主族 FWER；保留"随机化正当性
       不足 → 纯估计"退路（§5、§8）。
     - **H2**：定义预注册**提名质量指标**（Q1 审计命中率 precision@k 为主；Q2 秩相关；Q3 regret；
       Q4 存活性），并把**方法比较降为辅助研究问题**（exploratory，不并入主族校正）（§2.4、§6.2）。
     - **扰动与门槛与预算**：P1–P4 逐项细化（对象/分布/界/耦合/可证伪点）；门槛扩为 **G0–G10**
       （新增 G0 扰动随机化正当性、G9 P3 合理性、G10 截断/缺失可接受）；新增**独立技术 pilot 预算**
       （**TP-1 = 288** 或 **TP-2 = 576** 真实 episode，仅 dev seed、单列、计入总预算、零 formal）；
       **明确正式样本量尚不能确定**并给出确定程序（§4、§7、§10）。
     - **事后性披露**：新增专节**显式承认** V02 设计受 V01 探索结果启发（零碰撞→连续主终点；
       负 ΔTTC→反转假设；种子退化→锚内扰动），并给出**七项事后选择风险控制措施**（§13）。
     - **重叠审查**：重写与 CornerCaseLab v0.3.0 的**逐要素重叠判定**——方法比较/独立审计/等预算配对
       **高重叠**（须显式归属、不作新颖点），**四条件反事实干预 / 安全反转 / 尺度显式交互**为
       **低重叠（候选新增点）**（§12）。
  2. **新增 `docs/V02_PROTOCOL_REVIEW_CHECKLIST.md`**：供人工逐项裁决的验收清单（A1–A7 对照表
     + B 结构性复核 + C 边界合规自检 + D 人工签署）。
- **证据/依据**：已安装依赖 `cornercaselab 0.3.0` 的 `METADATA` 与模块文档字符串（只读）；
  评审 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`。
- **边界**：零新 episode；未改 `safefliplab/` 任何模块；未改 `configs/formal_v01.json`（mtime 不变）；
  未删历史；未发 GitHub；未访问/修改旧 CornerCaseLab 项目目录；未宣布任何批准。
- **状态**：全部条目仍 **PROPOSED**，**待人工批准**；未选择主尺度/样本量/技术 pilot 方案。

## D26. V02 第三轮关键方法学纠错 + V02 离线工程准备（隔离、零真实 episode）

- **背景**：V02 提案外部复审"方向原则上通过、尚未批准协议冻结与真实实验"，指出六项关键方法学问题；
  并授权建立与 V01 隔离的 V02 离线开发区。
- **决定 A（仅文档纠错，见 `docs/V02_RESEARCH_PROPOSAL.md` §0.B）**：
  1. **撤回**"P1–P4 扰动随机化即保证锚级符号对称"的不充分论证；给出 sign-flip/max-T 适用条件
     **A/B/C**，在假设被证明/签字前**确证性检验一律 `PENDING`**、默认只报锚级估计与区间（§8.3/§8.3.1）。
  2. 新增 **§8.7**：区分 `E_pop`（总体 anchor 效应）与 `E_audit`（提名后 audit 效应），
     给 **POP-1 独立总体抽样 / POP-2 确认集** 方案。
  3. §6.2：H2 提名目标对齐**安全裕度反转**；Q1 改**反转命中率 precision@k**（废止任意 η）；
     全池指标标 `NOT_ESTIMABLE`；Q3 改 **π 内受限后悔**。
  4. §3.4 重构为 **TTC 三层**（逐 step / episode 汇总 / 终止）+ 配对缺失定义。
  5. §2.6 补"两单因素均改善但联合反转"格；§2.2 定义 `I_log` 定义域与原因码。
  6. §7.2 澄清开发种子集（TP-1 `[20261011]`；TP-2 第二枚 `PROPOSED_UNSET`）；
     §10 把 G3 拆为 **G3a（连续方差）/ G3b（碰撞事件率充分性）**。
- **决定 B（隔离工程准备）**：在 `D:\SafeFlipLab\v02\`（独立包 `v02lab`、仅标准库、不 import
  V01/上游仿真）实现：配置 schema 强制显式 status（杜绝任意默认）、四条件合法性与共享扰动与
  SHA256 派生纯函数、TTC 三层纯函数、独立 canonical 21 列账本、合成数据报告/统计接口
  （sign-flip/max-T 默认 `PENDING`）。**真实测试 93 项全过（exit 0，5.3 s）**，
  日志 `docs/V07_TEST_RESULTS_20261013.txt`；交付说明与**技术 pilot 前阻塞清单 B-01…B-12**
  见 `docs/V02_ENGINEERING_PREP_20261013.md`。清单更新见 `docs/V02_PROTOCOL_REVIEW_CHECKLIST.md`（A8–A13、E1–E8）。
- **边界**：**零真实 episode**（未运行 smoke/pilot/formal）；未改 `safefliplab/` 与
  `configs/formal_v01.json`（mtime 仍 Oct 12 12:13）；账本仍 530 行；未改写/访问旧 CornerCaseLab
  （`v02/` 不 import `cornercaselab`）；未发 GitHub；**未自行批准 TP-1/TP-2/formal**。
- **状态**：全部条目仍 **PROPOSED**；本轮交付物待人工逐项裁决；**未**解除阻塞清单。

## D27. 结构化输出补齐 + run_id 方法标签缺陷（F-06）修复（2026-10-15）

- **背景**：本轮执行《一次性执行总指令》，只读核验既有 A–G 成果后发现**两项真实缺口**：
  1. §6 要求的结构化产物 `episodes.csv/jsonl`、`anchors.csv`、`budget_summary.csv`、
     `comparisons.csv` **从未生成**（既有 `report --phase` 只产出 `*_quartets.csv`、
     `*_margins.csv`、`*_summary.json`、`*_report.md` 与图）；
  2. 新增 `episodes.csv` 后**首次暴露**一个既有缺陷：真实账本中 2 个 `run_id` 字符串内嵌的
     方法名与其 `method` 列不一致。
- **决定 A（补齐结构化输出，纯派生、零新 episode）**：扩展 `safefliplab/report.py`，
  新增 `_phase_episode_records` / `_anchor_records` / `_budget_records` / `_comparison_records`
  与 `write_structured_outputs`，由既有 `report --phase smoke|pilot` 一并写出五个新文件。
  全部数值仅来自真实账本与真实原始记录；**无数据时写"仅表头"空模板**，绝不填伪造值。
- **决定 B（缺陷认定与范围）**：**F-06（新发现）**。`run_smoke` 用**同一个** `PhaseDriver`
  （`method=METHOD_WIDE`）串行执行 WideExplore discovery 与 VerifyFirst stage-1 两类 job，
  而 `_new_run_id()` 原先取 `self.method`，因此 smoke 的 **2 个 VerifyFirst stage-1 quartet**
  的 `run_id` 被写成 `smoke_WideExplore_...`。
  - **权威判定证据（决定性）**：`sim_seed` 由 `SHA256` 派生且**包含 method**。
    实测该 run 的 `sim_seed = 1524636909`，`sim_seed_for(...,"VerifyFirst",...)` 复现一致，
    而 `"WideExplore"` 应为 `3812604799`。⇒ **账本 `method` 列正确，`run_id` 字符串错误**。
  - **全账本核验**：528 行全部与 `method` 列 `sim_seed` 一致（**0 处不一致**）；
    66 个 `run_id` 中**仅 2 个**标签错误（均在 smoke，均为 VerifyFirst stage-1）。
    pilot 的 64 个 `run_id` 全部正确；原始 episode JSON 的 `method` 字段亦为 `VerifyFirst`。
  - **影响面**：仅为**标识/命名**缺陷。所有碰撞 Y、`sim_seed`、锚、条件、统计量均不受影响；
    pilot 与 formal（每 method 独立 driver）不受影响。**不构成数据错误，也不改变任何已有结论。**
  - **处置**：`_new_run_id(method=None)` 改为接受显式方法，`execute_job` 传 `job.method`，
    smoke 重放路径显式传 `METHOD_WIDE`。
    **历史账本与原始记录一律不改写**（只增不覆盖），2 个错误 `run_id` 作为历史事实保留并在此披露。
- **决定 C（连带修复：未完成尝试不再隐形）**：写测试时发现 `load_phase_data` 只用
  `row_type=="outcome"` 构造状态视图，**只有 launch 行、没有 outcome 行的 episode
  （崩溃/断电/被杀）会被静默丢弃**，既不进 `incomplete` 也不进任何计数——而协议要求此类尝试
  "保守标 UNKNOWN 并视作预算已花"。已修复：launch 行若无对应 outcome，其条件状态记为
  `unknown` 并进入 `incomplete`（仍不计分、不插补、不当作安全）。
  对既有 smoke/pilot 数据**无任何影响**（264 个 episode 均有 outcome 行），仅补上真实缺口。
- **新增测试**：`tests/test_run_id_label.py`（5 项：run_id 方法标签、两方法并存、
  `sim_seed` 与 method 一致、直接执行 VerifyFirst job 的标签）；
  `tests/test_report_structured_outputs.py`（11 项：表头稳定、每 episode 一行、JSONL 与 CSV 一致、
  anchor 分母/比率自洽、预算 cap/unused、comparisons 不可计算时不填值、
  空数据仅表头、launch-only ⇒ `unknown` 且计费、未完成锚不进入打分）。
- **证据**：`docs/V09_TEST_RESULTS_20261015.txt`（全量单测）、
  `.workbuddy/tmp_audit/runid_audit_20261015.txt`（F-06 取证脚本输出）、
  `reports/{smoke,pilot}_episodes.csv|jsonl`、`*_anchors.csv`、`*_budget_summary.csv`、
  `*_comparisons.csv`。
- **边界**：**零新真实 episode**（未运行 smoke/pilot/formal）；未改 `configs/formal_v01.json`；
  未改历史账本行；未删任何历史数据（`reports/` 改动前已整体备份至
  `.workbuddy/backups/reports_pre_v08/`）；未发 GitHub；未访问/改动旧 CornerCaseLab。
- **状态**：D27 修复已落地并测试通过；**formal 仍需人工 GO**；D4/D5/D6 等 PROPOSED 条目**仍未批准**。
