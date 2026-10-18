# SafeFlipLab — 最新交接文件（LATEST HANDOFF）

> 状态时间：**2026-10-17（GMT+8）**，WorkBuddy **第六轮：结题验收独立复核 + 返工轮：B-01/OBS-1 + 返工轮 2：OBS-4/OBS-5（成员 A 工程执行）**。
> **各轮均零新增真实仿真**、未启动 formal、未重跑 smoke/pilot、未改历史账本或冻结配置。
> 第六轮 6 项验收一次通过，**并被成员 B 独立复现全部通过**；返工轮修复成员 B 开具的
> **B-01（MINOR：两处终态字节数失真）** 并处理 **OBS-1（V01 测试计数陈旧值）**；
> 返工轮 2 按总控扩展授权修复 **OBS-4（授权清单外 4 处陈旧 225）** 与 **OBS-5（categories=14）**；
> B-02 已被 B 以 mtime 实证自行撤销。
> 完整复核报告：**`docs/FINAL_CLOSEOUT_2026-10-17.md`**（证据：`D:\SafeFlipLab_AUDIT_2026-10-17\round1\`）；
> 返工证据：`D:\SafeFlipLab_AUDIT_2026-10-17\rework_r1\`（B-01/OBS-1）、`D:\SafeFlipLab_AUDIT_2026-10-17\rework_r2\`（OBS-4/OBS-5）。
> 上一轮（第五轮，2026-10-16）结题执行见下文 §0 原条目与 `docs/FINAL_CLOSEOUT_20261016.md`。

---

## 0. 本轮（第六轮）结论速览 —— 结题验收独立复核

| 项 | 结果 |
|---|---|
| 执行方式 | 成员 A 在项目外审计目录独立执行；**所有可能写文件的命令均在隔离副本** `isolated_round1/` 运行；项目内仅运行只读命令（doctor ×2、`--check`、账本只读统计） |
| 独立复算器 | **ALL CHECKS PASS**：**141 项断言**，**0 MISMATCH**，EXIT 0（在隔离副本运行：该脚本会写证据文件，且 ROOT 硬编码，副本内已改 ROOT；项目内脚本未动） |
| Manifest 闸门 | `--check` → **PASS**（**判据为 PASS / EXIT 0，而非任何固定字面量**；files/bytes/categories/key_hash_rows 一律以 `docs/FINAL_ARTIFACT_COUNTS.md` 的生成块为准），EXIT 0 |
| doctor | **V01 17/17 GO；V02 7/7 GO**（均零 episode），EXIT 0 |
| 测试套件 | **V01 Ran 227 tests, OK**（45.4 s）；**V02 Ran 143 tests, OK**（1.9 s）；均 EXIT 0。venv 无 pytest，按任务书改用 `unittest discover`；**未修改任何测试** |
| 报告幂等性 | **58/58** 产物：隔离副本同位置重跑**逐字节一致**；路径归一化后与项目归档 **58/58 一致**（8 个 md/json 产物嵌入绝对输出路径，跨目录原始比对必有前缀差——预期行为，非缺陷） |
| 账本只读复核 | **完全一致**：V01 活动 528 行（264 launch+264 outcome，全 completed）；作废备份 488 行（smoke 24 + pilot 220）；V02 smoke 48 行（23 completed + 1 error=D37）、pilot 480 行（240 completed）；**有效合计 528；历史真实发起 748 = 磁盘 JSON 748**（磁盘数仅取自账本 `raw_path` 列）；孤儿 0、重复 key 0 |
| 科学数据完整性 | 隔离副本跑完测试+报告后，`runs/` 490↔490、`v02/runs/` 272↔272、4 账本+3 配置**逐字节一致** |
| 历史计数核验 | V01 227 / V02 143 / 141 断言 / 528 行 / 748 JSON / 220（244 口径）/ doctor 17+7——**全部与实测一致** |
| 缺陷与修复 | **无**（6 项验收一次通过，诊断修复流程未被触发；无新回归测试、无 diff） |
| 决策追加 | `docs/AUTONOMOUS_DECISIONS.md` **D49**（记录本轮复核结论与「无修复」判定） |
| 新增真实 episode | **0** |

**下一步**：**无。** 探索性阶段已结题；§9 的 G-1…G-10 需人工新授权，且**不阻塞**结题。

---

## 0. 本轮（返工轮）结论速览 —— B-01 修复与 OBS-1 处理

| 项 | 结果 |
|---|---|
| 触发 | 成员 B 审核（证据 `round2/AUDIT_REPORT.md`）：round1 六项验收**全部被独立复现通过**；开具 **B-01（MINOR FAIL）**（两份交付文书终态字节数与命令实际输出不符）；OBS-1（V01 测试计数陈旧 225）经总控裁定本轮一并处理；B-02 已被 B 以 mtime 实证自行撤销 |
| B-01 修复 | ① `round1/REPORT.md` L15/L44 的 `3351248` → 以**可见更正记录**修正为 `3351475`（= round1 日志 `step5_manifest_check_final.txt` / `step5_manifest_regenerate.txt` 实际输出；偏差 227 字节）；② 第六轮速览表 Manifest 闸门行的终态 `3351355` → 改为**不可过期表述**（判据 `--check` **PASS / EXIT 0**；files/bytes/categories/key_hash_rows 一律以 `docs/FINAL_ARTIFACT_COUNTS.md` 生成块为准；偏差 120 字节）。根因同 D47：手工固化派生数值 |
| OBS-1 处理 | 全库 grep `225` **36 处**逐处判定（证据 `rework_r1/logs/grep_225_full.txt`；权威 227 见 `docs/V13_FINAL_V01_TESTS_20261016.txt`）：**授权内修正 4 处**（`REPRODUCTION_MANUAL` L56/L57 → 227；`FINAL_DELIVERY_MANIFEST` L162 → 227、L76 加"2026-10-15 快照；现行权威 227 / 143 见 V13"限定）；**授权外陈旧现行值 4 处只记录不修改**（`OWNER_GUIDE.zh-CN.md` L96、`LITERATURE_DIFFERENCE_TABLE.zh-CN.md` L43、`FINAL_RESEARCH_AUDIT.zh-CN.md` L207、`FINAL_DELIVERY.md` L50 —— 记为 **OBS-4** 待总控裁定）；**历史留痕 28 处一律未改**（带日期/证据引用的历轮记录与 V09/V11/V12 原始测试输出） |
| 新发现 | `REPRODUCTION_MANUAL.zh-CN.md` L78 的 `categories=14` 为陈旧值（现行 **15**；`script` 类于第五轮补入清单）——本轮对该文件仅授权 OBS-1 类修正，未改，记为 **OBS-5** 待总控裁定 |
| 决策追加 | `docs/AUTONOMOUS_DECISIONS.md` **D50**（B-01 修复 + OBS-1 逐处判定 + 编辑顺序纪律） |
| Manifest 闸门 | 全部文档内容编辑完成后**最后**重生成 manifest + `--check` → **PASS**，EXIT 0（files/bytes 以 `docs/FINAL_ARTIFACT_COUNTS.md` 生成块为准；**判据为 PASS / EXIT 0，而非任何固定字面量**） |
| 新增真实 episode | **0** |

**下一步**：**无。** OBS-4 / OBS-5 待总控裁定（**不阻塞**结题）；§9 的 G-1…G-10 需人工新授权。

---

## 0. 本轮（返工轮 2）结论速览 —— OBS-4 / OBS-5 修复（总控扩展授权）

| 项 | 结果 |
|---|---|
| 触发 | 总控裁定：**B-01 修复方案合格**；rework_r1 记录的 **OBS-4**（授权清单外 4 处陈旧 V01 测试计数 225）与 **OBS-5**（`REPRODUCTION_MANUAL.zh-CN.md` L78 `categories=14`）**扩展授权本轮修复**；成员 B 将在暂停写入后做最终独立复验 |
| OBS-4 修正（权威 227，见 `docs/V13_FINAL_V01_TESTS_20261016.txt`） | ① `docs/OWNER_GUIDE.zh-CN.md` L96（§4 目录描述，无日期现行主张）→ 改数 **225→227**；② `docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md` L43（现行描述）→ 改数 **225→227**；③ `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` L207（该轮历史快照；与同文件 §1.7 上表的 227 自相矛盾）→ **加限定语**「该轮当时口径；结题执行后为 227，见 §1.7 上表与 D48」；④ `docs/FINAL_DELIVERY.md` L50（2026-10-15 交付轮快照，文件头有日期）→ **加限定语**「当时口径；结题执行后为 227，见 D48」 |
| OBS-5 修正 | `docs/REPRODUCTION_MANUAL.zh-CN.md` L78 `categories=14` → **15**（以最后 `--check` 实际输出为准） |
| 纪律遵守 | 只修现行主张处；历史留痕文件（`DECISION_LOG.md`、`V12_*`、`V13_*`、`PROGRESS.md`、`AUTONOMOUS_MASTER_PLAN.md` 等）与记载「225→227」变更史的条目**一律未改**；历史快照语境加限定语而非改数 |
| 决策追加 | `docs/AUTONOMOUS_DECISIONS.md` **D51** |
| Manifest 闸门 | 全部文档编辑完成后**最后**重生成 + `--check` → **PASS**，EXIT 0（files/bytes/categories 以 `docs/FINAL_ARTIFACT_COUNTS.md` 生成块为准；**判据为 PASS / EXIT 0，而非任何固定字面量**） |
| 新增真实 episode | **0** |

**下一步**：暂停项目写入，等待成员 B **最终独立复验**；OBS-4/OBS-5 已无未解决项；§9 的 G-1…G-10 需人工新授权。

---

## 0. 本轮（第五轮）结论速览 —— 结题执行

| 项 | 结果 |
|---|---|
| 附件 | 《SafeFlipLab｜自主完成结题任务》以**消息正文**给出（无独立附件）；按其正文执行 |
| **实跑测试时发现真实失败** | V01 全量测试出现 **1 项失败**：`test_cap_one_legacy_ledger` 期望 5 个 `REFUSED`，实测仅 **4**，第 6 个 worker **输出为空** |
| **缺陷 D48（已修复）** | 根因：`safefliplab/ledger.py::_exclusive_file_lock` 把**锁边车文件的 `os.open`/`mkdir` 放在重试与超时机制之外**；Windows 上并发创建/删除边车会瞬时抛共享冲突（`PermissionError`），**逃逸为未捕获异常** → worker 静默死亡。**已用 monkeypatch 确定性复现**。修复：单一 deadline 覆盖 mkdir+open+加锁，瞬时错误重试，持续失败抛 `LedgerLockTimeout`（调用方已处理） |
| **回归测试（可失败）** | `tests/test_ledger_safety.py::TestLockFileOpenIsRetried`（2 项）。**反向控制**：临时回退 `ledger.py` → 两项均以 `PermissionError` **失败**；恢复后**通过** |
| 测试可诊断性 | `test_ledger_legacy_acceptance.py::_run()` 现保留每个 worker 的 **rc + stderr 尾部**，失败信息可诊断（**未削弱断言**） |
| **V01 测试** | **Ran 227 tests, OK, EXIT 0**（317.9 s；由 225→227） |
| **V02 测试** | **Ran 143 tests, OK, EXIT 0** |
| doctor | **V01 17/17 GO；V02 7/7 GO**（均零 episode） |
| 独立复算 | **ALL CHECKS PASS（141 项断言）** |
| **账本对账** | **通过**：V01 有效 **264**（24 smoke + 240 pilot）+ 作废 **220**；V02 **264**（smoke 24 / pilot 240）。**有效合计 528；历史真实发起合计 748 = 磁盘 JSON 数**。孤儿 0；双向 1:1 |
| **「220 vs 244」口径澄清** | **220** = 被作废的 **pilot** 数；**244** = 备份账本**总 launch 行**（24 smoke + 220 pilot）。**不矛盾**，只是范围不同。见 `docs/LEDGER_RECONCILIATION_20261016.md` |
| 缺陷类别扫描 | 文档引用 942 处 → 逐类解析后**真正无法解析的 16 处**已分诊并修复（见下） |
| 文档修正 | ① `AUTONOMOUS_MASTER_PLAN` 指向不存在的 `V10_V02_TEST_RESULTS.txt` → 已改实际文件名；② `V02_PROTOCOL_FROZEN` 声称表头哈希"记录于 `episode_ledger.schema.json`"，但**该文件从未落盘** → **已用项目自带 API 生成**（smoke/pilot 各一份，哈希 `24eeb391…` 与 manifest 一致，**账本未被触碰**）并改写文档；③ `LATEST_HANDOFF` 引用的一次性临时文件 `pilot_out2.json` → 改指向稳定产物 |
| **`scripts/` 此前未被清单覆盖** | **已补入清单**（新增 `script` 类），并把**独立复算器**从临时目录**提升到 `scripts/`** 作为规范位置，同步更新 6 处文档引用 |
| **关键哈希表改为生成式** | 此前仍为手工；本轮编辑后**被闸门当场捕获为过期**（3 行哈希不符）→ 已改为脚本生成，并把 `--check` 扩展为**逐行核对哈希与实际文件**（含幽灵条目检测） |
| 闸门反向控制 | 篡改关键哈希 ✓｜幽灵条目 ✓｜分类小计 ✓｜文件总数 ✓（**全部 EXIT 1**） |
| 清单最终 | `--check` → **PASS**；**文件数/字节数/类别数以 `docs/FINAL_ARTIFACT_COUNTS.md` 的生成块为准**（写入时为 199 文件 / 15 类 / 13 关键哈希） |
| 假设判定 | 报告与论文新增 **§4.7 假设判定**：H-R1a/b/c 与 H-I-lin **INCONCLUSIVE**；H2 **NOT ESTABLISHED** |
| 新增真实 episode | **0** |

**下一步**：**无。** 探索性阶段已结题；§9 的 G-1…G-10 需人工新授权，且**不阻塞**结题。

---

## 0b. 第四轮结论速览 —— 最终闭环结题

| 项 | 结果 |
|---|---|
| 附件 | 《SafeFlipLab 最终闭环自主执行授权》**未随消息附带**（Downloads 无新文件）；按负责人明确指示，依据消息正文 + 本地 `FINAL_RESEARCH_AUDIT.zh-CN.md` / `LATEST_HANDOFF.md` / `DECISION_LOG.md` 继续 |
| **缺陷类别扫描** | 对 V01+V02 全代码扫描 **D43 同类缺陷**（按文件名通配枚举 episode、按名而非账本 `raw_path` 取数）⇒ **仅 `m2_from_raw` 一处**曾有问题（D43 已修 + 回归测试）；V01 全部读取点均基于账本；`metric_equivalence` 自洽比较不受影响 |
| **全量独立复算** | 新写 `independent_verify_all.py`（**不导入**任何报告模块）⇒ **ALL CHECKS PASS（141 项断言）**，覆盖 V01 计数/60 quartet/4×(method,stream)/12 组 ΔTTC 与 V02 M1/M2 全对比 + bootstrap 区间 + 辅助审计 + 样本量网格 |
| **口径澄清** | `n_primary_quartets`（四条件均已计费）与 `n_usable_quartets`（四条件均有可恢复值）是**两个不同定义**；smoke = **6 / 5**，pilot = **54 / 54**，**两者均已独立复算通过** |
| **P1–P7 一次性关闭** | 见 `docs/FINAL_CLOSURE_DECISIONS.md`：P1 MDE=0.10 s **仅为规划示例**；P2 V02 **以探索性/描述性研究结题**；P3 外部评审=**可选未来工作、不阻塞**；P4 **拒绝任何新增真实仿真**；P5 不批准正式主种子（不适用）；P6 **D4/D5/D6 归档不追认**；P7 **M1 主要描述性终点 + M2 辅助指标，保留方向不一致证据** |
| **主张登记** | `docs/CLAIMS_REGISTER.zh-CN.md`：**C1–C18** 主张→证据 + **X1–X17** 禁止表述 + 符号约定表 |
| **报告/论文统一** | 中文报告与英文初稿已加**结题状态**与**终点角色**；数值一致性机械核对通过；禁用表述仅出现在禁止/否定语境 |
| **幂等性** | `report --phase` 重跑后 **32 个报告产物逐字节相同**（IDEMPOTENT） |
| **交付与哈希** | `docs/FINAL_DELIVERY_MANIFEST.md` + `docs/FINAL_ARTIFACT_HASHES.csv`（**逐文件 SHA-256；文件数以 CSV 行数为准**）+ `docs/FINAL_ARTIFACT_COUNTS.md`（生成的计数摘要）+ `docs/REPRODUCTION_MANUAL.zh-CN.md` |
| **测试** | **V01 227/227 OK；V02 143/143 OK**（均 EXIT 0）；doctor **17/17 / 7/7 GO** |
| **最终验收** | `docs/V13_FINAL_ACCEPTANCE_20261015.txt`：账本无新增、冻结历史 mtime 未变、三个安全门**全部拒绝（EXIT 2）**、交付物齐备、独立复算 PASS |
| 新增真实 episode | **0** |

**下一轮**：**无。探索性研究阶段到此结束。** 任何后续正式研究都需**新的独立协议 + 新的明确授权预算**。

---

## 0c. 第三轮结论速览 —— 最终科研质量收尾

| 核验项 | 结果 |
|---|---|
| **样本量推导自洽性** | **通过**：`n=ceil((z_{1-α/2}+z_power)²·sd²/MDE²)`，α=0.05（Holm 最坏 ⇒ 每对比 0.0125，族=4）、power=0.80；**n=18 最灵敏对比（Δboth）可检出 MDE=0.0837 s**；MDE=0.10⇒**59 锚/708 eps**，MDE=0.05⇒**235 锚/2820 eps**。澄清：0.084 s 是**四对比中最灵敏者**，非「全部对比都能检出 0.084 s」（最迟钝者 `i_lin` 为 0.180 s） |
| **240 ↔ 54 核对** | **通过**：240 = 216（18×3×4，主）+ 24（2×3×1×4，审计）；216/4 = **54 主 quartet 全可用**；孤儿 launch **0**；每锚恰 3 个；每条件各 54 |
| **审计种子复用重估** | **历史数据不独立**：6 个名义审计 quartet 仅 **5 次不同模拟**（`anchor-0012` 同种子同场景、trace 逐位相同），4 个 episode（16.7%）重复计费。**留一后 WideExplore `1/3→0/2`、VerifyFirst `3/3→2/2`** ⇒ WideExplore 唯一命中**完全依赖**该共享模拟。**代码已修 ⇒ 历史数据仍不独立** |
| **符号方向核对** | M1 全部一致；**M2 发现新缺陷 D43（已修）** —— 见下行 |
| **★ 新发现缺陷 D43** | `m2_from_raw()` 曾按**文件名通配**读取 episode，而主研究流与审计流**写出同名文件** `<anchor_id>_rep<r>_<cond>.json` ⇒ 5 个被提名锚在 `rep0` 被审计 episode **覆盖**（解析 **240** 而非 **216**）。**→ 旧结论「M2 与 M1 方向一致」不成立**：更正后 `Δgap` 在两终点上**方向相反**（M1 `+0.0127` vs M2 `+0.00186`），区间均跨 0。**仅影响 M2**；已改为以账本 `raw_path` 为准 + 回归测试 |
| 上游重叠 | **已扩展到其公开协议文档全文**（`cornercaselab_v03_eval_v1`、`v03_scoring_v1`，commit `ce3a9b07…`）：60,000 eps、预算闭合 700+300、审计不回填、Wilson ≥21/30、SNY 精确最大独立集、20 配对种子、**成文不报 p 值**、六维 `PERTURBATION` 半径、**其自述审计选择规则仍非方法中性**。见 `CORNERCASELAB_OVERLAP_VERIFIED.md` §6 |
| 文献差异表 | **已完成**：`docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md`（17 行要素对比 + 4 条硬约束；**禁止**「首次/独有/原创」） |
| 回归测试 | **V01 225/225 OK（EXIT 0）**；**V02 142 → 143/143 OK（EXIT 0）**；V01 doctor **17/17 GO**；V02 doctor **7/7 GO** |
| 独立统计复核 | **PASS**（四个 M1 对比点估计与区间差 **0.0**） |
| 报告/论文 | 中文报告与英文初稿**已消除过度声称**并重写 M2 章节；`docs/FINAL_RESEARCH_AUDIT.zh-CN.md` 已产出 |
| 新增真实 episode | **0** |

**结论**：全部授权范围内工作已完成；**不提出新一轮自动开发、不以新版本重置预算**；
正式实验在 `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` §4 的 P1–P7 全部裁决前**不得启动**。

---

## 0d. 第二轮结论速览

| 项 | 结果 |
|---|---|
| 附件 | `《最终一次性自主完成总任务书》**未随消息附带**`（Downloads 无新文件、近 3 小时无新增文档）；已按消息正文边界执行 |
| P2 正式样本量 | **已完成（仅推导）**：锚级 SD `Δgap .144 / Δspeed .203 / Δboth .106 / I_lin .229` s；**n=18 仅能检出 ≥0.084 s**；MDE=0.10 → **59 锚 / 708 eps**，MDE=0.05 → 235 锚 / 2820 eps。见 `docs/V02_SAMPLE_SIZE_DERIVATION.md` |
| P3 上游重叠 | **已完成**：其公开 README 层面核验（60,000 eps、独立审计 10×30、Wilson ≥21/30、SNY、**同样不报 p 值**、Apache-2.0）→ **V02 的"无 p 值"属趋同、非新颖**。见 `docs/CORNERCASELAB_OVERLAP_VERIFIED.md` |
| P4 新颖性 | **已完成（非穷尽）**：组件均有先例；候选新增点收窄为 3 条并须附限定。见 `docs/RELATED_WORK_V02.md` §4 |
| P5 独立复核 | **已完成**：1 MAJOR 代码缺陷（D42）+ 3 MAJOR 过度声称 + 12 MINOR/INFO，**全部已处置**。见 `docs/REVIEW_RESPONSE.md`、D41/D42 |
| P6 正式准备包 | **已完成（只准备）**：`docs/V02_FORMAL_READINESS_PACKAGE.md`；**V02 仍无 formal 入口** |
| P7 论文/文档 | 中文报告、英文初稿、OWNER_GUIDE、FINAL_DELIVERY 等已按复核意见修正 |
| 测试 | V02 **142 项 OK**（+11 power、+2 seed-label 回归）；V01 225 项 OK |
| 独立统计复核 | **PASS**（点估计与区间差 0.0） |
| 新真实 episode | **0** |

### 本轮最重要的一项发现（MAJOR，已修）

`v02lab/quartet.py` 曾把 `sim_seed` 的 method 标签**硬编码为 `"shared"`**，使两分配策略对
**同一锚**的审计使用**相同种子与场景**（trace 逐位相同）——名义 6 个审计 quartet 中
只有 5 次不同模拟，**4 个 episode（16.7%）为重复模拟且各自计费**，该处的"独立审计"声称不成立。
**已修**（method 变为必填参数并进入种子派生 + 2 项回归测试）；
**数据不重跑**（预算用满），原数字保留并在报告 §4.6、论文 §4.4 显式披露。
**不影响**主研究（primary 的 method 恒为 `"Shared"`）。

### 本轮最重要的三项表述降级（MAJOR，已改）

1. **锚级符号异质性必须与均值同读**：`Δboth` **10/18 为负**；剔除最大 3 个正向锚后均值
   **+0.0030 → −0.0327**。新增 `heterogeneity()`，报告 §4.3a / 论文 §4.2.1。
2. **端点分辨率**：观测效应 0.003–0.033 s、区间半宽 0.05–0.09 s，而 1D 常速 TTC 的已知偏差量级约 0.2 s
   ⇒ **"未发现效应"不能与"分辨率不足"区分**。报告 §4.3b / 论文 §4.2.2。
3. **"重复携带独立信息"过强** → 改为"min-TTC **不再逐位相同**（可能携带额外信息），
   但**重复不是独立样本**，独立单元仍是锚"。

---
## 0e. V02 自主执行轮（2026-10-15）结论速览

| 核验项 | 结果 |
|---|---|
| V01 事实核验 | **225 单测 OK**；doctor 17/17 GO；账本 528 行 = 264 episodes，全 completed、全零碰撞；无效首轮 489 行 — **用户所述全部属实** |
| V01 对 formal 裁决 | **NO-GO**（主终点零方差 + 提名退化） |
| V02 协议 | **由项目负责人自主冻结**（`v02/configs/v02_frozen_v1.json`，SHA-256 `d175ec90…`）；**非外部评审** |
| V02 工程 | 8 个新模块；`doctor` 7/7 GO；**129 项测试全过** |
| V02 真实 smoke | **24/24**（完成 23、错误 1 = D37）；全部技术门槛通过；**1 次真实碰撞**；锚内方差 0.5096 s² |
| V02 真实 pilot | **240/240**（完成 240、0 错误）；**G2/G3a/G3b/G4/G6/G10/度量等价性全 PASS** |
| V02 主结果 | **未发现安全反转**（`Δgap/Δspeed/Δboth` 区间均跨 0）；**未发现可判定交互**（`I_lin` 区间跨 0） |
| 二元端点 | 54 个 quartet 中 **2 次碰撞**；`reverse=0`、`rescue=1`；**不作率推断** |
| 独立统计复核 | **PASS**（点估计与区间逐位一致，差 < 1e-12） |
| V01 formal / GitHub / V03 | **均未启动/未发布/未创建** |

新增/修改：`v02/v02lab/{anchors,quartet,adapter_real,runner,methods,phases,report,cli,__main__}.py`、
`v02/configs/v02_frozen_v1.json`、`v02/tests/test_v02_pipeline.py`、
`v02/runs/{smoke,pilot}/**`、`v02/reports/**`、`reports/v02/{REPORT.zh-CN.md,PAPER_DRAFT_EN.md}`、
`docs/{AUTONOMOUS_MASTER_PLAN,AUTONOMOUS_PROGRESS,AUTONOMOUS_DECISIONS,V02_PROTOCOL_FROZEN,
AUDIT_V01_V02,V02_BUDGET_LEDGER,OWNER_GUIDE_V02.zh-CN,RELATED_WORK_V02,HUMAN_DECISION_CHECKLIST,
FINAL_DELIVERY,V10_V02_TEST_RESULTS_20261015}.md/txt`、`docs/LATEST_HANDOFF.md`、本文件。

**未改**：`configs/formal_v01.json`（mtime 仍 2026-10-12 12:13）、`runs/**` 任何历史行、
V01 源码行为、`D:\CornerCaseLab`。

---

## 0f. 2026-10-13 第二轮复审修订 + V02 设计轮（更早轮次，保留）

| 核验项 | 结果 |
|---|---|
| R1 rule of three | 已撤回"<5%"量级宣称（独立性假设不成立）；改分层计数（episode 60 / anchor 15 / audit 3） |
| R2 VerifyFirst 排序键 | 已修正：stage-1 仅 `(first_seen, anchor_id)` 生效；**最终提名 `valid_n` 为第一枚生效键**（4 vs 1） |
| R3 TTC 确定性范围 | 已限定：仅对已采样 pilot 锚成立，不外推到未来 anchor 与碰撞事件 |
| L-01 formal 标准账本 | **已设计（PROPOSED，未实现）**：独立 canonical 21 列，与旧账本物理分离（V02 §9） |
| V02 预注册提案 | **已写入 `docs/V02_RESEARCH_PROPOSAL.md`（全 PROPOSED，未实现代码）** |
| 本轮新真实 episode | **0**（未启动 smoke/pilot/formal；账本 528 行、原始 JSON 484 个未变） |
| 代码/配置/历史 | **未改** `safefliplab/`、未改 `configs/formal_v01.json`、未删历史数据 |
| 评审建议（延续） | 工程 GO / 协议 CONDITIONAL GO / 科研对 formal **NO-GO**（见 `INDEPENDENT_SCIENTIFIC_REVIEW.md`） |

---

## 0g. 独立审计轮（2026-10-13）核验结论速览（更早轮次，保留）

| 核验项 | 结果 |
|---|---|
| `python -m safefliplab doctor` | **17/17 PASS，VERDICT: GO**（零 episode；`docs/DOCTOR_20261013.txt`） |
| 单元测试 `unittest discover -s tests` | **209 项全过（EXIT 0，47.4 s）**（190 旧 + F-01 验收 15 + 标题换行 4） |
| F-01 账本缺陷 | **已修复 + 独立验收**（`LedgerFormatError` 安全拒绝 + 遗留表头兼容；`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`） |
| 账本 `runs/episode_ledger.csv` | 528 行 = smoke 24 + pilot 240 = 264 episodes；真实账本只读复核计数/字节不变 |
| 四张图 | 无 `1e−17` 伪差、点估计不冒充置信区间、标题不裁切、TTC 标注 `NON-PROTOCOL` |
| 原始 episode JSON | 真实 HighwayEnv 输出（trajectory/policy_steps/reward/TTC/trace 指纹） |
| Git | **非 git 仓库**（无历史可记；未擅自 init） |
| 本轮新真实 episode | **0**（未启动任何 smoke/pilot/formal） |
| formal | **未获授权、未运行**；CLI 锁 + `_require_formal_go` 安全门完好 |
| 评审建议 | 工程 GO / 协议 CONDITIONAL GO / 科研对 formal **NO-GO**（见 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`） |

本轮新增：`safefliplab/ledger.py::LedgerFormatError`+`resolve_fieldnames()`、
`tests/test_ledger_legacy_acceptance.py`（15 项）、`tests/test_figure_axes.py::TestTitleWrap`（4 项）、
`report.py::_wrap_title()`、`docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`、
`docs/F01_LEDGER_ACCEPTANCE_20261013.txt`、`docs/V06_TEST_RESULTS_20261013.txt`、
`docs/DOCTOR_20261013.txt`；详见 `docs/DECISION_LOG.md` D21/D22。

---

## 1. 项目结论速览

| 阶段 | 状态 | 真实 episode | 关键结论 |
|---|---|---:|---|
| A 技术核查 | DONE | 0 | 环境/接口/schema/控制器/碰撞字段全部只读核验通过；文献 6 项 |
| B 工程骨架 | DONE | 0 | 工程目录、venv、LICENSE/README/CITATION 齐备 |
| C 仿真适配与账本 | DONE | 0 | adapter/domain/generator/runner/ledger 实现，启动即计费 |
| D 两种方法 | DONE | 0 | WideExplore/VerifyFirst/独立审计；D4/D5/D6 为 PROPOSED 待批；D11 阶段隔离 bug 已修 |
| E 统计报告 | DONE | 0 | stats/report 仅用真实数据；无数据不出图 |
| F 测试与真实试验 | DONE | 24 + 240 | **225 单测 OK**（2026-10-15 复跑确认；209→225，新增 F-06 回归 5 + 结构化产物 11）；smoke 24/24；pilot 240/240（修复后重跑） |
| G 中文知识交接 | DONE | 0 | OWNER_GUIDE / DECISION_LOG（D1–D27）/ PROGRESS / 本文件 / INDEPENDENT_SCIENTIFIC_REVIEW / V02_RESEARCH_PROPOSAL / **ACCEPTANCE_CHECKLIST**（2026-10-15 新）/ **reports/pilot/REPORT.zh-CN.md**（2026-10-15 新）/ FORMAL_READINESS_V04 |
| formal 12,800 | **NOT DONE（按协议禁止自动执行）** | 0 | **完整调度已实现（`_execute_formal_phase`）但被 CLI 锁 + 独立安全门拒绝执行，需人工 GO** |

---

## 2. 环境与复现

- 系统：Windows 10/11（win32）；Python 3.13.12 托管版，项目 venv `D:\SafeFlipLab\.venv`。
- 依赖：`cornercaselab==0.3.0`（GitHub tag v0.3.0，git 安装）、`highway-env==1.10.2`、
  `gymnasium==1.2.2`、`numpy<3`、`Pillow<13`、`matplotlib<4`。
- 冻结仿真契约：`policy=boundary`，25 s 时域，15 Hz 仿真，5 Hz 策略，schema `merge-scenario-v1`。
- 复现顺序：
  ```
  cd D:\SafeFlipLab
  .venv\Scripts\python.exe -m safefliplab doctor      # 只读校验，必须 GO
  .venv\Scripts\python.exe -m safefliplab smoke --max-episodes 24
  .venv\Scripts\python.exe -m safefliplab pilot --max-episodes 240
  .venv\Scripts\python.exe -m safefliplab report --phase smoke
  .venv\Scripts\python.exe -m safefliplab report --phase pilot
  ```

---

## 3. smoke 结果（真实，已核验）

- 命令：`python -m safefliplab smoke --max-episodes 24`（前序模型启动，已正常结束，EXIT 0；本次接管未重跑）。
- 记账（权威：`runs/episode_ledger.csv`）：发起 **24 / 完成 24 / 错误 0 / 中断 0**，恰好用满上限。
- 方法分布：WideExplore 4 quartet（anchor 0/1/2 + 同种子重放 anchor 0）、VerifyFirst 2 quartet（anchor 0/1）。
- 全部 `ego_collision=0`（各锚抵达目标，无本车碰撞）。
- **真实 HighwayEnv 证据**：`runs/manifest_smoke_WideExplore.json` 指纹确认
  `cornercaselab 0.3.0`+`highway-env 1.10.2`+`gymnasium 1.2.2`+`policy=boundary`；
  原始 `runs/<run_id>/anchor-*.json` 含 `policy_steps / reward_sum / min_forward_ttc_sampled_s /
  trace_sha256_rounded_9dp`，非 mock。
- **确定性重放**：WideExplore anchor-0 同种子两次运行
  `determinism_check.all_conditions_match=true`，四条件 trace 哈希完全一致。
- 产物：`reports/smoke_report.md`、`reports/smoke_quartets.csv`、两张图、
  `report --phase smoke` 返回 `status: OK`。

---

## 4. pilot 结果（真实，修复后重跑）

> ⚠️ **重要更正说明（透明记录）**：首次 pilot 运行（2026-10-12 接管前由前序模型启动）因
> **阶段隔离 bug** 实际只发起 220 episodes（少 20），且错误地跳过了与 smoke 共享 key 的前几个
> discovery 锚（WideExplore 0/1/2、VerifyFirst 0/1）。该运行**无效**，已移入
> `runs/_buggy_pilot_run1/`（55 个 run 目录）与 `runs/episode_ledger.csv.buggy_pilot_run1`（**489 数据行**）
> 作审计留痕，不计入有效证据。修复 bug 后**重新干净运行**得到下方有效结果。
> （账本行数口径：buggy 备份 **489** 数据行 = 整本快照含 smoke 24 + buggy pilot 220 = 244 episodes；
> 本文件旧版"440 行"只统计了 buggy pilot 自身 220×2、漏算 smoke 48 行；活动账本 **528** 数据行 =
> smoke 24 + 有效 pilot 240 = 264 episodes。三者均为真实账本，差异仅口径不同，无数据丢失或篡改。）

- 命令：`python -m safefliplab pilot --max-episodes 240`（修复后重跑，EXIT 0，耗时约 2m59s）。
- 记账（权威：`runs/episode_ledger.csv`）：发起 **240 / 完成 240 / 错误 0 / 中断 0**，恰好用满上限 240。
- 方法平衡：WideExplore **120** / VerifyFirst **120**；discovery 120 / audit 120。
- quartets：**60**（每 (method, stream) 恰好 15 个）。
  - WideExplore discovery 锚索引 **0–14 全覆盖**（含首次漏跑的 0/1/2）。
  - VerifyFirst discovery 锚 0–5（stage1 6 + selected×extra）；audit 提名 3。
- 提名（真实；可由稳定产物复核：`reports/pilot_quartets.csv`、`reports/pilot_comparisons.csv`、
  `reports/pilot_summary.json`；本行此前引用的一次性临时文件 `pilot_out2.json` 已不再保留）：
  - WideExplore discovery 提名：`anchor-0000, anchor-0001, anchor-0002`；audit 3 个提名 × 5 = 15。
  - VerifyFirst 选 3（selected_20_scaled）：`anchor-0000, anchor-0001, anchor-0002`；
    final 提名同；audit 3 个提名 × 5 = 15。
- **碰撞结果**：全部 240 个 completed episodes 的 `ego_collision=0`（本 dev_seed 样本下，两种干预
  均未产生本车碰撞；各锚均抵达目标）。因此各条件碰撞率、delta_both/gap/speed、interaction、
  reverse、rescue 在该样本下**全部为 0**。
- 这是**描述性 / 管道验证**结果，dev_seed 不构成正式证据；结论不能外推到正式评估。
- 产物：`reports/pilot_report.md`、`reports/pilot_quartets.csv`、三张图
  （`reports/pilot/figure_1_paired_condition_outcomes.png`、

  `figure_2_forest_delta_both.png`、`figure_3_discovery_to_audit.png`）、
  `reports/pilot_summary.json`、`runs/manifest_pilot_summary.json`。
- **2026-10-13 探索性补充（D20，零新 episode，非协议指标）**：从已付费原始记录提取
  连续安全裕度 `min_forward_ttc_sampled_s` 的配对差。pilot 全部 4 个 (method, stream) 组
  mean ΔTTC(both) **均为负**（WideExplore/discovery −0.0383、WideExplore/audit −0.2158、
  VerifyFirst/discovery −0.1799、VerifyFirst/audit −0.2158），即组合干预在连续裕度上
  一致地**降低**最小前向 TTC（更接近碰撞但未碰撞）。单 dev_seed、样本小、未经正式审计放大，
  **不得作为正式证据或稳定反转宣称**；详见 `reports/pilot_report.md` 探索性章节、
  `reports/pilot_margins.csv` 与 `reports/pilot/figure_4_margin_forest_ttc.png`。

---

## 5. 预算总账（真实，权威=账本）

| 阶段 | 上限 | 有效已发起 | 有效成功 | 错误 | 中断 | 备注 |
|---|---:|---:|---:|---:|---:|---|
| smoke | 24 | 24 | 24 | 0 | 0 | 有效，已验收 |
| pilot | 240 | 240 | 240 | 0 | 0 | 有效（修复后重跑）；首次无效 220 已隔离备份 |
| formal | 12800 | 0 | 0 | 0 | 0 | 未执行 |

所有失败/中断均已计入预算；本构建**未**发生任何偷偷重试（runner 启动即计费，错误立即上浮、无自动重跑）。
首次 pilot 的 220 无效 episodes 虽已在账本留痕，但**不计入有效 pilot 证据**。

---

## 6. 真实完成 / 未完成的清单

**真实完成（有证据）：**
- A–E 全部代码与单元测试（**209 项**，0 失败 0 错误；含 `TestPhaseIsolation`、`TestMasterSeedIsolation`、
  `test_ledger_safety`、`test_ledger_legacy_acceptance`、`test_formal_scheduling`、`test_formal_config`、
  `test_margins`、`test_figure_axes`）。
- smoke 24 真实 episodes（真实 HighwayEnv，预算用满，确定性通过）。
- pilot 240 真实 episodes（修复阶段隔离 bug 后重跑，预算用满，锚全覆盖）。
- 2026-10-13 接续核验轮：doctor 17/17 GO；169→183 单测全过；账本/原始 JSON/报告逐一核验吻合。
- 2026-10-13 独立审计轮：F-01 账本格式兼容修复 + 独立验收（15 项）；图表标题溢出修复（F-05）；
  全量 **209 单测 OK**；doctor 17/17 GO；产出 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`。
- 探索性连续安全裕度分析（D20）：零新 episode，基于已付费原始记录；pilot 全部 4 组
  mean ΔTTC(both) 为负（描述性，非正式证据）。
- 中文交接文档：OWNER_GUIDE.zh-CN.md、DECISION_LOG.md（D1–D22，含 D11 bug 记录）、PROGRESS.md、
  RELATED_WORK.md、PROTOCOL_V01.md、PROVENANCE.md、ATTRIBUTION.md、
  INDEPENDENT_SCIENTIFIC_REVIEW.md、本文件。
- 报告：smoke_report.md / pilot_report.md / *_quartets.csv / *_margins.csv / 各阶段图（smoke 3 张、pilot 4 张）。

**NOT DONE（明确说明）：**
- **formal 12,800 episodes：未执行。** 完整调度器 `_execute_formal_phase` 已实现（8 seed × 2 method，
  每 method×seed 800 = 400 discovery + 400 audit），但被**双层保护**拒绝执行：(a) CLI 锁
  `run_formal`/`run_formal_phase` 始终抛 `RuntimeError`；(b) 独立安全门 `_require_formal_go`
  在未获 `human_go=True` 时拒绝任何非测试替身（含 `adapter=None`）启动真实 episode。
  需你显式人工 GO，且仅在你批准 D4/D5/D6 后方可运行 `python -m safefliplab formal --confirm --max-episodes 12800`。
- **GitHub 发布：未执行，按协议禁止自动发布。**
- **旧 CornerCaseLab 项目：未改动。**

---

## 7. 正式评估（formal）前需你审核的事项

1. **PROPOSED 规则待批**（见 `docs/DECISION_LOG.md`）：
   - D4 sim_seed 完整映射（任务书只要求“四条件共享、稳定派生”，未给全映射）。
   - D5 tie-break 两单因素顺序与方向（VerifyFirst 选 20 与最终提名的完整次序）。
   - D6 pilot 内部配额（结构缩放，非任务书精确定义）。
2. **有效样本数权重**（D5/D10）：提名里 `valid_n` 的权重可能与“先看效应量”的直觉冲突，需确认。
3. **审计证据强度**：pilot 每个提名仅审计 5 个 quartet，远小于正式的 20；pilot 的 audit 结论
   **不得**外推为正式结论。
4. **8 个 formal master seed 已冻结**于 `configs/formal_v01.json`，由
   `SHA256(canonical_json(['SafeFlipLab-v01','formal-master',i]))` 派生，**非**从结果挑选。
5. 运行 formal 前建议先 `python -m safefliplab doctor` 复核环境与接口未变。
6. **本次发现的 bug（D11）**：`PhaseDriver.completed_quartets()` 与 `_records_for()` 原先未按
   `phase` 过滤，导致 pilot 的 resume 逻辑误把 smoke 已完成且 key 相同的 quartet 当作“已完成”，
   跳过前几个 discovery 锚、少跑 20 episodes。已修复（按 phase 隔离）并新增回归测试
   `tests/test_experiments.py::TestPhaseIsolation`；修复后重跑 pilot 得到有效 240。
   建议你复核该修复是否足以覆盖正式评估的断点恢复语义。
7. **（2026-10-12 接续轮）跨 master_seed 隔离已修复（D12，BLOCKER-1 解除）**：前序审计发现
   D11 的相位隔离仍**不足以支撑正式多 seed**——resume 隔离键缺 `master_seed`，8 个 formal seed 共享
   账本会彼此误复用 quartet（真实唯一 episode 仅约 1/8）。已修复（`experiments.py` 隔离键升级为 5 元组
   `(master_seed, method, anchor_index, repetition, stream)`，并新增 `master_seed` 过滤），新增
   `TestMasterSeedIsolation`（8 项，全 FakeAdapter）覆盖跨 seed 隔离、同 seed 合法恢复、force 重跑、
   launch-only、error、不同 run_id、预算耗尽等路径。单元测试 **98 → 106 全通过**；`doctor` 仍 17/17 GO；
   正式 CLI 锁（`--confirm` + `--max-episodes 12800` 才放行、之后仍 `RuntimeError` 不真跑）**未改动**。
   待你确认修复方案与回归测试后正式关闭 BLOCKER-1。
8. **（2026-10-12 本轮 V03）正式调度补齐与安全加固（D13–D16）**，全部静态 + FakeAdapter 单测、零真实 episode：
   - **D14** 补齐 `_execute_formal_phase` 完整调度；正式预算判据改为 **`method×master_seed` 累计预算 = 800**
     （旧的 `after−before==800` 会在合法**半程/全程恢复**时误报，已废弃），并单记 `new_episodes_this_call`；
     修复 `audit_results` **混流**（只读 `audit` 流）；`run_pilot` 汇总改用重开的持久化账本；每 (seed,method)
     独立 manifest 不覆盖。
   - **D13** 账本加固：`reserve_launch` **原子**（预算检查+去重+计费同一把锁）；`DuplicateLaunch` 在仿真前
     拒绝重复 key（杜绝"启动多次只计费一次"）；新账本仅写表头（消除空数据行）并提供兼容核对；
     `budget_scope` 列使 formal 8 seed × 2 method 各自独立受限。
   - **D15** 正式执行**独立安全门** `_require_formal_go`：未获 `human_go=True` 时，非测试替身（含
     `adapter=None`）在构造任何仿真器**之前**抛 `PermissionError`；`FakeAdapter` 加 `is_test_double=True`。
   - **D16** 正式配置**冻结漂移校验** `validate_formal_config`：校验种子数量/唯一性/整型/冻结值/顺序/
     协议指纹与 budget/plan/simulator 冻结值；**未修改** `configs/formal_v01.json`。
   - **单元测试 106 → 146 全通过**；`doctor` 17/17 GO；正式 CLI 锁**未解除**。详见 `docs/FORMAL_READINESS_V03.md`。
9. **（2026-10-13 独立审计轮）F-01 账本格式兼容（D21，已修复 + 独立验收，待复核）**：真实账本
   表头/数据行均为 20 列（早于 `budget_scope`），当前代码写 21 列。已新增 `LedgerFormatError`
   与 `resolve_fieldnames()`：严格前缀→补齐、**不兼容→安全拒绝**、行宽超限→拒绝；只读侧修复，
   **未改写历史账本**。独立验收 6 场景全过（含 8 进程 cap=3 不超支、无免费重试）。请复核后与
   D12–D19 一并关闭 BLOCKER-1。详见 `docs/DECISION_LOG.md` D21 与 `docs/F01_LEDGER_ACCEPTANCE_20261013.txt`。
10. **（2026-10-13 独立审计轮）BLOCKER-3 专项与评审结论**：见 `docs/INDEPENDENT_SCIENTIFIC_REVIEW.md`——
    工程可靠性 **GO**；协议合规性 **CONDITIONAL GO**（PD-01 pilot +220 待接受、D4/D5/D6 待批）；
    **科研可行性对 formal 执行 NO-GO**（零碰撞致主指标零方差、两方法提名退化不可区分、
    repetition 不重采样 ego–lead 交互、ΔTTC 为确定性属性）。报告给出保留 V01 vs 新建 V02 的利弊，
    **未代为选择**，等待 `D:\SafeFlipLab` 人工审核。
11. **（2026-10-15）F-06 缺陷已修，待复核**：`run_smoke` 由单一 `PhaseDriver(method=METHOD_WIDE)`
    串行执行两方法 job，`_new_run_id()` 却取 `self.method`，导致 smoke 的 **2 个
    VerifyFirst stage-1 quartet 的 `run_id` 内嵌 `WideExplore`**。
    **权威判据**：`sim_seed` 为 SHA-256 且含 method，实测 `1524636909` 与 `VerifyFirst` 一致
    （`WideExplore` 应为 `3812604799`）；全账本 **528/528 行 `sim_seed` 与 `method` 一致**。
    ⇒ `method` 列正确，**缺陷仅限 `run_id` 字符串**，不影响任何 Y 值/统计量/pilot/formal。
    已改为 `_new_run_id(job.method)` 并新增 5 项回归测试；**历史账本一行未改**。
    证据 `.workbuddy/tmp_audit/runid_audit_20261015.txt`。请复核后与 D12–D21 一并归档。
12. **（2026-10-15）D27-C 行为变更待复核**：`load_phase_data` 现会把「只有 launch、无 outcome」
    的已计费尝试记为 `unknown` 并计入 `incomplete`（原先被静默丢弃）。对既有 264 个 episode
    （均有 outcome 行）**零影响**；此项使报告更严格地满足协议「UNKNOWN 亦计费」的要求。

---

## 8. 交付物文件图

```
D:\SafeFlipLab\
  safefliplab/            包源码（adapter/domain/generator/runner/ledger/methods/stats/report/protocol/experiments/margins/cli）
  configs/dev_v01.json    smoke+pilot 配置（dev_seed，非证据）
  configs/formal_v01.json 冻结 formal 配置（未执行；历轮均未修改）
  tests/                  209 个单元测试（FakeAdapter/合成数据，零真实 episode）
  reports/                smoke_report.md / pilot_report.md / *_quartets.csv / *_margins.csv / <phase>/figure_*.png / *_summary.json
                          + *.pre_margin_backup（2026-10-13 重新生成前的旧版备份）
  runs/                   episode_ledger.csv（权威账本）+ 每 run 原始 episode JSON + manifest_*.json
                          + _buggy_pilot_run1/（首次无效 pilot 备份）+ episode_ledger.csv.buggy_pilot_run1
  docs/                   PROTOCOL_V01 / DECISION_LOG（D1–D20）/ PROGRESS / RELATED_WORK / PROVENANCE / ATTRIBUTION /
                          OWNER_GUIDE.zh-CN.md / LATEST_HANDOFF.md（本文件）/ FORMAL_READINESS_V02–V04 /
                          FINAL_PRE_FORMAL_AUDIT.md / V04_TEST_RESULTS.txt
  README.md / README.zh-CN.md / LICENSE / CITATION.cff / requirements.txt / pyproject.toml / .gitignore
```

（注：本项目**不是 git 仓库**，无提交历史；历轮均未 `git init`、未 push、未发布。）
