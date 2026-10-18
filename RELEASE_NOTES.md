# SafeFlipLab 发布说明（RELEASE NOTES）

- **发布日期**：2026-10-17（GMT+8）
- **发布负责人**：成员 A（工程发布负责人 AI），经总控授权执行；本版为**返工重建版**
  （总控裁定：初版违反默认排除规则，退回重建；初版证据保留于审计目录 `p1_a/`）
- **仓库可见性**：**PRIVATE**（GitHub 私有仓库；git 初始化/提交/推送由总控在 P3 执行）
- **内容性质**：SafeFlipLab 结题时点（ENGINEERING CLOSEOUT PASS / SCIENTIFIC CLAIM
  INCONCLUSIVE）的**授权快照**——包含源码、测试、配置与**结果汇总**；
  **不包含**原始 episode 级数据与账本（见 §3 数据可用性声明）。

---

## 1. 结题状态摘要

- **工程结题：PASS。** 独立复算 141 项断言全过、manifest 闸门 PASS
  （201 文件 / 3,367,902 字节 / 15 类 / 13 关键哈希，EXIT 0）、doctor V01 17/17 +
  V02 7/7 GO、测试 V01 **227** + V02 **143** 全过、报告产物 58/58 逐字节幂等、
  账本与原始数据全口径对账通过（有效 528 / 历史发起 748 / 孤儿 0）。
- **科研结论：INCONCLUSIVE**（合法结题结果）。V02 为探索性/描述性研究；
  两主终点方向不一致，保留并公开；不产出 p 值、不作显著性声明；
  MDE=0.10 s 仅为样本量规划示例。
- V01 formal（12,800 episodes）**永久 NO-GO**：已实现、未授权、未运行。
- 完整结题报告与审计证据不在本仓库内（保存于项目外审计目录）。

## 2. 计数口径（P0.4 核对结果）

### 2.1 审计证据计数（两种口径）

| 口径 | 数值 | 构成 |
|---|---:|---|
| 口径一（不含最终报告） | **154** | round1 37 + round2 52 + rework_r1 18 + rework_r2 27 + reverify_r1 20 |
| 口径二（含最终报告） | **155** | 口径一 + `final/FINAL_CLOSEOUT_REPORT.md` |

**本说明采用口径二（155，含最终报告）**：陈述结题证据总量时，最终结题报告是
结题阶段的正式产物，应计入。以上证据文件均**不在**本发布包内。

### 2.2 grep `335|336` 疑点订正（对结题项目重跑实测）

`reverify_r1/REVERIFY_REPORT.md` R1 声称"docs/ 共 8 行命中"（其分类相加实为 9），
`reverify_r1/hashes/r1_grep_335_336_adjudication.txt` 自称"7 文件 8 行"却列出
10 个行号。对结题项目 `D:\SafeFlipLab` 重跑 `grep -rn "335\|336" docs/`：

- **真实结果：7 个文件、10 个行号**（子串匹配口径，与原始判据一致）。
- 逐行分类：更正记录 3（`AUTONOMOUS_DECISIONS.md:402,403,405`，D50）+
  返工记录 2（`AUTONOMOUS_PROGRESS.md:261`、`LATEST_HANDOFF.md:41`）+
  脚本生成块 2（`FINAL_ARTIFACT_COUNTS.md:7`、`FINAL_DELIVERY_MANIFEST.md:31`，
  均为 3367902 = `--check` 实测）+ 哈希串子串 2（`FINAL_ARTIFACT_HASHES.csv:103,163`）+
  浮点值子串 1（`V12_INDEPENDENT_RECOMPUTE_20261015.txt:130`）。
- **订正**：两处"8 行"均为计数笔误，真实为 **10 行 / 7 文件**；adjudication 文件
  列出的 10 个行号清单与本次实测逐行一致。疑点为取证计数笔误，不影响结题结论
  （docs/ 内无手工固化的现行 bytes 硬编码；现行权威计数 201 / 3367902 与
  `--check` 实测一致）。审计原件按约束未改动，订正记录于本说明。

### 2.3 本发布包口径

- **发布包磁盘文件数：201**；`PUBLICATION_MANIFEST.csv` 登记 **199** 行
  （= 201 − 清单自身 − `scripts/verify_publication.py`，避免自引用）；
  约 3.1 MB（精确字节数以 `PUBLICATION_MANIFEST.csv` 汇总与审计目录构建日志
  的脚本实测输出为准；本说明自身计入该总数，故不在此固化易漂移的精确值）。
