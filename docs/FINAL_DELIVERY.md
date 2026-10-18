# FINAL_DELIVERY — SafeFlipLab 自主执行最终交付

> 授权：《SafeFlipLab — 项目总负责人自主执行授权》（2026-10-15）
> 交付日期：2026-10-15（GMT+8）
> 状态：**授权范围内工作已全部完成并落盘真实证据**；formal 相关事项按要求保持 `BLOCKED`，
> 等待你的人工裁决（见 `docs/HUMAN_DECISION_CHECKLIST.md`）。

---

## 1. 一句话结论

V01 的**主终点零方差**缺陷已在 V02 中通过改用连续终点修复并验证（锚内方差 0 → 0.0917 s²）；
**第二个缺陷（重复运行不携带信息）只被部分修好**——扰动使 18/18 个锚的 min-TTC **不再跨重复逐位相同**，
但**重复并非独立样本**，独立性未获证明。**主结果是否定的**：聚合未发现安全反转、也未发现可判定的
非可加交互 —— 但锚级高度异质（`Δboth` 有 10/18 为负），且观测效应处于端点系统误差量级。
这是一个**保留负结果、并明确标注其解释边界的真实交付**。

## 2. 交付物清单

| # | 交付物 | 路径 | 状态 |
|---|---|---|---|
| 1 | 完整源码与可执行命令 | `v02/v02lab/`（8 个新模块）、`safefliplab/`（V01，未破坏） | ✅ |
| 2 | 实际测试报告 | 结题最终：`docs/V13_FINAL_TEST_EVIDENCE_20261016.txt` + `docs/V13_FINAL_V01_TESTS_20261016.txt`（**227 项**）+ `docs/V13_FINAL_V02_TESTS_20261016.txt`（**143 项**）；历史轮次报告见 `docs/V09_*` / `docs/V10_*` | ✅ |
| 3 | 真实实验账本与全部历史预算统计 | `v02/runs/{smoke,pilot}/episode_ledger.csv`、`runs/episode_ledger.csv`、`docs/V02_BUDGET_LEDGER.md` | ✅ |
| 4 | V01/V02 科学有效性审计 | `docs/AUDIT_V01_V02.md` | ✅ |
| 5 | 统计数据与真实图表 | `v02/reports/**`（CSV ×6 + JSON + 4 图 ×2 阶段） | ✅ |
| 6 | 中文研究报告 | `reports/v02/REPORT.zh-CN.md` | ✅ |
| 7 | 英文论文初稿 | `reports/v02/PAPER_DRAFT_EN.md`（**明确标注非投稿稿**） | ✅ |
| 8 | 中文教学与复现指南 | `docs/OWNER_GUIDE_V02.zh-CN.md` | ✅ |
| 9 | 正式评估人工决策清单 | `docs/HUMAN_DECISION_CHECKLIST.md` | ✅ |
| 10 | 文献综述（增补，已核验） | `docs/RELATED_WORK_V02.md` | ✅ |
| 11 | 自主计划/进度/决策 | `docs/AUTONOMOUS_{MASTER_PLAN,PROGRESS,DECISIONS}.md` | ✅ |
| 12 | 冻结协议 | `docs/V02_PROTOCOL_FROZEN.md` + `v02/configs/v02_frozen_v1.json` | ✅ |

## 3. 真实运行记录

### 3.1 V02（本轮新增）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python -m v02lab doctor` | 0 | 7/7 PASS，VERDICT: GO（零 episode） |
| `python -m unittest discover -s tests` | 0 | **Ran 131 tests, OK** |
| `python -m v02lab smoke --max-episodes 24` | 0 | 已发起 **24/24**；完成 23、错误 1（D37）、中断 0；墙钟 26.0 s |
| `python -m v02lab pilot --max-episodes 240` | 0 | 已发起 **240/240**；完成 **240**、错误 0、中断 0；墙钟 262.5 s |
| `python -m v02lab report --phase smoke` / `pilot` | 0 | 生成全部 CSV/JSON/MD/图（零 episode） |
| `scripts/independent_verify_all.py` | 0 | **PASS**（V01+V02 全量复算；点估计与区间逐位一致） |

### 3.2 V01（只读复核，未重跑）

`doctor` 17/17 GO；`unittest` **Ran 225 tests, OK**（当时口径；结题执行后为 **227**，见 D48）；账本 528 数据行 = 264 episodes（全 completed、
全 `ego_collision=0`）；无效首轮备份 489 数据行。
**未启动任何 V01 episode；未修改 V01 账本/配置/数据。**

## 4. 主要科学结论（仅真实数据）

