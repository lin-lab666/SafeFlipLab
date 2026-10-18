# SafeFlipLab — 最终交付清单（FINAL DELIVERY MANIFEST）

**日期**：2026-10-15（GMT+8）　│　**交付状态**：**已封存（探索性研究阶段结题）**
**项目根目录**：`D:\SafeFlipLab`
**配套文件**：`docs/FINAL_ARTIFACT_HASHES.csv`（**逐文件 SHA-256**）、
`docs/FINAL_ARTIFACT_COUNTS.md`（**生成的计数摘要**）、
`docs/REPRODUCTION_MANUAL.zh-CN.md`（复现手册）、
`docs/FINAL_CLOSURE_DECISIONS.md`（结题决策）、
`docs/FINAL_RESEARCH_AUDIT.zh-CN.md`（科研审计）、
`docs/CLAIMS_REGISTER.zh-CN.md`（主张登记）。

**计数口径（防漂移）**：本文件的**全部文件数与字节数均由脚本生成**（见 §1 的
`GENERATED-COUNTS` 区块）。历史上本节曾手工维护计数，导致同一文档内出现
**186 / 187 / 188 三个互相矛盾的总数**（审阅意见已指出）。现已改为
**单一生成来源**，并提供 `--check` 校验模式；任何漂移都会使校验失败。
**权威文件集合永远是 `docs/FINAL_ARTIFACT_HASHES.csv`（其行数即文件数）。**
缺陷认定、根因、修复与**注入式反向控制**记录见
**`docs/MANIFEST_COUNT_RECONCILIATION.md`**。

**封存边界**：本轮**零新增真实仿真**；未启动 formal；未发布 GitHub；未投稿；未创建 V03；
未修改任何历史账本行、原始记录或 V01 冻结配置。

---

## 1. 交付物总览

> 本节内容为**脚本生成**（`scripts/build_final_manifest.py`）。若要核对，运行：
> `python scripts/build_final_manifest.py --check`。

<!-- BEGIN:GENERATED-COUNTS -->
**合计 `201` 个文件 / `3367902` 字节**

> 本区块由 `scripts/build_final_manifest.py` **生成**，**请勿手工修改**。
> 权威文件集合与逐文件 SHA-256 见 `docs/FINAL_ARTIFACT_HASHES.csv`。
> 生成器**不**把清单自身（本 MD / CSV / 本计数文件）计入，避免自引用。

| 类别 | 文件数 | 说明 |
|---|---:|---|
| `config` | 5 | V01 冻结/开发配置 + V02 冻结配置与 schema |
| `doc` | 41 | 协议、决策、审计、交接、指南 |
| `evidence` | 22 | 测试/审计/复算证据的归档文本 |
| `figure` | 15 | V01 7 张 + V02 8 张真实数据图 |
| `ledger` | 8 | V01/V02 账本（唯一预算权威）+ 阶段 manifest + V01 无效首轮备份 |
| `report-final` | 2 | **中文结题报告** + **英文论文初稿** |
| `report-v01` | 16 | V01 阶段报告 / CSV / JSON |
| `report-v02` | 16 | V02 阶段报告 / CSV / JSON |
| `root` | 6 | README（中/英）、LICENSE、CITATION.cff、pyproject.toml、requirements.txt |
| `script` | 3 | `scripts/`：清单生成器 + **独立复算器** + F-06 取证（均零 episode） |
| `source-v01` | 16 | `safefliplab/` 源码 |
| `source-v02` | 18 | `v02/v02lab/` 源码 |
| `test-v01` | 22 | `tests/`（V01 单元测试；**测试数见 `docs/V13_FINAL_V01_TESTS_20261016.txt`**） |
| `test-v02` | 10 | `v02/tests/`（V02 单元测试；**测试数见 `docs/V13_FINAL_V02_TESTS_20261016.txt`**） |
| `v02` | 1 | V02 README |
| **合计** | **201** | 分类表算术合计须等于文件总数 |

**分类表算术合计 = 201 = 文件总数 = CSV 行数 = 201。**
<!-- END:GENERATED-COUNTS -->

完整路径与逐文件 SHA-256：**`docs/FINAL_ARTIFACT_HASHES.csv`**。

---

## 2. 核心交付物（**先看这些**）

