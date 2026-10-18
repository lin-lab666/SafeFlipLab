# SafeFlipLab — FINAL CLOSEOUT（离线结题交付报告）

**日期**：2026-10-16（GMT+8）　│　**执行者**：WorkBuddy（首席工程师 / 科研实现负责人 / 最终交付负责人）
**项目根**：`D:\SafeFlipLab`　│　**V01 有效账本**：`runs/episode_ledger.csv`　│　**V02**：`v02/`
**授权依据**：《SafeFlipLab｜自主完成结题任务——执行 AI 总指令》
**本轮新增真实仿真**：**0**　│　**未启动 formal**　│　**未重跑 smoke/pilot**　│　**未改历史账本**

---

## 0. 结论：**具备离线工程结题条件 = YES**

| 判定项 | 结果 |
|---|---|
| 工程验收 | **PASS** |
| 账本对账 | **PASS**（V01/V02 各自账本 ↔ 磁盘双向 1:1；孤儿行 0） |
| 科研判定 | **全部假设 INCONCLUSIVE / NOT ESTABLISHED**（如实负结果） |
| 测试 | **V01 227/227 OK；V02 143/143 OK**（均 EXIT 0） |
| doctor | **V01 17/17 GO；V02 7/7 GO** |
| 独立复算 | **ALL CHECKS PASS（141 项断言）** |
| 清单闸门 | `build_final_manifest.py --check` → **PASS** |
| **本轮发现并修复的真实缺陷** | **1 项（D48，跨进程锁健壮性）** + 1 项测试可诊断性增强 |
| 阻塞项 | **无**（离线结题范围内） |
| 需人工新授权项 | **有（§9）**，但**不阻塞**本次结题 |

**一句话**：V01/V02 的探索性阶段**可以离线结题**；全部统计可由原始数据独立复算；
全部已知缺陷与历史成本**如实披露、未被消除**。

---

## 1. 工程验收结论及证据

| # | 检查 | 命令 | 结果 | 退出码 |
|---|---|---|---|---|
| 1 | V01 单元测试 | `.venv\Scripts\python.exe -m unittest discover -s tests -v` | **Ran 227 tests, OK**（317.9 s） | **0** |
| 2 | V02 单元测试 | `cd v02 && ..\.venv\Scripts\python.exe -m unittest discover -s tests -v` | **Ran 143 tests, OK**（8.7 s） | **0** |
| 3 | V01 doctor | `.venv\Scripts\python.exe -m safefliplab doctor` | **17/17 PASS，VERDICT: GO**（零 episode） | **0** |
| 4 | V02 doctor | `cd v02 && ..\.venv\Scripts\python.exe -m v02lab doctor` | **7/7 PASS，VERDICT: GO**（零 episode） | **0** |
| 5 | 独立复算（V01+V02） | `.venv\Scripts\python.exe scripts\independent_verify_all.py` | **ALL CHECKS PASS（141 项断言）** | **0** |
| 6 | 清单一致性闸门 | `.venv\Scripts\python.exe scripts\build_final_manifest.py --check` | **PASS**（文件数/字节数/类别数/关键哈希行数**由 `--check` 输出，以 `docs/FINAL_ARTIFACT_COUNTS.md` 的生成块为准**） | **0** |
| 7 | F-06 取证 | `.venv\Scripts\python.exe scripts\runid_audit.py` | `method` 列权威；`run_id` 标签为外观缺陷 | **0** |
| 8 | 报告幂等性 | 两次 `report --phase` | **报告产物逐字节相同** | 0 |
| 9 | V01 formal 安全门 | `formal --confirm --max-episodes 12800` | **REFUSED** | **2** |
| 10 | V02 预算保护 | `v02lab smoke/pilot --max-episodes <cap>` | **REFUSED（预算已用满）** | **2** |
| 11 | V02 无 formal 入口 | `v02lab --help` | 子命令仅 `{doctor,smoke,pilot,report}` | 0 |

