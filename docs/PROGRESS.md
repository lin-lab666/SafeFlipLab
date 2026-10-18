# PROGRESS — SafeFlipLab 真实进度台账

> 本文件只记录**可核验**的事实：真实命令、退出码、测试数、真实 episode 计数。
> 未知项写 UNKNOWN / NOT DONE / BLOCKED，不推测成功。
> 最后更新：2026-10-15（GMT+8，结构化输出补齐 + F-06 缺陷修复轮）。

## 2026-10-15 结构化输出补齐 + F-06 缺陷修复（零新 episode）

- 目标：按《一次性执行总指令》逐项验收既有 A–G，补齐**真实缺口**。**本轮新增真实仿真预算 = 0 episodes**
  （未运行 smoke / pilot / formal）。
- **只读核验（真实命令，EXIT 0）**：
  - `python -m safefliplab doctor` → **17/17 PASS，VERDICT: GO**（证据 `docs/DOCTOR_20261015.txt`）。
  - `python -m unittest discover -s tests -v` → 基线 **Ran 209 tests, OK, EXIT 0**（240.6 s）；
    补齐后复跑 → **Ran 225 tests, OK, EXIT 0**（273.7 s）（证据 `docs/V09_TEST_RESULTS_20261015.txt`）。
  - 账本 `runs/episode_ledger.csv`：**528 数据行**（264 launch + 264 outcome），
    smoke 48 行 / pilot 480 行；全部 `completed`、`termination=goal`、`ego_collision=0`；
    表头为 **20 列旧式**（无 `budget_scope`）。与历轮记载吻合。
- **缺口 1（§6 结构化产物缺失）→ 已补齐（D27-A）**：`safefliplab/report.py` 新增
  `_phase_episode_records` / `_anchor_records` / `_budget_records` / `_comparison_records` /
  `write_structured_outputs`，由既有 `report --phase smoke|pilot` 一并写出：
  `{phase}_episodes.csv`、`{phase}_episodes.jsonl`、`{phase}_anchors.csv`、
  `{phase}_budget_summary.csv`、`{phase}_comparisons.csv`（无数据时**仅表头**，绝不填伪造值）。
  报告 markdown 增加「预算账附录」。
- **缺口 2（阶段 G 文档缺失）→ 已补齐**：新建 `docs/ACCEPTANCE_CHECKLIST.md`（逐项验收 +
  人工 GO/NO-GO 判据）与 `reports/pilot/REPORT.zh-CN.md`（真实 smoke/pilot 中文报告）。
- **新发现缺陷 F-06（既有，非本轮引入）→ 已修 + 已取证（D27-B）**：
  66 个 `run_id` 中 **2 个**（均在 smoke）内嵌标签为 `WideExplore`，而 `method` 列 / 原始 JSON
  为 `VerifyFirst`。**决定性判据**：`sim_seed` 为 SHA-256 且含 method，实测 `1524636909` 与
  `VerifyFirst` 一致（`WideExplore` 应为 `3812604799`）⇒ **`method` 列正确，`run_id` 字符串错**。
  全账本 **528/528 行 `sim_seed` 与 method 一致（0 处不一致）**；影响面仅 `run_id` 命名，
  Y 值/种子/锚/条件/统计量/pilot/formal 均不受影响。根因：`run_smoke` 用单一
  `PhaseDriver(method=METHOD_WIDE)` 串行跑两方法的 job，而 `_new_run_id()` 取 `self.method`。
  已改为显式传入 `job.method`（`_new_run_id(method)`）；**历史账本一行未改**，缺陷如实保留披露。
  证据：`.workbuddy/tmp_audit/runid_audit_20261015.txt`。
- **连带修复（D27-C）**：`load_phase_data` 原先只按 `outcome` 行建状态视图，
  **「只有 launch、无 outcome」的已计费尝试会被静默丢弃**（违反协议「保守标 UNKNOWN 且计费」）。
  已修复：此类尝试记 `unknown` 并进入 `incomplete`（仍不计分、不插补）；对既有 264 个
  episode（均有 outcome 行）**无任何影响**。