| # | 文件 | 内容 |
|---|---|---|
| 1 | `reports/v02/REPORT.zh-CN.md` | **中文结题研究报告**（V02；含 M1/M2、符号约定、负结果、局限、结题声明） |
| 2 | `reports/v02/PAPER_DRAFT_EN.md` | **英文论文初稿**（**明确标注 NOT SUBMISSION READY**） |
| 3 | `docs/FINAL_CLOSURE_DECISIONS.md` | **结题决策 P1–P7**（含理由与"不意味着什么"） |
| 4 | `docs/FINAL_RESEARCH_AUDIT.zh-CN.md` | **科研审计**（已完成 / 局限 / 可公开讨论结论 / 正式实验前置条件） |
| 5 | `docs/CLAIMS_REGISTER.zh-CN.md` | **主张登记**（C1–C18 主张→证据；X1–X17 禁止表述；符号约定表） |
| 6 | `docs/LITERATURE_DIFFERENCE_TABLE.zh-CN.md` | **创新性核查 + 上游差异表**（17 行要素对比 + 4 条硬约束） |
| 7 | `docs/CORNERCASELAB_OVERLAP_VERIFIED.md` | **上游协议全文级只读重叠核验** |
| 8 | `docs/V12_INDEPENDENT_RECOMPUTE_20261015.txt` | **V01+V02 全量独立复算证据**（141 项断言全过） |
| 9 | `docs/V12_FINAL_TEST_EVIDENCE_20261015.txt` | 两套 doctor（V01 17/17、V02 7/7 GO） |
| 10 | `docs/V12_FINAL_V01_TESTS_20261015.txt` / `docs/V12_FINAL_V02_TESTS_20261015.txt` | **225 / 143 项单元测试全过**（2026-10-15 快照；**现行权威 227 / 143** 见 `docs/V13_FINAL_V01_TESTS_20261016.txt`） |
| 11 | `docs/REPRODUCTION_MANUAL.zh-CN.md` | **复现手册**（从零复现全部数字） |

---

## 3. 关键哈希（防篡改锚点）

> **口径说明（重要）**：项目中有**两种**合法的 SHA-256 口径，**不可混用**：
> - **原始字节哈希**：对文件磁盘字节直接取 SHA-256（`docs/FINAL_ARTIFACT_HASHES.csv` 用的就是它）；
> - **规范 JSON 哈希（canonical）**：对 JSON 解析后按 `sort_keys=True, separators=(',',':')`
>   重新序列化再取 SHA-256；这是**协议指纹**口径（`FrozenProtocol.protocol_hash`、doctor 使用）。

| 对象 | 口径 | 值（前 16 位） |
|---|---|---|
<!-- BEGIN:GENERATED-KEYHASHES -->
| `v02/configs/v02_frozen_v1.json` | **规范 JSON（协议指纹）** | `d175ec90eecf4e80` |
| `v02/configs/v02_frozen_v1.json` | 原始字节 | `52fc80aaa4936661` |
| `configs/formal_v01.json` | 原始字节（V01 冻结，**未执行**） | `e9232dec4b45bf7e` |
| `runs/episode_ledger.csv` | 原始字节（V01 权威账本） | `011047a8dfb0fdf7` |
| `runs/episode_ledger.csv.buggy_pilot_run1` | 原始字节（V01 作废首轮 pilot，历史留痕） | `ba5942a98c60351b` |
| `v02/runs/smoke/episode_ledger.csv` | 原始字节 | `00ca9de4a5bc21f2` |
| `v02/runs/pilot/episode_ledger.csv` | 原始字节 | `fea87c8d6e9c123e` |
| `reports/v02/REPORT.zh-CN.md` | 原始字节（中文结题报告） | `acc2ef593475a18c` |
| `reports/v02/PAPER_DRAFT_EN.md` | 原始字节（英文论文初稿） | `72fbca6e8082e67e` |
| `docs/FINAL_CLOSURE_DECISIONS.md` | 原始字节 | `bc5e6cdb7dfe755d` |
| `docs/LEDGER_RECONCILIATION_20261016.md` | 原始字节（账本对账） | `974573bd22555222` |
| `docs/FINAL_CLOSEOUT_20261016.md` | 原始字节（**本结题报告**） | `8f7eb2b17a65ff7e` |
| `scripts/independent_verify_all.py` | 原始字节（独立复算器） | `ec8cfad644b07faa` |
<!-- END:GENERATED-KEYHASHES -->

完整 64 位十六进制值见 `docs/FINAL_ARTIFACT_HASHES.csv`。

---

## 4. 真实实验与预算（唯一权威：账本）

| 版本 | 阶段 | 上限 | 已发起 | 完成 | 错误 | 中断 | 未用 |
|---|---|---:|---:|---:|---:|---:|---:|
| V01 | smoke | 24 | 24 | 24 | 0 | 0 | 0 |
| V01 | pilot（有效） | 240 | 240 | 240 | 0 | 0 | 0 |
| V01 | pilot（**无效首轮**，作废留痕） | — | 244 | — | — | — | — |
| V01 | formal | 12,800 | **0** | 0 | 0 | 0 | 12,800（**未授权**） |
| V02 | smoke | 24 | 24 | 23 | 1（D37） | 0 | 0 |
| V02 | pilot | 240 | 240 | 240 | 0 | 0 | 0 |

**失败/中断/UNKNOWN 一律计费**；无免费重试；两阶段预算不可互借；**未创建 V03**。

---

## 5. 科学结论（唯一允许的措辞，详见 `CLAIMS_REGISTER.zh-CN.md`）

1. **V01**：264 次真实 episode（smoke 24 + pilot 240）**全部零碰撞**，主终点**零方差**
   ⇒ 二元终点无法区分两方法；formal **NO-GO**。