**证据文件**：`docs/V13_FINAL_TEST_EVIDENCE_20261016.txt`、
`docs/V13_FINAL_V01_TESTS_20261016.txt`、`docs/V13_FINAL_V02_TESTS_20261016.txt`、
`docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt`（由 `scripts/independent_verify_all.py` 重写）。

**代码隔离与冻结校验**：V01（`safefliplab/`）与 V02（`v02/v02lab/`）**互不 import**；
`configs/formal_v01.json` mtime 仍 **2026-10-12 12:13**（未被修改）；
`v02/configs/v02_frozen_v1.json` 协议指纹 `d175ec90eecf4e80…`（规范 JSON）与
`52fc80aaa4936661…`（原始字节）**均未变化**。

---

## 2. V01 / V02 账本完整对账

> 详细版：**`docs/LEDGER_RECONCILIATION_20261016.md`**

| 版本 | 阶段 | 上限 | 有效发起 | 完成 | 错误 | 中断 | 孤儿 | 磁盘 JSON |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| V01 | smoke | 24 | 24 | 24 | 0 | 0 | 0 | 24 |
| V01 | pilot（有效） | 240 | 240 | 240 | 0 | 0 | 0 | 240 |
| V01 | **pilot（首轮作废）** | — | **220** | 220 | 0 | 0 | 0 | **220** |
| V01 | formal | 12,800 | **0** | 0 | 0 | 0 | 0 | 0 |
| V02 | smoke | 24 | 24 | 23 | 1（D37） | 0 | 0 | 24 |
| V02 | pilot | 240 | 240 | 240 | 0 | 0 | 0 | 240 |

| 汇总 | 值 |
|---|---:|
| **有效活动账本**（可作证据） | V01 **264** + V02 **264** = **528** |
| **历史真实发起总数**（含作废） | V01 **484** + V02 **264** = **748** |
| 磁盘原始 episode JSON | **748**（与上完全一致） |
| 账本 ↔ 磁盘 一致性 | **双向 1:1**（缺失 0，未登记 0），V01/V02 各自成立 |
| 重复 episode_key | **0** |
| 删除失败记录 / 重新计费 / 伪造成功 | **无** |

**关于「220」与「244」的口径澄清（审阅者易误判为矛盾）**：

- **220** = V01 **首轮被作废的 pilot** episode 数（`runs/_buggy_pilot_run1/` 有 220 个原始 JSON，
  备份账本 `runs/episode_ledger.csv.buggy_pilot_run1` 中 `phase='pilot'` 的 launch 行数亦为 220）；
- **244** = 该备份账本的**总 launch 行**（= 24 smoke + 220 pilot）；
- 二者**不矛盾**，只是范围不同。**历史成本按 220 次作废 pilot 计**，且**未被抹除**。
  旁证：`runs/manifest_pilot_summary.json.stale_zero_backup`（`episodes_launched = 0`
  却记录 `pilot_wall_time_s = 177.27`）正是"跑了但没记上"的物证。

**V01 首轮 pilot 被作废的原因**：阶段隔离缺陷使不同方法/阶段的行被错误地视为同一隔离键。
该轮整体备份、代码修复后**重新运行** 240 次有效 pilot。作废轮次**从不混入**任何统计。

---

## 3. 科研假设与结果判定

> 判据为**描述性**（区间是否严格离开 0；是否超过端点分辨率）。**不产出 p 值**，
> 因此任何假设**不得**写作"成立/被证明"。完整表见 `reports/v02/REPORT.zh-CN.md` §4.7。

| 假设 | 观测（点估计 / 95% 锚级 CI，s） | **判定** |
|---|---|---|
| **H-R1a** `Δgap` 安全反转 | +0.0127 / [−0.0525, +0.0769] | **INCONCLUSIVE** |
| **H-R1b** `Δspeed` 安全反转 | +0.0327 / [−0.0589, +0.1243] | **INCONCLUSIVE** |
| **H-R1c** `Δboth` 安全反转 | +0.0030 / [−0.0436, +0.0526] | **INCONCLUSIVE** |
| **H-I-lin** 非可加交互 | −0.0424 / [−0.1465, +0.0613] | **INCONCLUSIVE** |
| **H2** 两方法提名质量差异 | WideExplore 1/3 vs VerifyFirst 3/3 | **NOT ESTABLISHED** |

