# SafeFlipLab 所有者指南（中文）

> 面向接手本项目的人（或未来的你）。读完本文件即可独立运行、复核、扩展 SafeFlipLab。
> 所有结论以 `runs/episode_ledger.csv`、原始 episode 文件、`reports/` 与 `docs/` 中的真实记录为准。
> 本指南不替代任务书与续接手册，仅作工程上手速查。

---

## 0. 这是什么

SafeFlipLab 研究**反事实安全裕度**：在高速公路合流场景中，主动给本车施加两个不同的"反事实干预"，
观察**本车自身碰撞率**如何变化。核心科学问题是——**放大本车安全裕度，是否反而增加本车碰撞**？

- 干预 A（增隙）：`front_gap += 2.0 m`
- 干预 B（减速）：`ego_speed -= 1.0 m/s`
- 四条件：`00`（原场景）、`10`（仅增隙）、`01`（仅减速）、`11`（两者皆施）
- 两方法：**WideExplore**（广撒网、按效应量提名 audit）与 **VerifyFirst**（先聚焦、冻结 20 个候选再深挖）
- 冻结仿真：`cornercaselab 0.3.0` → `highway-env 1.10.2` + `gymnasium 1.2.2`，控制器 `policy=boundary`，
  时域 25 s、仿真 15 Hz、策略 5 Hz。

观察者变量是 `ego_collision = env.vehicle.crashed`（本车撞上任意对象）。

---

## 1. 环境

- Windows + Python 3.13（项目局部 venv：`D:\SafeFlipLab\.venv`，基于托管 3.13.12）。
- 激活：`D:\SafeFlipLab\.venv\Scripts\python.exe`
- 依赖已装：`cornercaselab==0.3.0`（git 安装）、`highway-env==1.10.2`、`gymnasium==1.2.2`、
  `numpy<3`、`Pillow<13`、`matplotlib<4`。**未修改系统 Python、未用管理员权限**。
- 不要升级 `cornercaselab` 主版本——0.3.0 的接口与任务书冻结的 schema 绑定。

运行任何真实 episode 前先跑：
```
python -m safefliplab doctor
```
它只读校验环境/接口/场景 schema/控制器/碰撞字段，**不启动任何 episode**。必须 `VERDICT: GO` 才继续。

---

## 2. 四条命令

| 命令 | 真实 episode | 用途 |
|---|---:|---|
| `python -m safefliplab doctor` | 0 | 只读环境校验 |
| `python -m safefliplab smoke --max-episodes 24` | ≤24 | 管道端到端校验（真实 HighwayEnv） |
| `python -m safefliplab pilot --max-episodes 240` | ≤240 | 结构缩放版验证（**非**正式证据） |
| `python -m safefliplab report --phase <smoke\|pilot\|formal>` | 0 | 由真实账本生成报告+CSV+图 |
| `python -m safefliplab formal --confirm --max-episodes 12800` | ≤12800 | **已实现但被本构建拒绝执行**，需人工 GO |

- `smoke`/`pilot` 的 `--max-episodes` 只可 <= 上限，超过直接拒绝（退出码 2）。
- `formal` 必须**同时**传 `--confirm` 与 `--max-episodes 12800`，否则拒绝执行、零 episode。
  当前代码在收到两标志后仍会抛 `RuntimeError`（"已实现但未执行"），即**不会真的跑 12800**。
- **正式执行双层保护**：(a) CLI 锁 `run_formal`/`run_formal_phase` 始终抛 `RuntimeError`；
  (b) **独立安全门** `_require_formal_go` 置于所有正式执行入口——任何直接调用 `_execute_formal_phase`
  的代码，若未显式传 `human_go=True` 且适配器不是测试替身（`is_test_double=True`），都会在构造
  任何仿真器**之前**抛 `PermissionError`。因此 `adapter=None` 永远不会在无人工 GO 时启动真实仿真。

---

## 3. 预算规则（不可突破）

| 阶段 | 上限 | 说明 |
|---|---:|---|
| smoke | 24 | 12(3 个 WideExplore discovery) + 8(2 个 VerifyFirst stage-1) + 4(同种子重放 WideExplore 锚 0) |
| pilot | 240 | 每方法 120：WideExplore 15+3×5；VerifyFirst 6+3×3+3×5（精确闭合 240，无部分计划） |
| formal | 12800 | 8 个 master seed × 2 方法 × 800，冻结于 `configs/formal_v01.json` |

硬规则（见 `docs/PROTOCOL_V01.md` 与 `docs/DECISION_LOG.md`）：

1. **启动即计费（原子）**：`runner` 在 `make_environment`/`reset` 之前调用 `ledger.reserve_launch`，
   它在**同一把锁**内完成"预算检查 + 重复拒绝 + 计费写入"，杜绝并发/重复启动绕过上限。
2. **失败/中断都计费**：`error`、`interrupted` 同样占预算，且**绝不自动重试**——重试必须重新计费。
   重复 `episode_key` 在仿真前被 `DuplicateLaunch` 拒绝（杜绝"实际启动多次只计费一次"）。
