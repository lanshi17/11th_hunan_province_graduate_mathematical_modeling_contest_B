# 图表题（论文直接粘贴稿）

**状态（2026-08-20）：** 编号与图题已写入 `paper/main.tex` 并编入 `paper/main.pdf`（16 页，版式对齐官方论文格式规范；楷体 11pt 图题表题）。正文实际用图 10 张、表 7 张，顺序为：残差热力图、E05 线损对照、逐月碳势、碳流网络、四种责任、无项目轨迹、开工安排、压力测试、POR 曲线、三方案对照。下面“建议 8 图”是精简备选；与 PDF 冲突时以 PDF 为准。

格式规范：图注、表头用**楷体 11 号**；图题在图下方，表题在表上方。文件路径相对于 `src/outputs/`。

---

## 正文建议图（8 张）

**图1 校正前各区域—月份能量平衡标准化残差**  
文件：`q1/fig_q1_raw_residual_heatmap.png`  
注：颜色为 \(z_{i,t}=r_{i,t}/\sigma_{i,t}\)；\(|z|>3\) 对应附件 1A 中 A2 九月等粗差。

**图2 2025 年区域间电力碳流与净责任格局**  
文件：`deepen/fig_q2_carbon_flow_network.png`  
注：箭头宽度正比于到达电量携带的碳量 \(F_{j\to i}\)（ktCO2）；节点颜色为消费责任 \(C^+_i\) 减生产责任 \(P^+_i\)（红=净转入）。主路径为 A4→A3（4374 kt）。

**图3 四种口径下的区域碳排放责任（2025）**  
文件：`deepen/fig_q2_responsibility_shapley.png`  
注：\(P^+\) 为扩展生产责任，\(C^+\) 为全口径消费责任，\(\lambda=0.5\) 为线性共担；Shapley 值为通道碳转移博弈的精确枚举，与 \(\lambda=0.5\) 在两位小数上一致。

**图4 问题三无项目、贪心与 MILP 的消费侧碳轨迹**  
文件：`deepen/fig_q3_no_project.png`  
注：2026 年三类方案重合（项目尚未投运）；无项目自 2027 年起越限，累计 567 kt；贪心与 MILP 均贴着 2028—2030 上限运行。

**图5 五年项目开工规模安排**  
文件：`q3/fig_q3_schedule.png`  
注：主方案入选 7 个项目、总投资 985.5 百万元；通道升级 P33—P35 未入选（官方碳核算不依赖潮流）。

**图6 问题三方案在送端碳因子情景下的压力测试**  
文件：`q4/fig_q4_stress.png`  
注：S3 情景 2028/2029/2030 年越限分别为 195.4、338.5、454.5 kt。

**图7 鲁棒性的代价（\(\Gamma\) 缩放）**  
文件：`q4/fig_q4_por.png`  
注：\(\tau=0\) 投资 985.5 百万元、最坏总越限 1125.46 kt；\(\tau=1\) 投资 4848.8 百万元、残余 18.17 kt。

**图8 确定性、静态鲁棒与稳健滚动三方案对照**  
文件：`deepen/fig_q4_three_schemes.png`  
注：静态鲁棒与稳健滚动在 S3 路径下均可零越限；二者实物总投资同为 4848.8 百万元（滚动第一阶段已按两阶段鲁棒锁定）。确定性方案投资低但 2030 年越限 454.5 kt。

---

## 附录备选图

| 建议编号 | 图题 | 文件 |
|----------|------|------|
| 附图1 | 标准化调整量绝对值前 20 的观测 | `q1/fig_q1_adjust_top20.png` |
| 附图2 | 通道工程线损率与调和估计比较 | `q1/fig_q1_eta_compare.png` |
| 附图3 | 各区域逐月节点碳势（送端承担口径） | `q2/fig_q2_rho_monthly.png` |
| 附图4 | 各区域终端用电的电源来源分解（2025） | `q2/fig_q2_origin_mix.png` |
| 附图5 | 线损碳排口径差：受端承担相对送端承担 | `q2/fig_q2_loss_convention_diff.png` |
| 附图6 | 候选项目单位减排成本排序（前 12） | `q3/fig_q3_merit_order.png` |
| 附图7 | 五种口径责任（仅 \(P^+/C^+/\lambda\)，无 Shapley） | `q2/fig_q2_responsibility.png` |
| 附图8 | 五年方案消费侧碳排放轨迹（无无项目对照） | `q3/fig_q3_carbon_trajectory.png` |

正文若已用图4、图3，则附图7、附图8不必重复出现。

---

## 正文建议表（6 张）

**表1 建模参数及其敏感性结论（节选）**  
数据：`deepen/q1_param_sensitivity.csv`，`deepen/q3_param_sensitivity.csv`  
表题：区内损耗先验、量测 \(\sigma\)、区域预算罚、缺供罚与惯性权重的敏感性

建议表内只留主结论行，完整网格放附录。

**表2 2025 年区域碳排放责任与 Shapley 共担**  
数据：`deepen/q2_responsibility_shapley.csv`  
表题：生产、消费、\(\lambda\) 共担与 Shapley 责任（ktCO2）

**表3 无项目、贪心可行解与 MILP 主方案比较**  
数据：`deepen/q3_baselines.csv`，`deepen/q3_no_project_vs_milp.csv`  
表题：问题三三类方案的投资、越限与方案 Jaccard 相似度

**表4 投资折现率 0 与 8% 对照**  
数据：`deepen/q3_param_sensitivity.csv` 中“折现率”两行  
表题：综合成本对折现率的敏感性

**表5 \(\Gamma\) 缩放下的投资与最坏越限**  
数据：`deepen/q4_gamma_sensitivity.csv`  
表题：预算不确定集半径 \(\tau\) 的 price-of-robustness

**表6 确定性 / 静态鲁棒 / 稳健滚动对照**  
数据：`deepen/q4_three_schemes.csv`  
表题：三种决策机制在 S3 路径下的投资与越限

---

## 附录备选表

| 建议编号 | 表题 | 文件 |
|----------|------|------|
| 附表1 | 异常与口径不一致清单 | `q1/q1_anomalies.csv` |
| 附表2 | 通道碳转移矩阵 \(F_{j\to i}\) | `deepen/q2_carbon_transfer.csv` |
| 附表3 | \(\lambda\) 共担相对 Shapley 的偏差 | `deepen/q2_lambda_vs_shapley.csv` |
| 附表4 | 贪心开工安排 | `deepen/q3_greedy_schedule.csv` |
| 附表5 | 碳上限影子价格 | `q3/q3_shadow_prices.csv` |
| 附表6 | 投资上限×碳上限网格（Jaccard） | `q3/q3_sensitivity.csv` |
| 附表7 | \(S_{ij}\) 冻结假设的传导偏差 | `deepen/q4_sij_limitation.csv` |
| 附表8 | 滚动调控逐年累计投资（S0/S1/S3） | `deepen/q4_rolling_with_investment.csv` |
