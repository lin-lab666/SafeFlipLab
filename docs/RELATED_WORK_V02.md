# RELATED_WORK_V02 — V02 相关文献核验（增补）

> 本文件是 `docs/RELATED_WORK.md`（V01，6 项）的**增补**，只收录与 V02 直接相关、
> 且**已在线核验**来源信息（期刊/卷/页/DOI/链接）的条目。
> 核验方式：联网检索并对照出版方/索引页；**未逐字阅读全文**的条目已显式标注。
> 核验日期：2026-10-15。

---

## 1. 已核验条目

### R-01｜Li et al. (2024) — 1D 安全替代指标的精度上限

- **书目**：Li, S., Anis, M., Lord, D., Zhang, H., Zhou, Y., Ye, X. (2024).
  *Beyond 1D and oversimplified kinematics: A generic analytical framework for surrogate
  safety measures.* **Accident Analysis and Prevention**, 204, 107649.
- **DOI**：`10.1016/j.aap.2024.107649`；预印本 `arXiv:2312.07019`
- **链接**：https://doi.org/10.1016/j.aap.2024.107649 ；https://arxiv.org/abs/2312.07019
- **研究任务**：提出通用的安全替代指标（SSM）解析框架，覆盖 1D 到多维高保真车辆动力学，
  给出「碰撞判据 + 剩余碰撞时间」的通用定义。
- **与本项目的关系**：
  - **直接支持 V02 的核心局限声明**：本项目主终点（最小前向 TTC）**正是 1D、常速假设**的 SSM；
    该文报告 1D SSM 相对 3D SSM 在 TTC > 1.5 s 时偏差可达 **约 300%**、在 TTC < 1.5 s 时约 **20%**。
  - **区别**：该文关注 SSM **定义与计算保真度**；本项目关注**在同一 1D 指标下的四条件因果对比**，
    不主张指标本身的保真度。
- **限制**：本项目**未**采用其多维框架，也不声称 TTC 是碰撞风险的充分度量。
- **阅读状态**：**摘要 + 索引页已核验**；全文未获取（付费墙）。

### R-02｜Do, Saunier & Miranda-Moreno (2025) — CAV 车-车跟随场景下传统指标的不足

- **书目**：Do, W., Saunier, N., Miranda-Moreno, L. (2025).
  *Evaluation of Conventional Surrogate Indicators of Safety for Connected and Automated
  Vehicles in Car Following at Signalized Intersections.*
  **Transportation Research Record**, 2679(2), 1118–1133.
- **DOI**：`10.1177/03611981241265849`
- **链接**：https://doi.org/10.1177/03611981241265849
- **研究任务**：在信号交叉口车-车跟随场景中评估 8 种安全替代指标（TTC、PET、TET、TIT、
  DRAC、CPI、RCRI、PICUD）对 CAV 的适用性。
- **与本项目的关系**：
  - **直接支持 V02 的适用性边界**：该文的结论之一是 **TTC / PET / DRAC 在连续车辆速度相近时
    不足以刻画安全含义**（CAV 小间距跟驰）——这与本项目「规则控制器维持间距、
    碰撞事件近乎为零、TTC 由几何决定」的诊断一致。
  - **区别**：该文用微观仿真评估**指标本身**；本项目用四条件析因设计评估**干预效应**。
- **限制**：该文场景为信号交叉口，本项目为高速汇入；结论只作方向性支持。
- **阅读状态**：**摘要 + TRB 索引页已核验**；全文未获取。

### R-03（沿用 V01，未重复核验）
`docs/RELATED_WORK.md` 中 V01 已核验的 6 项（counterfactual safety margin / planner
avoidability / metamorphic testing ×2 / simulation robustness ×2 / RSS ×2）继续有效；
本文件不重复列出，也不覆盖。**V01 中标注「未逐字阅读」的条目仍然如此。**

---

## 2. 未核验 / 待补条目（明确标注）