2. **V02（探索性/描述性）**：240 次真实 episode = 216（主：18 锚×3 重复×4 条件）+ 24（审计）。
   **54 个主 quartet 全部可用**。
3. **M1（主要描述性终点）**：`Δgap +0.0127`、`Δspeed +0.0327`、`Δboth +0.0030`、`I_lin −0.0424` s，
   **四个 95% 锚级 bootstrap 区间全部跨 0** ⇒ **未发现安全反转，也未发现可判定的非可加交互**。
4. **两条必须同读的限定**：锚级符号高度异质（`Δboth` **10/18** 为负）；
   端点分辨率与效应同量级（观测 0.003–0.033 s vs 代理量 ~0.2 s）
   ⇒ **"未发现效应"不能与"分辨率不足"区分**。
5. **M2（辅助指标）**：`Δgap +0.00186`、`Δspeed −0.01069`、`Δboth −0.00623`、`I_lin +0.00261`，
   区间均跨 0；**与 M1 在 `Δgap` 上方向相反**——**该不一致被保留并公开**。
6. **技术门槛（真实数据）**：G2 0 越界；G3a 控制条件锚内方差 **0.0917 s²**（V01 为 0）；
   G4 **18/18** 锚的 min-TTC 不再逐位相同；度量等价 **240/240**，最大差 **8.3×10⁻⁶ s**。
7. **样本量（仅规划）**：n=18 最灵敏对比可检出 **0.0837 s**；MDE=0.10 ⇒ 59 锚/708 eps；
   MDE=0.05 ⇒ 235 锚/2820 eps。**MDE=0.10 s 只是规划示例，不构成授权。**
8. **无 p 值**（抽样假设未证）；**不作任何显著性声明**。

---

## 6. 已知缺陷与事故（**全部保留、未被消除**）

| 编号 | 内容 | 处置 |
|---|---|---|
| **F-06** | V01 账本 2 个 `run_id` 内嵌方法标签错误（`method` 列正确） | 修复代码，**历史账本一行未改**，D27 披露 |
| **D37** | V02 smoke 首个 episode 真实仿真已执行但归档失败 | 计费 1 次，记 error，**未重跑** |
| **D42** | V02 审计 `sim_seed` 的 method 标签被硬编码 ⇒ 两方法共享同一次审计模拟（4 个 episode 重复计费） | 修复 + 回归测试；**数据不可重跑，永久不独立**，D42/D44 披露 |
| **D43** | V02 M2 曾按**文件名通配**读取 episode ⇒ 5 个锚被审计 episode 覆盖（解析 240 而非 216）；**旧结论" M2 与 M1 方向一致"不成立** | 改为以账本 `raw_path` 为准 + 回归测试；数据未重跑 |
| **V01 无效 pilot** | 首次 pilot 因阶段隔离缺陷作废 244 次 | 备份留痕 `episode_ledger.csv.buggy_pilot_run1` |

---

## 7. 交付完整性自检

| 检查 | 结果 |
|---|---|
| 单元测试（V01 / V02） | **227 / 143 全过（EXIT 0）**（V01 225→227 见 D48；证据 `docs/V13_FINAL_V01_TESTS_20261016.txt`） |
| doctor（V01 / V02） | **17/17 / 7/7 GO**（均零 episode） |
| 独立复算（不导入报告模块） | **ALL CHECKS PASS，141 项断言** |
| 报告 ↔ 论文数值一致 | **一致**（唯一差异为千分位与 U+2212 减号的排版差异） |
| 禁用表述扫描（"方向一致/显著/证明/首次发现"等） | **仅出现在禁止或否定语境** |
| 账本孤儿 launch | **0**（V01 与 V02 各自） |
| 历史冻结文件是否被改 | **未改**（`configs/formal_v01.json` mtime 仍 2026-10-12） |
| formal 安全门 | V01 CLI **EXIT 2（拒绝）**；**V02 无 formal 入口** |
| 逐文件 SHA-256 | **由脚本生成**（`docs/FINAL_ARTIFACT_HASHES.csv`）；文件数与字节数以 §1 的生成区块为准，`--check` 校验通过 |

---

## 8. 封存声明

> SafeFlipLab 的**探索性研究阶段正式结题并封存**。
> V01 formal 永久 **NO-GO**；V02 以**完整探索性/描述性研究**结题；
> **M1** 为唯一主要描述性终点、**M2** 为辅助指标，二者方向不一致**被保留**；
> **MDE = 0.10 s 仅为规划示例**；**不作显著性声明**；历史 **D4/D5/D6 归档不追认**；
> **外部同行评审为未来可选工作、不阻塞结题**。
> 全部统计**可由原始数据独立复算**；全部已知缺陷、事故与不利结果**如实披露、未被消除**。
> **本清单所列交付物即最终状态。** 任何后续正式研究都需要**新的独立协议 + 新的明确授权预算**。
