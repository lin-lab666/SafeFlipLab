# Publication scope: v1.0 research package and v1.1 engineering update

- 日期：2026-10-18
- 适用对象：本仓库（`https://github.com/lin-lab666/SafeFlipLab`，PRIVATE）
- 一句话：**v1.0 是冻结的研究包；v1.1 只做工程化完善，科研数据与结果产物
  不变。**

---

## 1. v1.0 — 研究包（字节级冻结）

| 项 | 值 |
|---|---|
| 提交 | `0f63b73`（初始发布）→ `baee8becb796b0fe4f067a0c4cb5fbac237c58b9`（G-ATTR 修复，v1.0 终态） |
| 文件数 | 202（磁盘） = 200（`PUBLICATION_MANIFEST.csv` 登记） + 清单自身 + 校验器 |
| 清单字节 | 3,111,181 |
| 内容 | 源码（`safefliplab/`、`v02/v02lab/`）、测试、配置、结果汇总（`reports/`、`v02/reports/`）、结题文档（`docs/`） |
| 不包含 | 原始 episode 数据与账本（`runs/`、`v02/runs/`，共 762 文件） |

**冻结含义**：`PUBLICATION_MANIFEST.csv` 的**字节永不改写**。v1.0 中每个
登记文件的 SHA-256 是该时点的权威记录；对应关系亦见
`docs/FINAL_ARTIFACT_HASHES.csv`（原项目口径，含 `runs/` 的 201 文件全量，
两者独立记录、互不覆盖）。

## 2. v1.1 — 工程化更新（当前分支 `engineering/open-source-readiness`）

v1.1 **只包含**以下三类变化，**不触碰科研数据与结果产物**：

1. **缺陷修复**（GH-2）：
   - `safefliplab/experiments.py`：`formal` 的拒绝路径提前到**任何文件系统
     副作用之前**（此前会先创建 `runs/` 与空账本，导致测试重复运行失败）；
   - `tests/test_report_cli.py`：CLI 正式门测试改用 mock，不再触发真实调度器；
   - 新增 `tests/test_formal_no_side_effects.py`（零副作用回归测试）。
2. **元数据与文档**：
   - `CITATION.cff`：`repository-code` 指向已发布仓库；
   - `pyproject.toml`：`[project.urls]`、`classifiers`、`keywords`、
     `test` extra、`setuptools>=77`（与 PEP 639 `license = "Apache-2.0"` 一致）；
   - `requirements.txt`：声明与 `sim` extra 的对齐关系；
   - `README.md` / `README.zh-CN.md`：可执行的 V02 测试命令、预期输出、
     测试产物说明；
   - `.gitignore`：补充构建/覆盖率产物；
   - 新增本文档（以及后续 GH-3 的安装/快速开始/架构/示例/贡献/安全/测试/
     数据可用性/变更日志文档与 CI 配置；OS-3 的展示资源
     `docs/assets/architecture.svg` 与 `docs/assets/offline-demo-output.txt`）。
3. **工具健壮性**：
   - `scripts/verify_publication.py`：两级范围报告（v1.0 字节校验 + v1.1
     白名单）；
   - `scripts/build_final_manifest.py`、`scripts/independent_verify_all.py`：
     `ROOT` 默认取仓库根，可用环境变量 `SAFEFLIPLAB_ROOT` 覆盖（不再硬编码
     `D:\SafeFlipLab`）。

**明确不变**：`configs/**`、`reports/**`、`v02/v02lab/**`、`v02/tests/**`、
`docs/**` 的既有文件、以及全部历史实验数值——v1.1 未重跑任何仿真、未修改
任何科研数据。

## 3. 验证方式

```bash
python scripts/verify_publication.py
```

输出分两层（PASS 时 EXIT 0）：

- **v1.0 研究包**：manifest 内除 `V11_UPDATED` 白名单外的所有文件必须
  逐字节匹配（存在 + 字节数 + SHA-256）；任一不符即 FAIL。
- **v1.1 工程范围**：磁盘上多出的文件必须匹配 `POST_V1_PATTERNS`（新增
  文档、`.github/**`、`examples/**`、新回归测试）；否则按 EXTRA 判 FAIL。

`V11_UPDATED` 与 `POST_V1_PATTERNS` 的完整清单及逐项理由**写在
`scripts/verify_publication.py` 顶部常量中**（代码即声明，避免文档与行为
漂移）。

### 与 `docs/FINAL_ARTIFACT_HASHES.csv` 的关系

| 文件 | 口径 | 用途 |
|---|---|---|
| `PUBLICATION_MANIFEST.csv` | 发布包口径（200 行；不含 `runs/`；v1.0 冻结字节） | 克隆/发布的完整性校验（本仓库 `verify_publication.py` 使用） |
| `docs/FINAL_ARTIFACT_HASHES.csv` | 原项目口径（含 `runs/` 的完整集合；结题时点生成） | 原项目结题证据；`scripts/build_final_manifest.py --check` 使用 |

两者**独立记录、互不覆盖**：前者回答"这个仓库快照是否与发布时一致"，
后者回答"原项目结题时点的全量文件哈希是什么"。v1.1 的更新只影响前者解释
（通过白名单），后者的历史记录保持原样。

## 4. 版本演进原则

- **科研结论不因工程更新而改变**：v1.1 不新增主张、不修改任何统计量或
  区间；`INCONCLUSIVE` 定位、X1–X17 禁止表述、G-1～G-10 授权边界全部沿用。
- **清单冻结**：如需再生成 manifest（例如未来的 v1.2），应发布新的清单文件
  并保留 v1.0 原件，而不是覆盖本文件。
- **可追溯**：每一次工程更新的范围由 `verify_publication.py` 的白名单常量
  与 git 历史共同界定。

## 5. 历史审计文档中的内部引用（P2-09）

`docs/` 中的结题文档（如 `FINAL_CLOSEOUT_2026-10-17.md`、
`AUTONOMOUS_PROGRESS.md`、`FINAL_DELIVERY.md`）含有对**内部审计工作目录**的
引用（例如 `D:\SafeFlipLab_AUDIT_2026-10-17\...`、
`D:\SafeFlipLab_RELEASE_AUDIT_2026-10-17\...`、`round1/logs/...`、
`p1_a_rework/...`）。这些是**内部审计留痕**（"当时用什么证据、在哪个目录
核对过"），**不构成面向外部读者的操作指引**——外部读者没有、也不需要这些
目录。

处置：**保持 `docs/` 字节不变**（v1.0 研究包冻结，改写会破坏 manifest 与
审计链），并在本文档与 `README.md` 的文档索引中说明其性质：读到这些路径时，
应理解为"项目内部审计时点记录"，而非可复现步骤。对外复现以
`QUICKSTART.md` / `TESTING.md` 与 `scripts/verify_publication.py` 为准。
