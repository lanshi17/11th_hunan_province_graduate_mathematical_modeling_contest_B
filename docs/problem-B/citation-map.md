# 正文真引文献对照（15–22 篇，禁止堆 52 篇目录）

著录按 GB/T 7714-2015，BibTeX 键见 `references/problem-B/refs.bib`。公式用本文符号，不要摘录综述原文。下列“落点”是建议首次引用的位置。

---

## 问题一（5 篇）

| 键 | 落点 | 本文中的对应 |
|----|------|----------------|
| `Crowe1996data` | 数据调和目标函数 | \(\min\sum_k((x_k-\hat x_k)/\sigma_k)^2\)，守恒约束下 WLS |
| `Narasimhan1999data` | 粗差与冗余 | 异常识别、可观测性与标准化残差 |
| `Schweppe1970power` | 方法定位句 | “面向能量平衡的广义状态估计” |
| `Abur2004power` | \(\lvert z\rvert>3\) 判据 | 标准化残差最大检验（LNR） |
| `deChalendar2021physics` | 引言/相关工作一句 | 电网多源电量守恒调和并追踪排放的同构实证 |

可选第 6 篇（页数宽裕再引）：`Cheng2023survey`（多源量测状态估计综述，只在引言用一句，不展开）。

## 问题二（6 篇）

| 键 | 落点 | 本文中的对应 |
|----|------|----------------|
| `Bialek1996tracing` | 比例共享 | 节点入流按同一碳势混合 |
| `Kang2012carbon` 或 `Kang2015carbon` | 节点碳势方程 | \((\mathrm{diag}(Q)-C)\boldsymbol\rho=\boldsymbol b\)；**二者只引一篇即可**，建议 `Kang2015carbon` |
| `Peters2008production` | 生产责任 \(P^+\) | 发电地（含省外输入接入）口径 |
| `Davis2010consumption` | 消费责任 \(C^+\) | 用电地全口径 |
| `Gallego2005consistent` | \(\lambda\) 共担 | \(R_i=\lambda P^+_i+(1-\lambda)C^+_i\) |
| `Qin2020cooperative` | Shapley | 通道碳转移博弈 \(v(S)\) 的公理化；与 \(\lambda=0.5\) 数值重合在正文点明 |

`Lenzen2007shared` 与 Gallego 同主题，**不要两篇都展开**，正文用 Gallego、参考文献可并列 Lenzen。`Kirschen1997contributions` 可不引（与 Bialek 功能重复）。

## 问题三（4 篇）

| 键 | 落点 | 本文中的对应 |
|----|------|----------------|
| `Raupach2014sharing` | 惯性份额 | 祖父条款 / 现状排放份额 |
| `Zhou2016carbon` | 公平份额 | 区域碳预算分配综述定位 |
| `Wang2013regional` | 省区配额分解 | 需求份额作为公平项 |
| `Koltsaklis2018generation` | 五年 MILP | 投资—运行耦合的发电扩张规划范式 |

`Cui2021allocation`、`Bai2024allocation` 不进正文，避免“分配文献堆砌”。

## 问题四（5 篇）

| 键 | 落点 | 本文中的对应 |
|----|------|----------------|
| `Bertsimas2004price` | 预算不确定集、POR 曲线 | \(\Gamma_t\)、对等式、图7 |
| `BenTal2004adjustable` | 两阶段可调鲁棒 | 2026–2027 此地决策 / 2028–2030 观望 |
| `Zeng2013solving` | C&CG | 顶点加列，两轮 5251.5→6522.4 |
| `Silvente2015rolling` | 滚动时域 | 已观测年用真 \(\xi\)，未来年 \(\Gamma\)-鲁棒 |
| `BenTal1998robust` | 可删 | 仅当需要“鲁棒凸优化”一句定位；优先保上面 4 篇 |

## 问题五 / 讨论（1–2 篇）

| 键 | 落点 | 本文中的对应 |
|----|------|----------------|
| `Feng2013outsourcing` | 责任格局讨论 | A4→A3 碳转出与省内“碳外包” |
| `Chen2024carbon` | 决策建议一句 | 碳感知调度，不必展开模型 |

---

## 建议正文引用清单（20 篇）

1. Crowe1996data  
2. Narasimhan1999data  
3. Schweppe1970power  
4. Abur2004power  
5. deChalendar2021physics  
6. Bialek1996tracing  
7. Kang2015carbon  
8. Peters2008production  
9. Davis2010consumption  
10. Gallego2005consistent  
11. Lenzen2007shared（与 10 并列，不单独成段）  
12. Qin2020cooperative  
13. Raupach2014sharing  
14. Zhou2016carbon  
15. Wang2013regional  
16. Koltsaklis2018generation  
17. Bertsimas2004price  
18. BenTal2004adjustable  
19. Zeng2013solving  
20. Silvente2015rolling  

外加讨论用 `Feng2013outsourcing` 则为 21 篇。其余 31 篇**不要出现在参考文献表**。

---

## 查重注意（公式用自己的符号）

- 不要出现 “data reconciliation is the process of adjusting…” 类综述句。  
- 碳势方程写成 \((\mathrm{diag}(\boldsymbol Q)-\boldsymbol C)\boldsymbol\rho=\boldsymbol b\)，不要照抄 Kang 文中符号 \(\boldsymbol R,\boldsymbol P_G\)。  
- 预算集写成 \(\{\boldsymbol z: 0\le z_j\le 1,\ \sum_j z_j\le \Gamma_t\}\)，不要大段翻译 Bertsimas–Sim 原文。  
- C&CG 写成“主问题加列最坏顶点、子问题按当前 \(W_{j,y}\) 贪心取满 \(\Gamma_t\)”，不要贴 Zeng–Zhao 伪代码。