| 主题 | 状态 | 说明 |
|---|---|---|
| 高速汇入场景的「汇入博弈」安全分析 | **NOT VERIFIED** | 本轮未检索到可直接引用且已核验的具体条目；不编造 |
| 反事实「更安全参数反而更危险」的既有实证 | **NOT VERIFIED** | 未能定位到与本项目同构（2² 析因 + 锚级聚类）的既有文献；这也是 V02 潜在新增点的**风险**：可能已有相关工作 |
| CornerCaseLab v0.3.0 的评估协议文档 | **PARTIAL** | 仅通过已安装包 docstring 与 V01 记录间接了解；**未**取得其公开评估文档原文，因此 `docs/V02_RESEARCH_PROPOSAL.md` §12 的重叠判定需以对方文档为准复核 |

---

## 3. 对本项目结论的影响

1. **支持**：把 min-TTC 明确定位为**有限保真度代理量**，而非碰撞风险（R-01、R-02）。
2. **支持**：当连续车辆速度相近 / 控制器维持间距时，二元与 TTC 类指标都可能失去分辨力（R-02）——
   这解释了 V01 的零碰撞与 V02 需要域收窄的原因。
3. **不支持**：任何「本项目首次发现安全反转」的声明 —— 文献检索未穷尽，
   且 V02 无确证性检验（见 `docs/AUTONOMOUS_DECISIONS.md` D35）。

---

## 4. 新增性核验（P4，2026-10-15）— 候选新增点是否已被覆盖

检索目标：本项目三条**候选新增点**（① 四条件 2² 析因反事实干预；② 把"安全反转"作为显式估计量；
③ 尺度显式的非可加交互）是否已有公开文献覆盖。**该检索为非穷尽。**

### 4.1 检索到的、构成"先例"的方向（削弱新颖性）

| 方向 | 证据 | 对 V02 的影响 |
|---|---|---|
| **反事实仿真用于安全效益估计** | Bärgman 等提出的反事实仿真框架；Chalmers 学位论文（Paper III 用反事实仿真估计安全效益，并指出结果**强依赖驾驶员模型选择**）；工作区车载报警的安全效益用**反事实蒙特卡洛仿真**估计（*Accident Analysis and Prevention*，doi:10.1016/j.aap.2025.100…，检索页 S0001457525001009） | "反事实"本身**不是**新颖点 |
| **轨迹级反事实推理 + 因子分析** | "Evaluating active driver intervention strategies in sequential conflict scenarios: a counterfactual reasoning-based framework"（*Accident Analysis and Prevention*，S000145752600165X）——明确提出用**反事实推理**估计干预净效益，并用**探索性因子分析**建立机制空间 | 与 ①③ **方向邻近**；必须显式承认 |
| **驾驶仿真中的析因设计** | 行人过街安全措施的多因子实验（PubMed 26253423）；Chalmers 论文中用于筛选主导因子的**分式析因设计** | "析因设计"**不是**新颖点 |
| **不报告 p 值、用 bootstrap CI** | CornerCaseLab v0.3（见 `docs/CORNERCASELAB_OVERLAP_VERIFIED.md`） | 统计姿态属**趋同**，不是新颖点 |

### 4.2 检索**未**发现被明确覆盖的部分

- 未检索到把 **"直觉上更安全的参数改动反而降低连续安全裕度"（安全反转）** 作为**显式估计量**
  并配合 **2² 锚内析因 + 锚级聚类**推断的公开工作；
- 未检索到在**同一冻结规则控制器**下、对**自车场景参数**做**尺度显式非可加交互**（`I_lin`/`I_log`）
  估计的公开工作。

### 4.3 结论（必须写入任何稿件）

> 本项目的**组件**均非新颖（反事实仿真、析因设计、安全替代指标、bootstrap 区间、不报 p 值）。
> 可能的**组合性**新增点仅为三条，且**检索非穷尽**，**不得**使用"首次""独有"等表述。
> 任何稿件必须同时引用并承认上述先例。

### 4.4 未核验项（明确标注）

| 主题 | 状态 |
|---|---|
| 上述文献的**全文** | **NOT VERIFIED**（仅核验摘要/检索页；`S000145752600165X` 与 `S0001457525001009` 的完整 DOI 未在检索页给出，故本文**不写出推测的 DOI**） |
| 是否存在未检索到的同构工作 | **UNKNOWN**（检索非穷尽） |
| CornerCaseLab 的 `EVALUATION_PROTOCOL_V03.md` / `SCORING_PROTOCOL_V03.md` 全文逐条比对 | **未完成**（见 `CORNERCASELAB_OVERLAP_VERIFIED.md` §3.5） |