**V02 pilot（18 锚 × 3 重复 = 54 个完整 quartet，240 次真实仿真）**

| 效应量 | 点估计 (s) | 95% 锚级 bootstrap 区间 (s) | 反转到？ |
|---|---:|---|---|
| `Δgap` | +0.0127 | [−0.0525, +0.0769] | 否 |
| `Δspeed` | +0.0327 | [−0.0589, +0.1243] | 否 |
| `Δboth` | +0.0030 | [−0.0436, +0.0526] | 否 |
| `I_lin` | −0.0424 | [−0.1465, +0.0613] | 交互不可判定 |

- 二元端点：54 个 quartet 中仅 **2 次碰撞**（条件 00 与 10 各 1）；`reverse=0`、`rescue=1`；
  **不作任何率推断**。
- `I_log`：53/54 可定义，均值 −0.081。
- 辅助方法比较（探索性）：VerifyFirst `precision@k = 3/3`、WideExplore `1/3`，**不构成结论**。

**技术验证（V02 修正生效的直接证据）**：

| 项 | V01 | V02 pilot |
|---|---|---|
| 锚内 min-TTC 方差 | 0（构造性） | **0.0917 s²** |
| min-TTC 跨重复逐位相同的锚 | 36/36 组 | **0/18** |
| 度量与上游一致性 | 未对拍 | **240/240 一致，最大差 8.3e−6 s** |
| 区间可估计 | 否（零方差） | **是** |

## 5. 项目 DONE / BLOCKED / NOT DONE

**DONE（有证据）**
- 阶段 1–8 全部完成（详见 `docs/AUTONOMOUS_PROGRESS.md`）。
- V02 协议冻结、工程实现、**143 项测试**（第三轮收尾后的最终计数；第二轮时为 142、首轮为 129）、
  真实 smoke 24 + pilot 240、统计与图表、中文报告、
  英文论文初稿、教学指南、审计、预算总账、独立统计复核。

**BLOCKED（需你裁决，非技术阻塞）**
- 正式样本量（无 MDE / 多重性方案）。
- 与 CornerCaseLab 的公开文档重叠核验。
- 「四条件反事实干预 / 安全反转」的新颖性核验。
- 外部同行评审的覆盖范围。

**NOT DONE（明确不做）**
- V01 formal 12,800（**NO-GO**：主终点零方差）。
- V02 formal（**未授权**；V02 无 formal 入口）。
- GitHub 发布 / 投稿 / 付费资源。
- 未创建 V03。
- 提案中的 P3（lead 减速）与「lead 初速≠目标速」——受「不改物理语义」约束未实现（D31、L7）。

**已知缺陷（已修或已披露）**
- **D37**：V02 新写 runner/adapter 契约不一致，消耗 1 个 smoke 预算；已修 + 4 项回归测试；
  历史不改写；**未重跑**。
- 文档/配置**种子笔误**（docs 写 20251015、配置为 20261015）——由独立复核发现并修正；
  **已发布结果使用的是配置值，未受影响**。

## 6. 边界合规自检

| 边界 | 结果 |
|---|---|
| 仅写入 `D:\SafeFlipLab`；未触碰 `D:\CornerCaseLab` | ✅ |
| 未改写 V01 冻结配置 / 旧账本 / 历史记录 | ✅（`configs/formal_v01.json` mtime 仍 2026-10-12 12:13） |
| 未启动任何 formal | ✅（V01 CLI 双保险仍拒绝；V02 无 formal 入口） |
| V02 预算未超：smoke 24/24、pilot 240/240，未互相借用 | ✅ |
| 未提权 / 未改系统 Python / 未改 ACL | ✅ |
| 未公开 GitHub / 未投稿 / 未付费 / 未外发数据 | ✅ |
| 未把未审核方案宣称为正式批准 | ✅（全部标注「项目负责人自主冻结，非外部评审」） |
| 未创建 V03 获取额外预算 | ✅ |

## 7. 恢复方式（已实测）

- 会话中断后：读 `docs/AUTONOMOUS_PROGRESS.md` + `docs/LATEST_HANDOFF.md` + `docs/V02_BUDGET_LEDGER.md`
  即可恢复状态与预算。
- **幂等恢复已实测**：`report --phase` 可重复执行（账本行数不变）；
  `smoke`/`pilot` 再调用会被预算账本**拒绝**（不重跑、不重复计费）——
  该行为由 `tests/test_v02_pipeline.py::TestRunnerSafety` 覆盖。