- **新增测试（+16）**：`tests/test_run_id_label.py`（5 项）、
  `tests/test_report_structured_outputs.py`（11 项）。全量 **209 → 225 全过，0 失败 0 错误**。
- **报告重新生成（零 episode，EXIT 0）**：`report --phase smoke` / `--phase pilot`。
  改动前 `reports/` 已整体备份至 `.workbuddy/backups/reports_pre_v08/`。
- **未做**：未运行 formal（12,800）；未重跑 smoke/pilot；未改 `configs/formal_v01.json`；
  未改历史账本任何行；未删历史数据；未改旧 CornerCaseLab；未发布 GitHub；未宣布任何批准。

## 2026-10-13 第二轮复审修订 + V02 研究设计轮（纯文档；零新 episode）

- 目标：修订评审报告的统计解释（R1/R2/R3），设计 formal 独立标准账本与 V02 预注册提案。
  **本轮新增真实仿真预算 = 0 episodes**；未改代码、未改冻结配置、未改账本/历史数据。
- **R1（rule of three 独立性假设）**：`INDEPENDENT_SCIENTIFIC_REVIEW.md §2.3` 撤回
  "每条件 60 episode 全零 ⇒ 95% 上界 ≈ 5%"。理由：rule of three 要求 iid Bernoulli，
  而锚内 repetition 非独立重采样、同 quartet 四条件共享配对种子、anchor 由确定性拒绝流生成。
  改为分层单元计数（episode 60 / anchor 15 / audit 3），**只作"0 次碰撞观测"描述**。
- **R2（VerifyFirst 排序键）**：修正 §2.1–2.2"tie-break 链从未被触发"的误述。
  逐键分解：stage-1 三枚 delta 键恒并列于 0（仅 `(first_seen, anchor_id)` 生效）；
  **最终提名 `valid_n` 是第一枚生效判别键**（stage-2 锚 `valid_n=4` vs 其余 `=1`，实测）。
- **R3（TTC 跨种子确定性范围）**：新增 §3.3.1，限定该结论仅对已采样 pilot 锚成立，
  不外推到 lead 非自由流 / ramp 更早并入的未来 anchor，亦不外推到碰撞事件。
- **L-01（formal 独立 21 列标准账本，PROPOSED）**：见 `docs/V02_RESEARCH_PROPOSAL.md §9`。
  方案：`runs/formal/episode_ledger.csv` 与旧账本**物理分离**、创建即 canonical 21 列表头、
  严格模式读取、固定行宽、schema 指纹、首行即含 `budget_scope`、旧账本只读不变。**未实现**。
- **V02 预注册提案（D24，PROPOSED）**：新增 `docs/V02_RESEARCH_PROPOSAL.md`——
  假设 H1–H4、连续前向安全裕度主终点（M1/M2）、有效锚内扰动 P1–P4（G4 前置验证）、
  四条件配对、独立审计、公平预算、锚级聚类统计、技术门槛 G1–G8、V01/V02 对比、
  与 CornerCaseLab v0.3.0 的贡献差异（此差异表述需人工核验）。**未实现任何 V02 代码**。
- **证据**：只读复核脚本 `.workbuddy/tmp_audit/rev_data.py` → `docs/REVISION_ANALYSIS_20261013.txt`
  （分层单元计数：WE discovery 15 锚 / VF discovery 6 锚 / audit 3 锚；VF `valid_n` = 4 与 1）。
- **未做**：formal、重跑 smoke/pilot、改冻结配置、删历史、发 GitHub、宣布批准、选择主指标、开始 V02 编程。

## 2026-10-13 独立科研审计轮（正式实验前最后验收；零新 episode）

- 目标：完成正式前的工程安全验收、科学审计与交接报告，完成后停止等待人工审核。
  本轮**新增真实仿真预算 = 0 episodes**（账本 528 行、原始 JSON 484 个、子目录 66 run 均未变）。