**方法学事实的判定（区分 ESTABLISHED / NOT ESTABLISHED）**：

| 主张 | 判定 | 证据 |
|---|---|---|
| 端点方差已从 0 恢复 | **ESTABLISHED（描述性）** | G3a：控制条件锚内方差 **0.0917 s²**（V01 为 0） |
| 扰动使 min-TTC 不再逐位相同 | **ESTABLISHED（描述性）** | G4：**18/18** 锚 |
| 重复已成为**相互独立**样本 | **NOT ESTABLISHED** | 仅证明"不再逐位相同"；独立单元仍是**锚** |
| 度量实现与上游一致 | **ESTABLISHED（验证性）** | 240/240 一致，最大差 **8.3×10⁻⁶ s**（容差 1e-4） |
| 两方法孰优 | **NOT ESTABLISHED** | 3 提名 × 1 audit quartet（3 自由度）；提名集共享锚且该锚两次审计**是同一次模拟** |

**独立性 / 区间 / 假设 / TTC 状态 / 审计隔离 复核结论**：

| 项 | 结论 |
|---|---|
| 独立单元 | **锚**（非 episode、非 repetition）——代码与报告一致 |
| 区间语义 | 锚级 cluster bootstrap **描述性**；无覆盖保证（抽样假设 A/B/C 未证） |
| 显著性 | **不产出 p 值**；`stats_anchor` 强制门控，系统**无权自行批准** |
| TTC 状态 | Layer-1（NORMAL_CLOSING / NO_CLOSING / NO_CANDIDATE）与 Layer-2（FINITE / CENSORED / NO_CANDIDATE / MISSING）**定义完整**；`None ≠ 安全`、`None ≠ 0`；V02 pilot 主研究 **216/216 = FINITE** |
| M2 与 M1 | 在 `Δgap` 上**方向相反**（M1 `+0.0127` 更安全；M2 `+0.00186` 不安全）——**该不一致被保留并公开**（D43） |
| 审计隔离 | 审计流与发现流 `sim_seed` 不相交；**但**历史审计种子标签硬编码 ⇒ 两方法共享同一次模拟（D42）⇒ 该比较**永久不独立** |
| 零碰撞 / 零反转 / 不显著 | **均为允许结果**，已如实记录；**未**把 ΔTTC 代理变化冒称真实事故概率 |

**禁止表述复核**：`docs/CLAIMS_REGISTER.zh-CN.md` 的 **X1–X17** 在交付文本中
**仅出现于禁止/否定语境**（已机械扫描确认）。

---

## 4. 测试命令、实际通过数与退出码（原始记录）

```text
[V01] python -m unittest discover -s tests -v
      Ran 227 tests in 317.922s
      OK                                                  V01_EXIT=0

[V02] cd v02 && python -m unittest discover -s tests -v
      Ran 143 tests in 8.745s
      OK                                                  V02_EXIT=0

[V01] python -m safefliplab doctor
      17/17 checks passed
      VERDICT: GO (interface verified; no episodes launched by doctor)      EXIT=0

[V02] cd v02 && python -m v02lab doctor
      7/7 checks passed
      VERDICT: GO (interface verified; no episodes launched by doctor)      EXIT=0

[复算] python scripts\independent_verify_all.py
      INDEPENDENT RECOMPUTATION: ALL CHECKS PASS                          EXIT=0

[闸门] python scripts\build_final_manifest.py --check
      MANIFEST COUNT CHECK: PASS (files=198, bytes=3304653,
                                  categories=15, key_hash_rows=12)        EXIT=0

[安全门] python -m safefliplab formal --confirm --max-episodes 12800
      REFUSED: formal driver is implemented but NOT executed by this build  EXIT=2
[安全门] cd v02 && python -m v02lab smoke --max-episodes 24                 EXIT=2
[安全门] cd v02 && python -m v02lab pilot --max-episodes 240                EXIT=2
```