- 恢复命令：
  ```powershell
  cd D:\SafeFlipLab\v02
  ..\.venv\Scripts\python.exe -m v02lab doctor
  ..\.venv\Scripts\python.exe -m unittest discover -s tests
  ..\.venv\Scripts\python.exe -m v02lab report --phase pilot
  ```

## 8. 下一条安全操作

1. 阅读 `docs/HUMAN_DECISION_CHECKLIST.md`，逐项裁决（尤其 A1–A7、B1–B4、D2）。
2. 在裁决完成前，**不要**授权任何 formal 运行。
3. 若需推进论文，请先明确 D2（新颖性核验）与 D3（外部评审）的处置方式。

---

# 附录：第二轮（无仿真收尾与复核修正，2026-10-15）

> 本轮**未消耗任何新增真实仿真预算**。起因：用户要求执行《最终一次性自主完成总任务书》，
> 但**该附件未随消息附带**（Downloads 无新文件、近 3 小时无新增文档）。
> 依消息正文所述边界（不授权任何新增真实仿真、不授权 formal / GitHub / 投稿）执行可做之事。

## A. 本轮完成的七项工作

| # | 工作 | 产出 | 状态 |
|---|---|---|---|
| P1 | 记录附件缺失并更新作业计划 | 本附录 + `docs/AUTONOMOUS_PROGRESS.md` 第二轮 | ✅ |
| P2 | **正式样本量推导**（由 18 锚方差） | `v02lab/power.py`（+11 测试）、`docs/V02_SAMPLE_SIZE_DERIVATION.md` | ✅ |
| P3 | **CornerCaseLab 公开文档重叠核验** | `docs/CORNERCASELAB_OVERLAP_VERIFIED.md` | ✅ |
| P4 | **新颖性文献核验**（非穷尽） | `docs/RELATED_WORK_V02.md` §4 | ✅ |
| P5 | **两位独立对抗性复核 + 全部修正** | `docs/REVIEW_RESPONSE.md`、D41/D42 | ✅ |
| P6 | **正式评估准备包**（只准备、不执行） | `docs/V02_FORMAL_READINESS_PACKAGE.md` | ✅ |
| P7 | 论文与文档更新 | 报告/论文/OWNER_GUIDE/FINAL_DELIVERY 修正 | ✅ |

## B. 关键新增结论

1. **样本量**：锚级 SD `Δgap 0.144 / Δspeed 0.203 / Δboth 0.106 / I_lin 0.229` s。
   **n = 18 时只能检出 ≥ 0.084 s 的效应** —— 这在统计上解释了 pilot 的"接近零但不可判定"。
   MDE = 0.10 s ⇒ **59 锚 / 708 eps**；MDE = 0.05 s ⇒ 235 锚 / 2820 eps。
   **正式样本量仍未冻结**，需人工先声明 MDE 并加强方差估计。
2. **上游重叠**：CornerCaseLab 的「方法比较 / 独立审计 / 等预算配对 / 不报 p 值」全部重叠
   ⇒ **V02 的"无 p 值"属趋同、不是新颖点**；候选新增点收窄为三条并须附限定。
3. **独立复核**：共 1 项 MAJOR 代码缺陷 + 3 项 MAJOR 过度声称 + 12 项 MINOR/INFO，**全部已处置**；
   **未影响** V02 的任何量化主结果。
4. **最重要的代码缺陷（D42）**：审计 `sim_seed` 的 method 标签被硬编码为 `"shared"`，
   使两方法对同一锚的审计**共用同一次模拟**（4 个 episode 重复且各自计费）。
   **已修 + 回归测试；数据不重跑，原样披露。**
5. **最重要的三项表述降级**：锚级符号异质性（`Δboth` 10/18 为负）、端点分辨率与效应同量级、
   "重复携带独立信息"过强 —— 均已改为与证据相符的措辞。

## C. 本轮之后的 DONE / BLOCKED / NOT DONE（增量）

- **新增 DONE**：样本量推导、上游重叠核验、新颖性核验、独立复核与修正、正式准备包。
- **BLOCKED 减少**：原「与 CornerCaseLab 公开文档重叠核验」与「新颖性核验」**已解除**
  （降级为"仅 README 层面/非穷尽"，若要升级为全文级比对仍需人工授权）。
- **仍 BLOCKED**：MDE 未声明；方差估计未加强；正式主种子未批准；无确证性检验定位未确认；
  端点分辨率未解决；外部同行评审未安排。
- **NOT DONE（明确不做）**：任何新增真实仿真；formal；GitHub；投稿；V03。

## D. 最终状态

