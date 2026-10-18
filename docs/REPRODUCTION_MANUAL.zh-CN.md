# SafeFlipLab — 复现手册（REPRODUCTION MANUAL）

**日期**：2026-10-15　│　适用于 V01 与 V02 的**探索性研究结题版本**
**目标**：让任何第三方**在不运行任何新仿真**的前提下，独立复现本项目的**全部已发布数字**，
并核对账本、哈希与结论。

> **重要前置**：真实仿真预算**已全部用满**（V01 24+240、V02 24+240）。
> 本手册的每一步**都不消耗仿真预算**（除注明「会拒绝」的步骤外）。
> **不要**尝试重跑 `smoke` / `pilot` / `formal`——它们会被账本或安全门拒绝，这是**正确行为**。

---

## 1. 环境

| 项 | 值 |
|---|---|
| 平台 | Windows（Git Bash 或 PowerShell 均可） |
| 项目根 | `D:\SafeFlipLab` |
| 虚拟环境 | `D:\SafeFlipLab\.venv`（Python 3.13） |
| 关键依赖 | `cornercaselab==0.3.0`（含 HighwayEnv 1.10.2、Gymnasium 1.2.2） |
| 解释器路径 | `<root>\.venv\Scripts\python.exe` |
| 网络 | **不需要**（除可选的文献/上游文档核验外） |

自检：
```powershell
cd D:\SafeFlipLab
.\.venv\Scripts\python.exe -c "import sys, cornercaselab; print(sys.version); print(cornercaselab.__file__)"
```
预期：Python 3.13.x；`cornercaselab` 位于 `.venv\Lib\site-packages\cornercaselab\`。

---

## 2. 一键复现（推荐顺序）

```powershell
cd D:\SafeFlipLab

# 1) V01 接口自检（零 episode）
.\.venv\Scripts\python.exe -m safefliplab doctor
#    预期：17/17 checks passed / VERDICT: GO

# 2) V02 接口自检（零 episode）
cd v02
..\.venv\Scripts\python.exe -m v02lab doctor
#    预期：7/7 checks passed / VERDICT: GO；并打印冻结协议 hash=d175ec90eecf4e80...
cd ..

# 3) 用账本 + 原始记录重新生成全部报告（幂等，零 episode）
cd v02
..\.venv\Scripts\python.exe -m v02lab report --phase smoke
..\.venv\Scripts\python.exe -m v02lab report --phase pilot
cd ..
.\.venv\Scripts\python.exe -m safefliplab report --phase smoke
.\.venv\Scripts\python.exe -m safefliplab report --phase pilot

# 4) 全部单元测试（V01 227 + V02 143，零 episode）
.\.venv\Scripts\python.exe -m unittest discover -s tests          # 预期 Ran 227 tests, OK
cd v02
..\.venv\Scripts\python.exe -m unittest discover -s tests          # 预期 Ran 143 tests, OK
cd ..

# 5) 全量独立复算（V01 + V02，不导入任何报告模块）
.\.venv\Scripts\python.exe scripts\independent_verify_all.py
#    预期：INDEPENDENT RECOMPUTATION: ALL CHECKS PASS（141 项断言）

# 5b) 账本 schema 指纹（零 episode；只读表头后写独立的指纹文件，不触碰账本）
cd v02
..\.venv\Scripts\python.exe -c "import sys;sys.path.insert(0,'.');from pathlib import Path;from v02lab.ledger21 import EpisodeLedger21;[EpisodeLedger21(Path(f'runs/{p}/episode_ledger.csv'),phase=p).verify_schema_fingerprint(f'runs/{p}/episode_ledger.schema.json') for p in ('smoke','pilot')];print('schema fingerprints verified')"
#    预期：schema fingerprints verified；表头 SHA-256 = 24eeb3915d91bcec...（与 manifest 的 header_sha256 一致）
cd ..

# 5c) F-06 取证（零 episode）
.\.venv\Scripts\python.exe scripts\runid_audit.py
#    预期：VERDICT: the `method` column is authoritative; the affected run_id strings are a cosmetic labelling defect (F-06).