- **F-01 账本缺陷独立验收（D21）**：新增 `LedgerFormatError` + `resolve_fieldnames()` 表头
  兼容性校验（严格前缀→补齐；不兼容→安全拒绝）。新增 `tests/test_ledger_legacy_acceptance.py`
  （**15 项**）覆盖 6 场景：完整往返 / budget_scope 保存恢复 / 每 (method, seed) 独立预算 /
  多进程并发不超上限（8 进程 cap=3 → 恰 3 成功）/ 无免费重试 / 格式不兼容安全拒绝。
  独立证据脚本 `.workbuddy/tmp_audit/f01_acceptance.py` → `docs/F01_LEDGER_ACCEPTANCE_20261013.txt`。
  真实账本只读复核：`smoke=24 / pilot=240` 不变、文件字节数不变。
- **图表标题溢出修复（D22/F-05）**：`report.py` 新增 `_wrap_title()` + `bbox_inches="tight"`；
  再验收四图：无 `1e−17` 偏移、点估计图不冒充置信区间森林图、标题完整不裁切、
  图 4 标注 `NON-PROTOCOL`。新增 `tests/test_figure_axes.py::TestTitleWrap`（**4 项**）。
- **全量测试**：`python -m unittest discover -s tests -v` → **Ran 209 tests, OK（0 failures /
  0 errors），EXIT 0，47.4 s**（190 旧 + 19 新）。证据 `docs/V06_TEST_RESULTS_20261013.txt`。