- 与原项目结题口径（**201** 文件 / 3,367,902 字节，含 `runs/` 全量，见
  `docs/FINAL_ARTIFACT_COUNTS.md` 与 `docs/FINAL_ARTIFACT_HASHES.csv`）的关系：
  原口径中除原始数据外的文件基本全部包含在内；本包**不含** `runs/`、
  `v02/runs/`（原始 episode JSON 与账本，共 762 个文件）及 2 个含开发机个人
  路径的文档。两个口径独立记录、互不覆盖。原项目的
  `scripts/build_final_manifest.py --check` 面向含 `runs/` 的完整口径，
  **在本发布包内不适用**（将因缺少 runs/ 失败）；本包完整性以
  `PUBLICATION_MANIFEST.csv` + `scripts/verify_publication.py` 为准。

## 3. 数据可用性声明（重要）

- **包含**：全部源码（`safefliplab/`、`v02/v02lab/`）、测试（`tests/`、
  `v02/tests/`）、冻结/开发配置（`configs/`、`v02/configs/`）、阶段结果汇总
  （`reports/` 28 个 + `v02/reports/` 24 个：报告 md、图 png、CSV、JSON、JSONL）
  与结题/协议/复现文档（`docs/` 64 个）。
- **不包含**：原始 episode 级数据与账本——`runs/`（490 个文件）与
  `v02/runs/`（272 个文件），含每 episode 原始 JSON、`episode_ledger.csv*`、
  manifest、作废首轮 `_buggy_pilot_run1/` 备份。这些原始数据由项目负责人保存，
  确有需要者可向项目负责人提出合理申请。
- 因此：`scripts/independent_verify_all.py`（独立复算器）的**完整重跑需要
  私有原始数据**；在本发布包范围内，复现性以**测试套件**（V01 227 + V02 143，
  合成数据/mock，不消耗真实 episode）与**结果摘要**（`reports/`）为准。

## 4. 纳入清单（正向允许，实测计数）

| 类别 | 路径 | 文件数 |
|---|---|---:|
| 源码 | `safefliplab/` | 16 |
| 源码 | `v02/v02lab/` | 18 |
| 测试 | `tests/` | 22 |
| 测试 | `v02/tests/` | 10 |
| 配置 | `configs/` + `v02/configs/` | 5 |
| 脚本 | `scripts/`（原 3 个 + 发布校验器 `verify_publication.py`） | 4 |
| 结果汇总 | `reports/` | 28 |
| 结果汇总 | `v02/reports/` | 24 |
| 文档 | `docs/`（66 − 2，见 §5） | 64 |
| 根文件 | README（中/英，发布版）、RELEASE_NOTES.md、LICENSE、CITATION.cff、pyproject.toml、requirements.txt、.gitignore（重建） | 8 |
| V02 README | `v02/README.md` | 1 |
| **小计（各类合计，不含 manifest 自身）** | | **200** |
| 磁盘总数 | 小计 200 + `PUBLICATION_MANIFEST.csv` 自身 | **201** |
| 其中自引用不登记 | `PUBLICATION_MANIFEST.csv`、`scripts/verify_publication.py` | −2 |
| **PUBLICATION_MANIFEST.csv 登记行数** | | **199** |

### 报告产物中的绝对路径（披露，未篡改）

`reports/` 与 `v02/reports/` 的结果产物系结题时点由原项目路径
（`D:\SafeFlipLab\...`）生成，部分 CSV/JSONL 的 `raw_path` 列与 md 报告中
**保留原始绝对路径字符串**（发布纪律：不为发布而篡改结果产物字节）。
这些路径指向原开发位置，其中 `raw_path` 引用的原始 episode JSON **不在本包内**
（见 §3）。发布副本与项目归档在这些结果产物及保留文档上**逐字节一致**
（未做任何改写）；相对源项目，本包新增/改写的文件仅 6 个：README（中/英，
发布版）、`RELEASE_NOTES.md`、`.gitignore`（重建）、
`scripts/verify_publication.py`（新增）、`PUBLICATION_MANIFEST.csv`（新增）。
同理，`docs/` 保留的文档中引用的 `D:\SafeFlipLab` 项目路径亦为原文。