3. **账本只追加、不可变**：`runs/episode_ledger.csv` 的两行式（launch+outcome）是预算权威来源。
   新账本仅写表头（无空数据行）；旧账本可兼容读取并 `diagnose()` 独立核对。
4. **断点恢复基于证据**：重跑同一命令时，已完成的 quartet 直接复用账本中的真实 Y，
   不重新发起、不虚构；未完成/失败的 job 才重新发起并重新计费。
   **隔离维度**：复用判定同时按 `phase` 与 `master_seed` 过滤（`experiments.py` 的 resume 隔离键为
   5 元组 `(master_seed, method, anchor_index, repetition, stream)`）。这保证正式阶段 8 个 master seed
   各自独立产生观测、互不误复用（`TestMasterSeedIsolation` 覆盖）。
   **计费维度**：formal 以 `budget_scope = formal|method|master_seed` 独立计费；恢复时按**累计**作用域
   预算（=800）验证，并另记本次新增次数（不因合法恢复而误报）。
5. **确定性重放检查**：smoke 同种子重放同一 quartet，比对 `trace_sha256_rounded_9dp`，必须完全一致。
6. **正式配置冻结校验**：真实运行前 `validate_formal_config` 校验种子数量/唯一性/冻结值/顺序/协议指纹
   与 budget/plan/simulator 冻结值（`safefliplab/protocol.py`），防止误改研究设计。

---

## 4. 目录与产物

```
D:\SafeFlipLab\
  safefliplab/        包源码（adapter/domain/generator/runner/ledger/methods/stats/report/protocol/experiments/margins/cli）
  configs/            dev_v01.json（smoke+pilot，dev_seed 非证据）、formal_v01.json（冻结，未执行）
  tests/              227 个单元测试（FakeAdapter/合成数据，零真实 episode）；`python -m unittest discover -s tests`
  reports/            smoke_report.md / pilot_report.md / *_quartets.csv / *_margins.csv / <phase>/figure_*.png
                      / *_episodes.csv|jsonl / *_anchors.csv / *_budget_summary.csv / *_comparisons.csv
                      / pilot/REPORT.zh-CN.md
  runs/               episode_ledger.csv（权威账本）+ 每 run 的原始 episode JSON + manifest_*.json
  docs/               PROTOCOL_V01 / DECISION_LOG（D1–D27）/ PROGRESS / RELATED_WORK / PROVENANCE / ATTRIBUTION /
                      OWNER_GUIDE / LATEST_HANDOFF / ACCEPTANCE_CHECKLIST / FORMAL_READINESS_V02–V04
```

每个原始 episode 文件含：`adapter_fingerprint`、`anchor`+`stream_draws`、`conditioned_scenario`、
`result`（ego_collision、goal_reached、min_forward_ttc_sampled_s、policy_steps、sim_time_s、
termination、trajectory、trace_sha256_rounded_9dp）。**这是真实 HighwayEnv 输出**，不是 mock。

`safefliplab/margins.py` 是**探索性、非协议**的连续安全裕度分析（D20）：只重读账本
`raw_path` 指向的已存在原始记录（不启动任何新仿真），按与主统计完全相同的 quartet 隔离规则
计算 `min_forward_ttc_sampled_s` 等连续量的配对差，输出到报告的"探索性连续安全裕度分析"章节、
`reports/<phase>_margins.csv` 与 `figure_4_margin_forest_ttc.png`。负 ΔTTC 表示更接近碰撞
但不等于碰撞；不得作为正式证据。

**§6 结构化产物（2026-10-15 补齐，D27-A）**：`report --phase <phase>` 除上述文件外还会写出五类
结构化输出，全部由 `safefliplab/report.py` 的 `write_structured_outputs()` 从**真实账本与真实原始记录**
聚合，**无数据时只写表头空模板，绝不填伪造值**：

| 文件 | 内容 | 怎么用 |
|---|---|---|
| `<phase>_episodes.csv` / `.jsonl` | 每个**已计费** episode 一行（含 run_id、方法、锚、repetition、条件、`sim_seed`、`exit_status`、`ego_collision`、`raw_path`、`billed`） | 逐条核对；`result_recorded=0` 表示发起后无结果（保守记为 `unknown`，仍计费） |
| `<phase>_anchors.csv` | 每 (master_seed, method, stream, anchor) 的四条件碰撞计数、分母、比率与四个配对差值 | 看单锚风险差；`denominator == n_complete_quartets`，不完整锚 `denominator=0` 且比率留空 |
| `<phase>_budget_summary.csv` | 每预算作用域的 cap / launched / completed / error / interrupted / pending-unknown / unused | 核账；失败与未知同样计费 |
| `<phase>_comparisons.csv` | 每 master_seed 的方法对比（审计锚平均 `delta_both` 及 `VerifyFirst − WideExplore`） | `metric_role=PROTOCOL_AUDIT` 才是协议指标；`computable=0` 时对比列留空 |
| `<phase>_quartets.csv` | 完整**主** quartet 明细（重放与不完整另记） | 主统计的来源 |