**测试计数变化**：V01 **225 → 227**（D48 新增 2 项回归测试）；V02 **142 → 143**（D43 于上一轮新增）。

---

## 5. 文件哈希及清单检查

| 项 | 值 |
|---|---|
| 清单 | `docs/FINAL_ARTIFACT_HASHES.csv`（**198** 行，逐文件 SHA-256） |
| 计数摘要 | `docs/FINAL_ARTIFACT_COUNTS.md`（**脚本生成**） |
| 分类 | **15** 类（含新增 `script` 类） |
| 字节合计 | **以 `docs/FINAL_ARTIFACT_COUNTS.md` 生成块为准**（写入本报告时为 3,304,653；此后文档编辑会增加） |
| 关键哈希行 | **12**（含两种口径） |
| 闸门 | `--check` → **PASS** |

**两种哈希口径（不可混用）**：

| 对象 | 口径 | 值 |
|---|---|---|
| `v02/configs/v02_frozen_v1.json` | 规范 JSON（协议指纹） | `d175ec90eecf4e80…` |
| `v02/configs/v02_frozen_v1.json` | 原始字节 | `52fc80aaa4936661…` |
| `configs/formal_v01.json` | 原始字节 | `e9232dec4b45bf7e…` |
| `runs/episode_ledger.csv` | 原始字节 | `011047a8dfb0fdf7…` |
| `v02/runs/smoke/episode_ledger.csv` | 原始字节 | `00ca9de4a5bc21f2…` |
| `v02/runs/pilot/episode_ledger.csv` | 原始字节 | `fea87c8d6e9c123e…` |

**闸门强度（注入式反向控制，全部被检出 EXIT 1）**：篡改关键哈希 ✓｜插入幽灵条目 ✓｜
篡改分类小计 ✓｜篡改文件总数 ✓｜**篡改关键哈希表**（本轮新增校验）✓。
⇒ 这是**会真正失败的闸门**，不是形式化绿灯。

**本轮修正的清单缺陷（承接外部审阅意见）**：清单曾出现 **186 / 187 / 188** 三个矛盾总数
（手工维护计数导致）。已改为**生成式计数 + `--check` 闸门**；
本轮进一步把**关键哈希表也改为生成式**（此前仍为手工，且在本轮编辑后**被闸门当场捕获为过期**）。
详见 `docs/MANIFEST_COUNT_RECONCILIATION.md`。

---

## 6. 历史协议偏离与仍存在的限制

### 6.1 历史偏离（全部保留、未消除）

| # | 偏离 | 处置 | 是否影响证据 |
|---|---|---|---|
| P-1 | **V01 首轮 pilot 隔离缺陷 → 220 次真实 episode 作废** | 整体备份 + 重新运行 240 次有效 pilot | **不影响**（作废轮从不混入统计） |
| P-2 | **F-06**：V01 账本 2 个 `run_id` 方法标签错误 | `method` 列为权威（`sim_seed` 判定）；仅字符串标签错 | **不影响**任何 Y/种子/锚/统计量 |
| P-3 | **V02 D37**：1 个 smoke episode 归档失败 | 计费 1 次、记 error、**未重跑** | **不影响** pilot 结论 |
| P-4 | **V02 D42**：审计种子标签硬编码 → 两方法共享同一次审计模拟（4 个 episode 重复计费） | 修复 + 回归测试；**数据不重跑** | **影响辅助方法比较** ⇒ **永久不独立**，已披露 |
| P-5 | **V02 D43**：M2 曾按文件名通配读取 episode（解析 240 而非 216） | 修复为以账本 `raw_path` 为准 + 回归测试 | **仅影响 M2**；旧结论"两终点方向一致"**不成立**，已更正 |
| **P-6** | **V01 `_exclusive_file_lock` 锁文件打开失败逃逸为未捕获异常（本轮 D48）** | 修复（单一 deadline + 重试 + `LedgerLockTimeout`）+ 2 项回归测试 | **不影响**任何科学数据；仅影响跨进程计费健壮性 |