# 6) 交付文件哈希与计数一致性（零 episode）
.\.venv\Scripts\python.exe scripts\build_final_manifest.py --check
#    预期：MANIFEST COUNT CHECK: PASS  (files=<N>, bytes=<B>, categories=15)
#    该命令会校验 docs/FINAL_DELIVERY_MANIFEST.md 中所有「N 个文件 / N 字节」声明
#    与分类表之和是否等于 docs/FINAL_ARTIFACT_HASHES.csv 的真实行数；不一致则 EXIT 1。

# 若项目文件集合有变化，重新生成清单（会改写 CSV、计数摘要与清单内的生成区块）
.\.venv\Scripts\python.exe scripts\build_final_manifest.py
```

> **关于文件计数**：清单里的文件数与字节数**全部由脚本生成**
> （区块标记 `BEGIN:GENERATED-COUNTS` / `END:GENERATED-COUNTS`）。
> 历史上它们曾是手工维护的文本，导致同一文档出现 **186 / 187 / 188 三个互相矛盾的总数**
> （外部审阅意见已指出）。现改为**单一生成来源 + `--check` 校验**，任何漂移都会被检出。
> **权威文件集合永远是 `docs/FINAL_ARTIFACT_HASHES.csv`（其行数即文件数）。**

**注意 1**：第 3 步会**重写** `reports/` 与 `v02/reports/` 下的报告文件（内容应**逐字节相同**，
除非模板变化）。若只想核对而不想改动文件，请先备份 `reports/` 与 `v02/reports/`。

**注意 2**：第 4 步的 V01 测试在 Windows 上因 `fsync` 与临时目录删除，墙钟约 **5–6 分钟**；
V02 约 **10 秒**。这是环境性耗时，与代码无关。

---

## 3. 逐项数字核对（**不导入报告模块**）

`scripts/independent_verify_all.py`（规范位置；该脚本不导入任何报告模块）会在一个进程内重算并逐项打印
`recomputed` 与 `published` 的对照。其覆盖范围：

### 3.1 V01
- smoke / pilot 的 `episodes_launched / completed / errored / interrupted`；
- `complete_quartets` 与 `replay_quartets`；
- 4 个 `(method, stream)` 组合的 `n_quartets`、`mean_delta_both`、`reverse_pairs`、`rescue_pairs`
  与四条件碰撞计数；
- **12 个探索性 ΔTTC 裕度**（4 组 × `gap/speed/both`）。

### 3.2 V02
- smoke / pilot 的 launch / outcome / 孤儿行 / `budget_scope`；
- **两个必须区分的定义**：`n_primary_quartets`（四条件均已计费）与
  `n_usable_quartets`（四条件均有可恢复值）——smoke 为 **6 / 5**，pilot 为 **54 / 54**；
- **M1 四对比**的点估计与 95% 锚级 bootstrap 区间（B=10000、α=0.05、seed=20261015）；
- **M2 四对比**与四条件均值；
- **辅助审计**的 `n_nominees` / `n_reversal` / `precision@k`，以及**重复模拟检测**
  （应发现 6 个名义 quartet 只有 **5 次不同模拟**，重复对象为 `v02-anchor-0012`，`sim_seed=484391145`）
  与**留一敏感性**（WideExplore `1/3→0/2`、VerifyFirst `3/3→2/2`）；
- **样本量推导**：`z(1-α/8)=2.497705`、`z(0.80)=0.841621`、锚级 SD、
  `n=18` 最灵敏 MDE `= 0.0837 s`、MDE 网格（235/2820 与 59/708）。

### 3.3 手动抽查（可选）

```powershell
cd D:\SafeFlipLab
# 账本行数与阶段
.\.venv\Scripts\python.exe -c "import csv,collections;rows=[r for r in csv.DictReader(open('runs/episode_ledger.csv',newline='',encoding='utf-8')) if r.get('row_type')];print(len(rows),collections.Counter(r['phase'] for r in rows))"
# 预期：528 Counter({'pilot': 480, 'smoke': 48})