**`D:\` 绝对路径实测统计**（本次对发布副本全树重跑）：除本说明自身外
共 **921 次、分布于 38 个文件**（docs 19、reports 8、reports/v02 1、
v02/reports 6、scripts 2、根文件 2；集中于 episodes CSV/JSONL 的
`raw_path` 列与结题文档路径引用）。本说明自身的 `D:\` 引用未计入
（自指计数随订正记录增长，不固化；含自身合计见 §9）。全部为
`D:\SafeFlipLab` 项目路径，非个人目录；开发机用户目录个人路径命中
**0**（订正记录见 §9）。

## 5. 排除清单（默认排除，实测计数）

| 排除项 | 数量 | 理由 |
|---|---:|---|
| `runs/` | **490 个文件** | 原始 episode JSON + 账本 + manifest + 作废首轮备份（默认排除；数据可用性见 §3） |
| `v02/runs/` | **272 个文件** | 同上（V02 原始数据与账本） |
| `*.lock` | 3 | 运行时锁（零字节），使用时重新生成 |
| `*.pre_margin_backup` + `*.stale_zero_backup` | 7 | 过程备份（margin 指标引入前旧版报告、陈旧零值 manifest） |
| `docs/V02_ENGINEERING_PREP_20261013.md`、`docs/VERIFICATION_20261013.md` | 2 | 曾含开发机用户目录下的个人路径（本说明仅作文本描述、不保留任何用户目录字面量；发布指令点名排除，全 docs/ 扫描确认恰此 2 个） |
| `.venv/`、`.workbuddy/` | 2 目录 | 虚拟环境 / agent 工作区 |
| `__pycache__/`（safefliplab、tests、v02/v02lab） | 3 目录 | 字节码缓存 |

**文件合计排除 770 个**（互斥实计）+ 5 个目录。

互斥口径说明：分项相加 490 + 272 + 3 + 7 + 2 = 774 中有 4 项重复——`*.lock`
3 个与 `runs/manifest_pilot_summary.json.stale_zero_backup` 1 个均位于
`runs/`、`v02/runs/` 内，已计入 490/272 的目录计数；按互斥实计为
490 + 272 + 6 + 2 = **770**（lock 类在 runs/ 之外实为 0，backup 类在
runs/ 之外为 6）。该计数经成员 B 独立复核确认；原 774 申报为重复相加
误差，订正记录见 §9。

排除的 2 个文档被 `docs/DECISION_LOG.md`、`docs/V02_PROTOCOL_REVIEW_CHECKLIST.md`、
`docs/V02_RESEARCH_PROPOSAL.md` 引用（`docs/FINAL_ARTIFACT_HASHES.csv` 亦登记其
哈希行，该 CSV 为原项目 201 口径记录、非本包清单）——这些引用在本包内为
**悬空引用**，特此披露；被排除文档内容属项目侧内部过程记录。

`.gitignore`（发布版）已重建：**不跟踪** `runs/`、`v02/runs/`；忽略
`.venv/`、`__pycache__/`、`*.pyc`、`*.lock`、`*.pre_margin_backup`、
`*.stale_zero_backup` 及 OS/编辑器文件。

## 6. 完整性校验与防篡改实证

- `PUBLICATION_MANIFEST.csv`：本包每个已登记文件的相对路径 / 字节数 / SHA-256
  （清单自身与包内校验器不登记，避免自引用）。
- 校验命令（任一行被篡改、文件增删均以非零退出失败）：

  ```powershell
  .\.venv\Scripts\python.exe scripts\verify_publication.py
  ```

- **负面控制实证**（在隔离副本上执行，发布副本本体零写入；结果见审计目录
  `p1_a_rework/logs/rework_tamper_test.txt`）：

| 场景 | 预期 | 实测 |
|---|---|---|
| 基线校验 | EXIT 0 | **PASS** |
| 篡改一个已登记文件内容 | EXIT≠0 | **捕获** |
| 篡改 manifest 一行 | EXIT≠0 | **捕获** |
| 新增未登记文件 | EXIT≠0 | **捕获** |
| 删除一个已登记文件 | EXIT≠0 | **捕获** |
| 恢复后 | EXIT 0 | **PASS** |

- 已知边界：包内自校验无法防范"同时篡改清单行与对应文件"；清单 CSV 的哈希已在
  项目外审计目录留证（`SafeFlipLab_RELEASE_AUDIT_2026-10-17/p1_a_rework/logs/`），
  PRIVATE 仓库提交本身亦为外部锚。
- 生成脚本 `build_publication_manifest.py` 按发布指令**不放入发布副本**，
  存放于审计目录（manifest 生成为发布时动作）。

## 7. 许可

- SafeFlipLab 自身代码：**Apache-2.0**（`LICENSE` 为正本：结构 15/15 项 OK、
  11,357 字节 = 官方标准大小、纯 LF、头尾段与 apache.org 官方文本逐字一致；
  `pyproject.toml` 与 `CITATION.cff` 许可字段均为 `Apache-2.0`）。
- 仿真接口 CornerCaseLab v0.3.0：Apache-2.0，以安装依赖方式使用；HighwayEnv /
  Gymnasium 等保留各自许可。详见 `docs/PROVENANCE.md`、`docs/ATTRIBUTION.md`。
- 核实局限：本环境 curl 直连 apache.org 不可达，未能做端到端逐字节 diff，
  以 结构 + 大小 + 行尾 + 头尾比对 四项交叉认定（详见审计留证）。

## 8. 已知事项

- **G-1…G-10**（新增真实仿真 / 启动 formal / 重跑 smoke-pilot / 修改冻结配置或
  历史数据 / 改动上游 CornerCaseLab / GitHub 发布或投稿 / 付费服务与全局权限 /
  获取上游 PROTOCOL_TODO 与源码 / 安排外部同行评审 / 提高端点保真度）——
  **全部需人工新授权**，本发布未发生其中任何一项。
- `scripts/independent_verify_all.py` 的 `ROOT` 常量硬编码原项目路径
  （`D:\SafeFlipLab`），且需要私有原始数据；在本仓库 checkout 位置运行时需改为
  本地路径并在具备原始数据的环境运行（该脚本尾部会写证据文件，应在隔离副本运行）。
- 英文论文初稿 `reports/v02/PAPER_DRAFT_EN.md` 与中文结题报告
  `reports/v02/REPORT.zh-CN.md` 为结题时点版本；科研结论 INCONCLUSIVE，
  正式研究需新协议 + 新授权。
- 初版发布副本（含 runs/ 全量）已按总控裁定弃置重建；初版构建证据保留于
  审计目录 `p1_a/` 未删除，供对照。

## 9. 审核订正记录（R-01 / R-02）

成员 B 独立审核结论 RELEASE AUDIT PASS，同时开列 2 项 MINOR FAIL，均只涉及
本说明的文本与计数，不涉及任何代码/测试/数据决策。订正如下（不静默涂改，
原值留档于审计目录）：

- **R-01**：§5 排除表原含开发机用户目录个人路径字面量（全库唯一命中即该
  披露行自身）。已泛化为文本描述，不保留任何用户目录字面量；语境（被排除的
  2 个 docs 曾含开发机个人路径、故按默认排除规则剔除）保留。订正后全树
  复扫个人用户目录路径命中 **0**。
- **R-02a**：§5 排除文件总数原申报 **774**（= 490+272+3+7+2 分项相加），
  互斥实计 **770**（lock 3 与 backup 7 中有 4 项位于 runs/ 内，与目录计数
  重复相加）。已订正为 770 并附互斥口径说明；排除/保留决策本身经 B 重算
  确认正确，仅申报计数失实。
- **R-02b**：`D:\` 绝对路径统计原申报"40 处 / 20 文件"（载于审计证据
  `p1_a_rework/REWORK_REPORT.md`，且与其所引日志的 40 文件亦不自洽）。
  本次对发布副本重跑全树实测（成员 B 审核时点，本说明微修前）：**925 次 /
  39 文件**（成员 B 实测 926 次 / 39 文件，差 1 次、文件数一致；差异或源于
  扫描模式对非 `D:\` 形式 `D:` 串的处理，具体来源未能定位；以成员 A 实测
  为准申报）。微修后本说明自身新增引用，为避免自指漂移，§4 披露节采用
  **除本说明自身外的稳定口径：921 次 / 38 文件**（含自身合计的数字随本
  说明编辑增长，不固化；稳定口径以除自身外的 921 / 38 为准）。
- 连带动作：`PUBLICATION_MANIFEST.csv` 已随本说明字节变化重生成，
  `scripts/verify_publication.py` 复验 EXIT 0 PASS；除 `RELEASE_NOTES.md`
  外全部登记行哈希未变（证据见审计目录 `p1_a_rework/logs/`）。本次改动未
  触碰任何代码/测试/数据文件，未重跑测试套件。