### 6.2 仍存在的限制（不得被削弱）

**设计**：事后性设计、**无外部预注册**（只有配置冻结）｜单一 dev 主种子｜**仅 18 个非随机锚**｜
锚域被有意收窄｜**端点分辨率与效应同量级**（0.003–0.033 s vs 代理量 ~0.2 s）｜
未实现提案中的 lead 减速事件｜**无 p 值 / 无 FWER**。
**数据**：辅助方法比较**永久不独立**｜M2 与 M1 在 `Δgap` 上**方向相反**｜
D37 消耗 1 个 smoke 预算｜D43 曾污染 M2（已修）｜容差在 smoke 后校准。
**主张**：TTC **不是碰撞概率**｜仅**描述性估计**｜文献检索**非穷尽**｜
**未与上游 60,000 episode 正式数据比较**｜未逐行比对上游源码。

---

## 7. 独立 AI 审核所需的证据（自包含清单）

**审核者可仅凭以下文件独立复核，无需访问本会话：**

| # | 文件 | 用途 |
|---|---|---|
| 1 | `docs/LEDGER_RECONCILIATION_20261016.md` | 账本对账（含 220 vs 244 口径澄清与复现命令） |
| 2 | `scripts/independent_verify_all.py` | **全量独立复算器**（不导入任何报告模块，141 项断言） |
| 3 | `docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt` | 复算输出（逐项 `recomputed` vs `published`） |
| 4 | `docs/V13_FINAL_V01_TESTS_20261016.txt` / `docs/V13_FINAL_V02_TESTS_20261016.txt` | 测试原始输出 |
| 5 | `docs/V13_FINAL_TEST_EVIDENCE_20261016.txt` | 两套 doctor |
| 6 | `docs/FINAL_ARTIFACT_HASHES.csv` + `docs/FINAL_ARTIFACT_COUNTS.md` | 逐文件哈希 + 生成计数 |
| 7 | `scripts/build_final_manifest.py`（含 `--check`） | 计数/哈希闸门（可自行注入错误验证其会失败） |
| 8 | `reports/v02/REPORT.zh-CN.md` / `reports/v02/PAPER_DRAFT_EN.md` | 结题报告与论文初稿（含 §4.7 假设判定） |
| 9 | `docs/CLAIMS_REGISTER.zh-CN.md` | 主张 C1–C18 与禁止表述 X1–X17 |
| 10 | `docs/AUTONOMOUS_DECISIONS.md`（D28–D48） | 全部决策、缺陷与修复的完整记录 |
| 11 | `docs/FINAL_CLOSURE_DECISIONS.md` | 结题决策 P1–P7 及理由 |
| 12 | `docs/REPRODUCTION_MANUAL.zh-CN.md` | 从零复现（含 schema 指纹、F-06 取证、闸门） |

**建议的独立审核动作**（全部零 episode）：
```powershell
cd D:\SafeFlipLab
.\.venv\Scripts\python.exe -m unittest discover -s tests        # 227 OK
cd v02; ..\.venv\Scripts\python.exe -m unittest discover -s tests; cd ..   # 143 OK
.\.venv\Scripts\python.exe scripts\independent_verify_all.py    # ALL CHECKS PASS
.\.venv\Scripts\python.exe scripts\build_final_manifest.py --check          # PASS
```
**对抗性建议**：审核者应尝试**注入错误**（改哈希、改计数、加幽灵文件）以确认闸门会失败；
并尝试**篡改一条账本行的副本**以确认复算器会报 MISMATCH。
（⚠️ **不得**修改 `D:\SafeFlipLab` 内的原始账本；请在副本上操作。）

---