**F-06 提示（2026-10-15）**：真实 smoke 账本中有 **2 个 `run_id` 字符串**内嵌方法名写作
`WideExplore`，而 `method` 列与 `sim_seed` 均为 `VerifyFirst`。以 `method` 列为准
（`sim_seed` 为 SHA-256 且含 method，可独立复现）。已修复产生该标签的代码；历史账本按
「只增不覆盖」保留原样。取证见 `.workbuddy/tmp_audit/runid_audit_20261015.txt`。


---

## 5. 真实结果如何复核（三步走）

1. 看账本：`python -c "import csv; rows=list(csv.DictReader(open('runs/episode_ledger.csv'))); ..."`
   或读 `runs/manifest_<phase>_<method>.json` 的 `episodes_launched_phase_total` / `_completed` / `_errored`。
2. 看原始文件：抽查 `runs/<run_id>/anchor-*.json` 的 `result.ego_collision` 与 `trace_sha256_rounded_9dp`。
3. 看报告：`python -m safefliplab report --phase <phase>` 后读 `reports/<phase>_report.md`。

**核对清单**：四条件是否齐全（00/10/01/11）？同 quartet 是否共享 sim_seed？碰撞字段是否来自真实环境？
预算是否恰好用满而不超？失败/中断是否计入？

---

## 6. 待你拍板的事项（PROPOSED，未经批准不得进入 formal）

写在 `docs/DECISION_LOG.md`：
- **D4** sim_seed 完整映射（任务书只要求"四条件共享、稳定派生"，未给全映射）。
- **D5** tie-break 两单因素的顺序与方向（WideExplore 提名已由任务书给定；VerifyFirst 选 20 与最终
  提名的完整次序为 PROPOSED）。
- **D6** pilot 内部配额（结构缩放，非任务书精确定义）。
- **D10** 有效样本数在提名中的权重、pilot 审计 quartet 数（5）远小于正式（20）导致审计证据有限。
- **D20**（2026-10-13 新增）探索性连续安全裕度分析：是否将其结论纳入 formal GO 前的裁决清单
  （例如是否在 formal 预注册 TTC 等次要终点）——需人工决定；**当前状态：仅描述性参考，未批准**。

`formal` 的 8 个 master seed 已在 `configs/formal_v01.json` 冻结，且由
`SHA256(canonical_json(['SafeFlipLab-v01','formal-master',i]))` 派生，**不是**从任何结果里挑的。

---

## 7. 扩展 / 修改须知

- 改场景 schema、控制器、时域 → 必须同步更新 `safefliplab/adapter.py` 的冻结 `fingerprint()`，
  并重新跑 `doctor`。换版本=换研究协议，需重新走审批。
- 加新方法/新条件 → 改 `safefliplab/methods.py` 与 `safefliplab/domain.py`，并补测试（`tests/`）。
- 任何会改动预算计数的逻辑 → 必须有 `tests/test_ledger.py` / `tests/test_ledger_safety.py` /
  `tests/test_experiments.py` / `tests/test_formal_scheduling.py` 覆盖。
- 改动正式研究设计（预算/计划/节奏/种子）→ 必须同步 `safefliplab/protocol.py` 的 `FROZEN_DESIGN`
  与 `configs/formal_v01.json`，否则 `validate_formal_config` 会拒绝、`tests/test_formal_config.py` 会失败。
  注意 8 个 master seed 是 SHA-256 派生**冻结值**，不得手改。
- **绝不**改动旧 `CornerCaseLab` 项目；本项目的所有改动都在 `D:\SafeFlipLab`。

---

## 8. 常见坑

- Windows 临时目录删除慢（实测删 ~240 小文件 ≈ 29 s），会让 `tests` 整体墙钟偏长——与代码无关，
  真实 run 写 `D:\SafeFlipLab\runs`（持久），不受影响。
- `smoke` 的 run_id 前缀统一为 `smoke_WideExplore_...`（因 `run_smoke` 复用单个 WideExplore driver 跑
  两种方法的 job）；账本 `method` 列才是真实方法（WideExplore / VerifyFirst），以账本为准。
- 报告里四条件碰撞率全 0 不代表"安全"——只代表该样本下无人撞；结论是分条件、分 anchor 比较出来的。
- **"全零碰撞" ≠ "四条件无可见差异"**：现有 66 个完整 quartet 全部零碰撞，但 100% 在 TTC / 奖励 /
  轨迹哈希上仍可观察条件差异（front_gap+2.0、ego_speed−1.0 确实改变了轨迹与控制行为）。正式阶段若
  碰撞基线率仍近 0，应把 TTC / 近撞等次要终点也纳入预注册分析，而非仅看碰撞率。
  2026-10-13 的探索性分析（D20，`reports/*_margins.csv`）显示 pilot 全部 4 个 (method, stream) 组
  的 mean ΔTTC(both) 均为负——连续裕度上方向一致地"反向"，但单 dev_seed、样本小，仅作人工裁决参考。