- 测试（**当时口径**）：V02 **142 项 OK**（第三轮收尾后为 143）；V01 **225 项 OK**（结题执行为 227）。
- 独立统计复核：**PASS**（点估计与区间与报告逐位一致）。
- 真实预算：V02 smoke **24/24**、pilot **240/240**（均用满）；**本轮新增 0**。
- 历史数据：**未改动任何一行**。
- **下一条安全操作**：阅读 `docs/HUMAN_DECISION_CHECKLIST.md`（尤其 A1–A8、B1–B4、D1–D3）逐项裁决。

---

# 附录 B：第三轮（最终科研质量收尾，2026-10-15，零新增真实仿真）

> 本轮为**最终收尾**。不启动任何新开发循环，不新增真实仿真，不启动 formal，
> 不发布 GitHub，不投稿，不创建 V03，不以新版本重置预算。
> 完整审计见 **`docs/FINAL_RESEARCH_AUDIT.zh-CN.md`**。

## B.1 本轮新增/更正的产物

| 文件 | 说明 |
|---|---|
| **`docs/FINAL_RESEARCH_AUDIT.zh-CN.md`** | **主交付物**：已完成内容 / 研究局限 / 可公开讨论的结论 / 正式实验前置条件（P1–P7、E1–E9） |
| `docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md` | **新**：与上游 CornerCaseLab + 公开文献的 17 行逐项差异表 + 4 条硬约束 |
| `docs/CORNERCASELAB_OVERLAP_VERIFIED.md` §6 | **新**：其**公开协议文档全文**级只读核验 |
| `reports/v02/REPORT.zh-CN.md` §4.3c / §4.6 / §5 / §6 / §8 | **重写**：M2 更正、留一敏感性、新增 L17、M2/M1 方向不一致 |
| `reports/v02/PAPER_DRAFT_EN.md` §2 / §4.2.3 / §5 / §6 / §7 | **重写**：M2 更正、样本量推导、上游重叠、原创性声明、缺陷披露 |
| `v02/v02lab/report.py` | **修复 D43**：`m2_from_raw()` 改为以账本 `raw_path` 为准；M2 markdown 增加方向警告 |
| `v02/tests/test_v02_pipeline.py` | **新增** `TestM2DoesNotReadTheAuditStream`（+1 测试 ⇒ V02 143 项） |
| `docs/AUTONOMOUS_DECISIONS.md` D43/D44 | 缺陷与核验结论记录 |
| `docs/V11_FINAL_V01_TESTS_20261015.txt` 等 3 份 | 测试与审计证据归档 |

## B.2 本轮三项核验结论（数字）

1. **样本量推导自洽**：`n = ceil((z_{1-α/2}+z_power)²·sd²/MDE²)`，α = 0.05（Holm 最坏 ⇒ 0.0125/对比，族 4）、
   power = 0.80。**n = 18 最灵敏对比 `Δboth` 的 MDE = 0.0837 s**（`i_lin` 最迟钝 = 0.180 s）；
   MDE = 0.10 ⇒ **59 锚 / 708 eps**；MDE = 0.05 ⇒ **235 锚 / 2820 eps**。
   **0.084 与 59 之间无直接换算**——它们对应**不同 MDE 目标**；若目标取 0.084 s，所需锚数即回到 18。
2. **240 ↔ 54 完全对应**：240 = 216（主：18 锚×3 重复×4 条件）+ 24（审计：2 方法×3 提名×1 quartet×4 条件）；
   216/4 = **54 主 quartet，全可用**；孤儿 launch **0**。
3. **审计种子复用 ⇒ 历史数据不独立**：6 个名义审计 quartet 只有 **5 次不同模拟**；
   **留一后 WideExplore `1/3 → 0/2`、VerifyFirst `3/3 → 2/2`** ⇒ WideExplore 的唯一命中
   **完全依赖**与对手共享的那一次模拟。**代码已修，但历史数据永久不独立。**

## B.3 本轮新发现的实质缺陷（D43）

**次要终点 M2 曾读取错误的 episode 集合**：`m2_from_raw()` 按**文件名通配**枚举 episode，
而主研究流与辅助审计流**写出同名文件**（`<anchor_id>_rep<r>_<cond>.json`），
审计 episode 在排序中后读并**覆盖**主研究值（5 个被提名锚的 `rep0`；解析 240 而非 216）。
**∴ 旧结论「M2 与 M1 方向一致」不成立**：更正后 **`Δgap` 在两终点上方向相反**
（M1 `+0.0127` vs M2 `+0.00186`，区间均跨 0）。**仅影响 M2**；已修复 + 回归测试；
**数据未重跑、未改写**。

## B.4 最终状态