## 8. 是否具备离线工程结题条件

**具备（YES）。** 判据：

1. 授权范围内工作**全部完成**，无未决缺陷、无未解释的失败；
2. **全部测试通过**且退出码为 0；两套 doctor 为 GO；
3. **全部统计可由原始数据独立复算**（141 项断言逐位一致）；
4. 账本与磁盘**双向 1:1**，历史成本**完整留痕**；
5. 清单**计数与哈希由脚本生成**，并有**会失败的闸门**；
6. 全部已知缺陷、事故、协议偏离**如实披露且未被消除**；
7. 报告与论文的**假设判定明确为 INCONCLUSIVE / NOT ESTABLISHED**。

**本轮新增的真实成果**：
- 发现并修复 **D48**（跨进程锁健壮性缺陷），含 **2 项可失败的回归测试**（已用反向控制证明）；
- 把**关键哈希表**改为生成式，并由闸门**当场捕获**了自身的过期条目；
- 补齐 `scripts/`（此前**未被清单覆盖**）与 `v02/runs/*/episode_ledger.schema.json`（协议声称存在但**从未落盘**）；
- 新增账本对账报告与逐条假设判定表。

## 9. 必须得到人工新授权的工作（**不阻塞结题**）

| # | 事项 | 为何需要授权 |
|---|---|---|
| G-1 | 新增任何真实仿真 episode | 绝对安全边界（五）；且预算已用满 |
| G-2 | 启动 V01/V02 formal（V01 为 12,800 次） | 明确未授权；MDE 仅为规划示例 |
| G-3 | 重新运行 smoke / pilot | 预算封闭原则 |
| G-4 | 修改冻结配置、历史账本或原始实验数据 | 证据完整性不可逆 |
| G-5 | 修改 `CornerCaseLab` 旧项目 | 只读引用边界 |
| G-6 | GitHub 发布 / push / 投稿 / 对外公开 | 明确未授权 |
| G-7 | 付费服务、Full Access、系统全局权限变更 | 明确未授权 |
| G-8 | 获取并逐行比对上游 `PROTOCOL_TODO.md` 与源码 | 需外部资源 |
| G-9 | 安排**外部**同行评审 | 需外部资源（当前仅内部独立复核） |
| G-10 | 提高端点保真度（多维 SSM）以区分"无效应"与"分辨率不足" | 需新资源与预算 |

**在上述任一项发生前，本项目保持"探索性阶段已结题、不得再启动真实仿真"的状态。**

---

## 10. 交付物速查

| 类别 | 关键文件 |
|---|---|
| **本报告** | `docs/FINAL_CLOSEOUT_20261016.md` |
| 账本对账 | `docs/LEDGER_RECONCILIATION_20261016.md` |
| 结题决策 | `docs/FINAL_CLOSURE_DECISIONS.md`（P1–P7） |
| 科研报告 / 论文 | `reports/v02/REPORT.zh-CN.md`、`reports/v02/PAPER_DRAFT_EN.md` |
| 主张登记 | `docs/CLAIMS_REGISTER.zh-CN.md`（C1–C18 / X1–X17） |
| 决策与缺陷 | `docs/AUTONOMOUS_DECISIONS.md`（D28–D48）、`docs/DECISION_LOG.md`（D1–D27） |
| 清单与哈希 | `docs/FINAL_DELIVERY_MANIFEST.md`、`docs/FINAL_ARTIFACT_HASHES.csv`、`docs/FINAL_ARTIFACT_COUNTS.md` |
| 复现 | `docs/REPRODUCTION_MANUAL.zh-CN.md` |
| 脚本 | `scripts/build_final_manifest.py`、`scripts/independent_verify_all.py`、`scripts/runid_audit.py` |
| 测试与审计证据 | `docs/V12_*`、`docs/V13_*` |
| 交接 | `docs/LATEST_HANDOFF.md`、`docs/AUTONOMOUS_PROGRESS.md`、`docs/FINAL_DELIVERY.md` |