- `python -m safefliplab doctor` → **17/17 PASS，VERDICT: GO**（证据 `docs/DOCTOR_20261013.txt`）。
- **科学审计结论**（详见 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`）：工程可靠性 GO；
  协议合规性 CONDITIONAL GO（PD-01 +220 待接受、D4/D5/D6 待批）；科研可行性
  **对 formal 执行为 NO-GO**（零碰撞致主指标零方差、两方法提名退化不可区分、
  repetition 不重采样 ego–lead 交互、ΔTTC 为确定性属性非风险反转）。
- **未做**：未运行 formal 12,800；未重跑 smoke/pilot；未改冻结配置；未删历史原始数据；
  未改旧 CornerCaseLab；未发布 GitHub；未宣布任何批准；未选择 V01/V02 方案。

## 2026-10-13 接续核验轮（只读核验 + 零新 episode 的探索性分析）

- 核验方式：完整读取 Word 任务书与 Markdown 执行说明；只读检查目录/源码/账本/报告；
  重跑 doctor 与全部单元测试；抽查原始 episode JSON。**未启动任何新真实 episode**。
- `python -m safefliplab doctor`：**17/17 PASS，VERDICT: GO**（与记载一致）。
- 单元测试：`python -m unittest discover -s tests` →
  **Ran 169 tests, OK（0 failures / 0 errors），EXIT 0**（2026-10-13 重跑确认）。
  注：PROGRESS 旧版"146"为过期口径；权威最新计数为 V04_TEST_RESULTS.txt 与本轮的 169。
  本轮新增 `tests/test_margins.py`（14 项）后总计 **183**（本轮末尾已重跑确认，见下）。
- 账本核验（权威 `runs/episode_ledger.csv`）：**528 数据行 = 264 episodes × 2 行**
  （launch 264 + outcome 264）；smoke 24（WideExplore 16 / VerifyFirst 8）+
  pilot 240（WideExplore 120 / VerifyFirst 120；discovery 120 / audit 120）；
  全部 completed、0 错误 0 中断、全部 `ego_collision=0`；66 个唯一 run_id。
  与首次无效 pilot 的备份（`runs/episode_ledger.csv.buggy_pilot_run1`，489 行）相互独立。
- 原始证据抽查：`runs/<run_id>/anchor-*.json` 含完整 trajectory、`policy_steps`、
  `reward_sum`、`min_forward_ttc_sampled_s`、`trace_sha256_rounded_9dp`，
  adapter 指纹为 cornercaselab 0.3.0 + highway-env 1.10.2 + gymnasium 1.2.2
  + policy=boundary + 25 s / 15 Hz / 5 Hz —— **真实 HighwayEnv 输出，非 mock**。
- Git：`D:\SafeFlipLab` **不是 git 仓库**（`git status` 报 not a git repository）。
  历史从未提交；按交接手册"如有 Git 记录 commit，不要重写历史"，无 Git 可记，
  本轮也未擅自 `git init`（不自动发布要求不变）。
- 新增工作（D20，见 DECISION_LOG）：`safefliplab/margins.py` 探索性连续安全裕度分析
  （只重读已付费原始记录，**零新 episode**）；`report.py` 增加"探索性连续安全裕度分析"
  一节与第 4 张图；`tests/test_margins.py` 14 项全通过；smoke/pilot 报告已重新生成
  （旧版备份为 `reports/*.pre_margin_backup`）。
- **未做**：未启动任何 smoke/pilot/formal；未运行 12,800；未发布 GitHub；未改旧 CornerCaseLab；
  未修改 `configs/formal_v01.json` 与任何冻结规则。

## 阶段 A｜只读核查（DONE）

- 环境（真实输出）：
  - Python 3.13.14（项目 venv `D:\SafeFlipLab\.venv`，基于托管 Python 3.13.12）
  - Node v22.22.2；Git 2.55.0.windows.3；Windows（win32）
- cornercaselab **不在 PyPI**（已核验 Not Found）；GitHub tag v0.3.0 存在，
  已安装进 venv：cornercaselab 0.3.0、highway-env 1.10.2、gymnasium 1.2.2、
  numpy 2.5.4、pillow 12.3.0、matplotlib 3.11.2、pygame 2.6.1。
- 场景 schema 已核实：`merge-scenario-v1` 六维；
  `front_gap ∈ [18,80]`、`ego_speed ∈ [20,32]` 均为真实字段（不假设）。
- `policy=boundary` 控制器已核实存在（gap 6.0 / headway 0.30 / TTC 0.90）。
- 碰撞观察已核实：`ego_collision = env.vehicle.crashed`。
- HighwayEnv 环境构建验证通过（未 reset，未启动任何 episode）。
- 文献核查：6 项可验证链接写入 `docs/RELATED_WORK.md`
  （反事实安全边际 / planner avoidability / 变形测试 ×2 / 仿真鲁棒性 ×2 /
  RSS ×2）。未逐字阅读全文的条目已标注。
- `python -m safefliplab doctor`：**17/17 PASS，VERDICT: GO**（零 episode）。

## 阶段 B｜工程骨架（DONE）

- 目录：`safefliplab/ configs/ scripts/ tests/ reports/ docs/ runs/`
  + `README.md` `README.zh-CN.md` `LICENSE`（Apache-2.0）`CITATION.cff`
  `.gitignore` `pyproject.toml` `requirements.txt`。
- 项目局部 Python 3.13 venv；未改系统 Python、未用管理员权限、未改 ACL。

## 阶段 C｜仿真适配与账本（DONE）

- `adapter.py`（接口验证 + 冻结 fingerprint）、`generator.py`（共享 anchor 流，
  拒绝采样，`stream_draws` 可审计）、`runner.py`（启动前计费、原始 JSON 落盘）、
  `ledger.py`（launch/outcome 两行式、只追加、fsync、阶段预算）。
- 四条件唯一性、配对 sim_seed、无裁剪、错误/中断计费均有单元测试。

## 阶段 D｜两种方法（DONE，含 PROPOSED 规则待批）

- `methods.py`：WideExplore / VerifyFirst / 独立审计 / 冻结 tie-break；
  正式计划精确闭合 800/800（`validate_formal_plans` 测试通过）。
- PROPOSED 规则（D4/D5/D6）写入 `docs/DECISION_LOG.md`，**未经用户批准**。

## 阶段 E｜统计报告（DONE）

- `stats.py`（delta/interaction/reverse/rescue，空结果返回 None 而非 0）；
  `report.py`（三类图仅在有真实数据时生成；无数据明示不出图）。

## 阶段 F｜测试与真实试验（DONE）

- 单元测试（**最新，权威口径**）：`python -m unittest discover -s tests` →
  **Ran 225 tests, OK（0 failures / 0 errors），EXIT 0**（2026-10-15 补齐结构化输出与 F-06 回归后复跑）。
  历史里程碑：98 → 106（D12 跨 seed 隔离）→ 146（D13–D16 账本/调度/安全门/配置校验）
  → 169（D17–D19，见 V04_TEST_RESULTS.txt）→ 183（D20 margins，2026-10-13 接续核验轮）
  → 189 → 190（F-01/F-02/F-03 修复）→ 209（F-01 独立验收 15 项 + 标题换行 4 项）
  → **225**（D27：run_id 标签回归 5 项 + 结构化产物 11 项，见 V09_TEST_RESULTS_20261015.txt）。
  注：测试墙钟随机器负载在 ~50 s–9 min 波动，绝大部分是 Windows 上 `fsync` + 临时目录删除的
  环境性缓慢，与代码无关。
- 测试不启动任何真实 episode（FakeAdapter 仅存在于 tests/）。
- smoke（≤24 真实 episodes）：**DONE（真实 HighwayEnv，24/24，0 错误 0 中断）**。
  详细结果见下方「真实实验结果」与 `reports/smoke_report.md`、`runs/manifest_smoke_WideExplore.json`。
- pilot（≤240 真实 episodes）：**DONE（修复阶段隔离 bug 后重跑，真实 HighwayEnv，240/240，0 错误 0 中断）**。
  详见下方「真实实验结果」与 `reports/pilot_report.md`、三张图、`runs/manifest_pilot_summary.json`。
- formal：**未获授权、未运行**（代码已实现但被本构建拒绝执行，见 cli.py `cmd_formal`）。

## 阶段 G｜交接（DONE，2026-10-15 补齐）

- `docs/OWNER_GUIDE.zh-CN.md`、`docs/LATEST_HANDOFF.md` 随 smoke/pilot 结果定稿。
- **2026-10-15 补齐两项缺失交付物**：`docs/ACCEPTANCE_CHECKLIST.md`（逐项验收 +
  人工 GO/NO-GO 判据）与 `reports/pilot/REPORT.zh-CN.md`（真实 smoke/pilot 中文报告，
  含负结果与局限）。
- 阶段 G 交付物现齐全：PROGRESS / LATEST_HANDOFF / DECISION_LOG（D1–D27）/ PROTOCOL_V01 /
  ACCEPTANCE_CHECKLIST / RELATED_WORK / OWNER_GUIDE / README.zh-CN / README。

## 阶段 F 续｜跨 master_seed 隔离修复（DONE，2026-10-12 接续轮）

- 前序正式前静态审计（`docs/FINAL_PRE_FORMAL_AUDIT.md §5.4`）发现 D11 相位隔离**不足以支撑
  正式多 seed**：resume 隔离键缺 `master_seed`，8 个 formal seed 共享账本会彼此误复用 quartet。
- 修复 `safefliplab/experiments.py`：隔离键升级为 5 元组
  `(master_seed, method, anchor_index, repetition, stream)`；`_index_completed` / `_note_outcome`
  新增 `master_seed` 过滤（叠加既有 `phase` 过滤）。详见 `docs/DECISION_LOG.md D12`。
- 新增 `tests/test_experiments.py::TestMasterSeedIsolation`（**8 项**，全用 FakeAdapter，零真实
  episode），覆盖跨 seed 隔离、同 seed 合法恢复、force 重跑、launch-only、error、不同 run_id、
  预算耗尽等路径。既有 `TestPhaseIsolation` 因键形变更同步更新。
- 单元测试：**98 → 106 全通过**（0 失败 0 错误，约 7.5 s，零真实 episode）。
- `python -m safefliplab doctor` 仍 **17/17 PASS，VERDICT: GO**；正式 CLI 锁（`--confirm` +
  `--max-episodes 12800` 才放行、之后仍 `RuntimeError` 不真跑）**未改动**，正式不可启动保护完整保留。
- **未做**：未启动任何真实 smoke/pilot/formal；未运行正式 12800；未发布 GitHub；未改动旧 CornerCaseLab。

## 阶段 F 续2｜正式调度补齐与安全加固（DONE，2026-10-12 本轮）

依独立源码审查，完成 D13–D16（详见 `docs/DECISION_LOG.md`），全部为静态代码 + FakeAdapter 单测，
**零真实 episode**：

- **D13 账本安全（`ledger.py`）**：`reserve_launch` 原子化"预算检查+去重+计费"；`DuplicateLaunch`
  在仿真前拒绝重复 key；新账本仅写表头（不再有空数据行）并提供 `empty_data_rows()/diagnose()`
  兼容核对；新增 `budget_scope` 列与 `launched_count_scope()` 支持 formal 的
  `formal|method|master_seed` 独立计费。runner 改用 `reserve_launch`。
- **D14 正式调度与结果记录（`experiments.py`）**：补齐 `_execute_formal_phase`（8 seed × 2 method，
  每 method×seed 800）；预算判别改为**累计作用域预算**并单记 `new_episodes_this_call`
  （废弃会误报的 `after−before==800`）；`_records_for(stream=...)` 修复 **audit 混流**；
  `run_pilot` 汇总改用**重新打开的持久化账本**；每 (seed, method) 独立 manifest 不覆盖。
- **D15 正式执行安全门（`experiments.py`）**：`_require_formal_go` 置于所有正式执行入口——
  未获 `human_go=True` 时，非测试替身（含 `adapter=None`）在构造任何仿真器**之前**抛
  `PermissionError`；`FakeAdapter` 加 `is_test_double=True` 保留离线测试能力。
- **D16 正式配置冻结漂移校验（`protocol.py`）**：`validate_formal_config` 校验种子数量/唯一性/
  整型/冻结值/顺序/协议指纹与 budget/plan/simulator 冻结值；`_execute_formal_phase` 严格模式强制。
  **未修改** `configs/formal_v01.json`。
- **新增测试**：`tests/test_formal_scheduling.py`（多 seed 调度、分阶段/半程/全程恢复、累计预算、
  审计隔离、主种子隔离、重复启动、manifest 不覆盖、安全门、CLI 锁），
  `tests/test_ledger_safety.py`（原子预占、去重、作用域、空行兼容、resume 重开账本），
  `tests/test_formal_config.py`（真实配置合法 + 各类漂移拒绝）。
- **单元测试：106 → 146 全通过**；`doctor` 仍 **17/17 PASS, VERDICT: GO**；正式 CLI 锁
  （`formal` 仍抛 `RuntimeError`，`--confirm --max-episodes 12800` 亦不真正运行）**未解除**。
- **未做**：未启动任何真实 smoke/pilot/formal；未发布 GitHub；未改旧 CornerCaseLab。

## 真实实验结果（smoke，已核验）

- 命令：`python -m safefliplab smoke --max-episodes 24`（接管前由前序模型启动，已正常结束，EXIT 0）
- 真实记账（权威：`runs/episode_ledger.csv`）：
  - 发起 24 / 完成 24 / 错误 0 / 中断 0 —— 恰好用满 24 上限。
  - 方法分布：WideExplore 4 个 quartet（anchor 0/1/2 + 同种子重放 anchor 0）、
    VerifyFirst 2 个 quartet（anchor 0/1）。
  - 全部 `ego_collision=0`（各锚均抵达目标，无本车碰撞）。
- 仿真来源：manifest 指纹确认 `cornercaselab 0.3.0` + `highway-env 1.10.2` + `gymnasium 1.2.2` +
  `policy=boundary` + 25 s 时域 + 15/5 Hz；原始 episode JSON 含 `policy_steps/reward_sum/
  min_forward_ttc_sampled_s/trace_sha256`，系**真实 HighwayEnv** 输出，非 mock。
- 确定性重放：WideExplore anchor-0 同种子（sim_seed 3812604799）两次运行，
  `manifest.determinism_check.all_conditions_match = true`，四条件 `trace_sha256` 完全一致。
- 报告：`reports/smoke_report.md`、`reports/smoke_quartets.csv`、两张图（四条件配对 / 森林图），
  `report --phase smoke` 返回 `status: OK`。

## 真实实验结果（pilot，修复后重跑，已核验）

> ⚠️ 首次 pilot 运行存在**阶段隔离 bug**：`PhaseDriver.completed_quartets()` 未按 `phase` 过滤，
> 误把 smoke 已完成且 (method,anchor,rep,stream) key 相同的 quartet 当作“已完成”，
> 跳过 WideExplore 0/1/2、VerifyFirst 0/1 共 5 个 discovery quartet，仅发起 220 episodes（无效）。
> 该运行已移入 `runs/_buggy_pilot_run1/` 与 `runs/episode_ledger.csv.buggy_pilot_run1` 审计留痕。
> 修复（按 phase 隔离）后**重新干净运行**得到下方有效结果。

- 命令：`python -m safefliplab pilot --max-episodes 240`（修复后重跑，EXIT 0，~2m59s）
- 真实记账（权威：`runs/episode_ledger.csv`）：
  - 发起 **240 / 完成 240 / 错误 0 / 中断 0** —— 恰好用满 240 上限。
  - 方法平衡：WideExplore 120 / VerifyFirst 120；discovery 120 / audit 120。
  - quartets 60（每 (method,stream) 恰好 15）；WideExplore discovery 锚 0–14 全覆盖、VerifyFirst 0–5。
  - 全部 240 completed 的 `ego_collision=0`（dev_seed 样本下两种干预均未致本车碰撞）。
- 提名（真实）：WideExplore discovery 提名 anchor-0000/0001/0002；VerifyFirst 选 3 = 同；各 audit 3 提名×5。
- 报告：`reports/pilot_report.md`、`reports/pilot_quartets.csv`、三张图、`reports/pilot_summary.json`、
  `runs/manifest_pilot_summary.json`，`report --phase pilot` 返回 `status: OK`。
- 本 pilot 数字为**描述性/管道验证**，dev_seed 非正式证据，不得外推。

## 预算总账（真实）

| 阶段 | 上限 | 有效已发起 | 成功 | 错误 | 中断 |
|---|---:|---:|---:|---:|---:|
| smoke | 24 | 24 | 24 | 0 | 0 |
| pilot | 240 | 240 | 240 | 0 | 0 |
| formal | 12800 | 0 | 0 | 0 | 0 |

（本表在每次真实运行后更新；权威计数以 `runs/episode_ledger.csv` 为准。首次无效 pilot 的 220
episodes 已隔离备份、不计入有效证据。）

## 待办 / 阻塞

1. **BLOCKER-2（合规，未解除）**：D4/D5/D6 仍为 **PROPOSED**，需用户书面批准后才能进入 formal。
2. **BLOCKER-3（研究，未解除）**：零碰撞/低事件率风险待人工裁决：见
   `docs/FORMAL_READINESS_V03.md` 与 `docs/FINAL_PRE_FORMAL_AUDIT.md §4.5`——现有 66 个完整
   quartet 全部零碰撞，但 100% 在 TTC/奖励/轨迹上仍可观察条件差异（"全零碰撞"≠"无可见差异"）。
   **2026-10-13 更新（D20）**：新增零预算消耗的探索性连续安全裕度分析，从已付费原始记录中提取
   ΔTTC 配对差：pilot 全部 4 个 (method, stream) 组 mean ΔTTC(both) 均为负
   （−0.0383 ~ −0.2158），方向一致但样本小、单 dev_seed，仅供人工裁决参考，**不构成正式证据**。
   是否将连续裕度指标纳入 formal 前的裁决清单，需人工决定（PROPOSED，未批准）。
3. **BLOCKER-1（技术）状态更新**：D12 修复跨 master_seed 隔离后，本轮 D13–D16 进一步加固账本
   原子性、正式调度累计预算、正式执行安全门与配置冻结漂移校验；169 单测全通过。**待人工复核
   D13–D16 方案与回归测试后正式关闭**。
4. formal 需显式人工 GO；本构建不自动运行、不发布 GitHub；正式 CLI 锁保留。
5. **PD-01（pilot 累计 460，超上限 220）** 已披露并保留于预算总账，不得通过重定义预算掩盖。