cd v02
# V02 pilot 分解
..\.venv\Scripts\python.exe -c "import csv,collections;rows=[r for r in csv.DictReader(open('runs/pilot/episode_ledger.csv',newline='',encoding='utf-8')) if r['row_type']=='launch'];print(len(rows),collections.Counter(r['stream'] for r in rows),collections.Counter(r['method'] for r in rows))"
# 预期：240 Counter({'discovery': 216, 'audit': 24}) Counter({'Shared': 216, 'WideExplore': 12, 'VerifyFirst': 12})
```

---

## 4. 安全门（**预期会拒绝**，不是故障）

| 命令 | 预期 |
|---|---|
| `.\.venv\Scripts\python.exe -m safefliplab formal --confirm --max-episodes 12800` | **EXIT 2**，打印 `REFUSED: formal driver ... NOT executed by this build` |
| `cd v02 && ..\.venv\Scripts\python.exe -m v02lab smoke --max-episodes 24` | **EXIT 2**，`REFUSED: ... budget already exhausted` |
| `cd v02 && ..\.venv\Scripts\python.exe -m v02lab pilot --max-episodes 240` | **EXIT 2**，同上 |
| `cd v02 && ..\.venv\Scripts\python.exe -m v02lab --help` | 子命令仅 `{doctor,smoke,pilot,report}` —— **无 formal 入口** |

---

## 5. 哈希核对（防篡改）

两种**不可混用**的口径：

```powershell
cd D:\SafeFlipLab
# (a) 原始字节哈希：对文件字节直接取 SHA-256（与 docs/FINAL_ARTIFACT_HASHES.csv 一致）
.\.venv\Scripts\python.exe -c "import hashlib;print(hashlib.sha256(open(r'v02\configs\v02_frozen_v1.json','rb').read()).hexdigest())"
#     预期：52fc80aaa4936661cce496278e29f847bb4b1be808f1a0af3c237d11f670b24d

# (b) 规范 JSON 哈希：解析后按 sort_keys + 紧凑分隔符重新序列化
.\.venv\Scripts\python.exe -c "import hashlib,json;d=json.load(open(r'v02\configs\v02_frozen_v1.json',encoding='utf-8'));print(hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest())"
#     预期：d175ec90eecf4e8080d33cc43aab1e2f1c469b73588c6a682bfdfd30c8dd9925  (= 协议指纹)
```

> **为什么有两个值**：`52fc80aa…` 是**磁盘文件**的哈希（会随空白/换行变化）；
> `d175ec90…` 是**协议语义内容**的哈希（`FrozenProtocol.protocol_hash`、doctor 与
> `v02/runs/manifest_*.json` 使用的就是它）。**两个都对**，但**含义不同**。

---

## 6. 从零重建（在**不消耗预算**的前提下可以做到什么）

| 可以完整重建 | 不可以重建 |
|---|---|
| 全部源码、配置、测试 | **真实 episode 的仿真结果**（预算已用满，无法重跑） |
| 全部**派生**报告 / CSV / JSON / 图（由账本 + 原始记录重算） | V01 的 12,800 次 formal（从未授权执行） |
| 全部单元测试与 doctor | 任何被修复缺陷之前的**旧行为**（如 D43 的通配读取） |

**因此**：本项目的"可复现性"指的是
**「给定已归档的账本与原始记录，全部数字可被独立重算」**，
而**不是**「可重新生成同一批真实 episode」。

---

## 7. 常见问题

| 现象 | 原因 / 处理 |
|---|---|
| `report --phase smoke` 输出条件均值与旧文档不同 | 若旧文档早于 **D43** 修复，那是**旧的错误值**；以当前输出为准（见 `docs/AUTONOMOUS_DECISIONS.md` D43） |
| 单元测试很慢（V01 约 5–6 分钟） | Windows 上 `fsync` + 临时目录删除的环境性耗时 |
| `smoke`/`pilot` 返回 2 并说 `exhausted` | **正确行为**：预算用满，账本拒绝 |
| `independent_verify_all.py` 报 `MISMATCH` | 说明**派生阅读逻辑**与已归档证据不一致——**这是一个真实发现**，请记录并检查，不要忽略 |
| doctor 打印的 hash 与文件字节哈希不同 | 见 §5：两个口径，均正确 |

---

## 8. 复现边界（如实声明）

- **未运行**任何新增真实仿真；**未**启动 formal；**未**发布 GitHub；**未**投稿；**未**创建 V03。
- 上游 CornerCaseLab 的核验为**其公开协议文档的只读引用**，
  **未**运行、未获取、未比较其 60,000 episode 正式数据，**未**逐行比对源码。
- 文献检索**非穷尽**；未检索到 ≠ 不存在。
- 本手册**不构成**任何运行的授权。