- 测试：**V01 227 项 OK**（结题执行后由 225→227，见 D48）；**V02 143 项 OK**（均 EXIT 0）。
- doctor：**V01 17/17 GO；V02 7/7 GO**（均零 episode）。
- 独立统计复核：**PASS**（M1 四对比点估计与区间差 **0.0**）。
- 真实预算：V01 264 + 无效 244；V02 smoke **24/24**、pilot **240/240**；**本轮新增 0**。
- 历史数据：**未改动任何一行**；V01 formal 安全门仍拒绝（EXIT 2）；**V02 无 formal 入口**。
- **下一条安全操作**：阅读 `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` §4，逐项裁决 P1–P7；
  在此之前**不要**启动任何正式评估。

---

# 附录 C：第四轮（最终闭环结题与封存，2026-10-15，零新增真实仿真）

> **探索性研究阶段正式结题并封存。** 完整清单见 **`docs/FINAL_DELIVERY_MANIFEST.md`**。

## C.1 结题状态（负责人一次性确定）

1. **V01 formal：NO-GO（永久）**。
2. **V02：以完整的探索性、描述性研究结题**。
3. **M1（最小前向 TTC）为主要描述性终点；M2（低 TTC 步占比）为辅助指标**；
   二者在 `Δgap` 上的**方向不一致被保留并公开**。
4. **MDE = 0.10 s 仅为未来样本量规划示例**，**不构成任何授权**。
5. **不作显著性声明**（抽样假设未证，无 p 值）。
6. **历史 D4/D5/D6 归档，不追认批准**。
7. **外部同行评审为未来可选工作，不阻塞结题**。
8. 未增加任何真实仿真、未启动 formal、未发布 GitHub、未投稿、未创建 V03。

## C.2 本轮新增交付物

| 文件 | 内容 |
|---|---|
| `docs/FINAL_CLOSURE_DECISIONS.md` | **P1–P7 结题决策**（含理由与"不意味着什么"） |
| `docs/CLAIMS_REGISTER.zh-CN.md` | **主张登记**：C1–C18 主张→证据；X1–X17 禁止表述；符号约定表 |
| `docs/FINAL_DELIVERY_MANIFEST.md` | **最终交付清单**（类别、核心交付物、关键哈希、预算、结论、缺陷、完整性自检） |
| `docs/FINAL_ARTIFACT_HASHES.csv` | **逐文件 SHA-256**（文件数与字节数由脚本生成；权威值见该 CSV 行数与 `docs/FINAL_ARTIFACT_COUNTS.md`；含说明：原始字节哈希 vs 规范 JSON 哈希两种口径） |
| `docs/REPRODUCTION_MANUAL.zh-CN.md` | **复现手册**（一键复现、逐项核对、安全门、哈希核对、常见问题、复现边界） |
| `scripts/build_final_manifest.py` | 交付清单与哈希生成器（只读、零 episode） |
| `scripts/independent_verify_all.py` | **V01+V02 全量独立复算器**（不导入任何报告模块；规范位置） |
| `docs/V12_*` `docs/V13_*` | 测试、复算与最终验收证据 |

## C.3 本轮核验结论（数字）

1. **独立复算**：**141 项断言 ALL CHECKS PASS**。V01（smoke/pilot 计数、60 quartet、
   4×(method,stream) 碰撞/反转/救援、12 组 ΔTTC 裕度）与 V02（M1 四对比点估计与 bootstrap 区间、
   M2 四对比与条件均值、辅助审计 `precision@k`、5 次不同模拟、样本量网格）**逐位一致**。
2. **口径澄清**：`n_primary_quartets`（四条件均已计费）≠ `n_usable_quartets`（四条件均有可恢复值）；
   smoke = **6 / 5**、pilot = **54 / 54**。
3. **缺陷类别扫描**：D43 同类缺陷**仅一处**（`m2_from_raw`，已修 + 回归测试）；V01 全部读取点基于账本。
4. **幂等性**：`report --phase` 重跑后 **32 个报告产物逐字节相同**。
5. **测试**：V01 **227/227 OK**、V02 **143/143 OK**；doctor **17/17 / 7/7 GO**。

## C.4 最终状态

- 真实预算：V01 264（+ 无效首轮 244）；V02 smoke **24/24**、pilot **240/240**；**本轮新增 0**。
- 历史数据：**一行未改**；`configs/formal_v01.json` mtime 仍 2026-10-12。
- 安全门：V01 formal **EXIT 2**；V02 smoke/pilot **EXIT 2**；**V02 无 formal 入口**。
- **下一轮：无。** 任何后续正式研究都需要**新的独立协议 + 新的明确授权预算**。
