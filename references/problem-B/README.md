# B 题参考文献

条目均经 OpenAlex 解析 DOI，并用 Crossref / doi.org 拉取 BibTeX，避免虚构文献。引用次数为 OpenAlex 统计，随时间变化。

- 经典（2022 年及以前）：**35** 篇（含 2026-08-20 增补的 12 篇方法论奠基文献与 8 篇 SerpApi 补检文献）
- 近三年（2024–2025）：**16** 篇，另含 1 篇 2023 年多源量测状态估计综述
- 合计：**52** 篇
- BibTeX：[`refs.bib`](refs.bib)

## 与赛题子问题的对应

| 子问题 | 建议精读（BibTeX 键） |
|--------|------------------------|
| 问题一 多源数据校正、缺失与平衡 | `Crowe1996data`, `Narasimhan1999data`, `Schweppe1970power`, `Abur2004power`, `deChalendar2021physics`, `deChalendar2019tracking`, `Cheng2023survey`, `Soroudi2013decision` |
| 问题二 碳流追踪与发电地/用电地责任 | `Bialek1996tracing`, `Kirschen1997contributions`, `Kang2012carbon`, `Kang2015carbon`, `Peters2008production`, `Davis2010consumption`, `Lenzen2007shared`, `Gallego2005consistent`, `Qin2020cooperative`, `Zhou2019cooperative`, `deChalendar2019tracking`, `Chen2024towards`, `Hu2025study` |
| 问题三 碳预算与五年项目组合 | `Raupach2014sharing`, `Zhou2016carbon`, `Wang2013regional`, `Cui2021allocation`, `Bai2024allocation`, `Koltsaklis2018generation`, `Zhang2024two`, `Feng2013outsourcing` |
| 问题四 送端碳因子不确定与鲁棒调控 | `Bertsimas2004price`, `BenTal1998robust`, `BenTal2004adjustable`, `Bertsimas2013adaptive`, `Zeng2013solving`, `Li2016adaptive`, `Silvente2015rolling`, `Ju2024data`, `Shen2024two`, `Sun2024modeling` |
| 问题五 决策咨询（调度/责任/规划） | `Chen2024carbon`, `Wang2024trade`, `Ling2024comprehensive` |

方法与文献的逐条对应关系见 [`../../docs/problem-B/plan.md`](../../docs/problem-B/plan.md)。

## 经典文献

### 电力潮流追踪

### 1. Tracing the flow of electricity

- **标记：** `经典` · 电力潮流追踪
- **作者：** Janusz Białek
- **年份 / 期刊：** 1996 · IEE Proceedings - Generation Transmission and Distribution
- **DOI：** [10.1049/ip-gtd:19960461](https://doi.org/10.1049/ip-gtd:19960461)
- **OpenAlex 引用次数：** 823
- **BibTeX 键：** `Bialek1996tracing`
- **与赛题关系：** 电力潮流追踪奠基，问题二碳流追踪的网络分配思想来源。
- **GB/T 7714：** Janusz Białek. Tracing the flow of electricity[J]. IEE Proceedings - Generation Transmission and Distribution, 1996. DOI: 10.1049/ip-gtd:19960461.

### 2. Contributions of individual generators to loads and flows

- **标记：** `经典` · 电力潮流追踪
- **作者：** Daniel S. Kirschen, R. S. Allan, Goran Štrbac
- **年份 / 期刊：** 1997 · IEEE Transactions on Power Systems
- **DOI：** [10.1109/59.574923](https://doi.org/10.1109/59.574923)
- **OpenAlex 引用次数：** 643
- **BibTeX 键：** `Kirschen1997contributions}`
- **与赛题关系：** 发电机对负荷与潮流的贡献分解，与 Bialek 并列的追踪经典。
- **GB/T 7714：** Daniel S. Kirschen, R. S. Allan, Goran Štrbac. Contributions of individual generators to loads and flows[J]. IEEE Transactions on Power Systems, 1997. DOI: 10.1109/59.574923.

### 鲁棒优化

### 3. The Price of Robustness

- **标记：** `经典` · 鲁棒优化
- **作者：** Dimitris Bertsimas, Melvyn Sim
- **年份 / 期刊：** 2004 · Operations Research
- **DOI：** [10.1287/opre.1030.0065](https://doi.org/10.1287/opre.1030.0065)
- **OpenAlex 引用次数：** 4490
- **BibTeX 键：** `Bertsimas2004price}`
- **与赛题关系：** 预算不确定集与“鲁棒性的代价”，直接对应问题四 Γ_t 与抗风险代价。
- **GB/T 7714：** Dimitris Bertsimas, Melvyn Sim. The Price of Robustness[J]. Operations Research, 2004. DOI: 10.1287/opre.1030.0065.

### 4. Robust Convex Optimization

- **标记：** `经典` · 鲁棒优化
- **作者：** Aharon Ben‐Tal, Arkadi Nemirovski
- **年份 / 期刊：** 1998 · Mathematics of Operations Research
- **DOI：** [10.1287/moor.23.4.769](https://doi.org/10.1287/moor.23.4.769)
- **OpenAlex 引用次数：** 2607
- **BibTeX 键：** `BenTal1998robust}`
- **与赛题关系：** 鲁棒凸优化理论框架。
- **GB/T 7714：** Aharon Ben‐Tal, Arkadi Nemirovski. Robust Convex Optimization[J]. Mathematics of Operations Research, 1998. DOI: 10.1287/moor.23.4.769.

### 消费侧碳核算

### 5. Consumption-based accounting of CO 2 emissions

- **标记：** `经典` · 消费侧碳核算
- **作者：** Steven J. Davis, Ken Caldeira
- **年份 / 期刊：** 2010 · Proceedings of the National Academy of Sciences
- **DOI：** [10.1073/pnas.0906974107](https://doi.org/10.1073/pnas.0906974107)
- **OpenAlex 引用次数：** 1762
- **BibTeX 键：** `Davis2010consumption}`
- **与赛题关系：** 基于消费的 CO2 核算，对应用电地责任。
- **GB/T 7714：** Steven J. Davis, Ken Caldeira. Consumption-based accounting of CO 2 emissions[J]. Proceedings of the National Academy of Sciences, 2010. DOI: 10.1073/pnas.0906974107.

### 6. Outsourcing CO 2 within China

- **标记：** `经典` · 消费侧碳核算
- **作者：** Kuishuang Feng, Steven J. Davis, Laixiang Sun, Xin Li, Dabo Guan, Weidong Liu, Zhu Liu, Klaus Hubacek
- **年份 / 期刊：** 2013 · Proceedings of the National Academy of Sciences
- **DOI：** [10.1073/pnas.1219918110](https://doi.org/10.1073/pnas.1219918110)
- **OpenAlex 引用次数：** 633
- **BibTeX 键：** `Feng2013outsourcing}`
- **与赛题关系：** 中国省际碳外包，对应区域间输电的碳排放转移。
- **GB/T 7714：** Kuishuang Feng, Steven J. Davis, Laixiang Sun, et al.. Outsourcing CO 2 within China[J]. Proceedings of the National Academy of Sciences, 2013. DOI: 10.1073/pnas.1219918110.

### 7. Consumption-based emission accounting for Chinese cities

- **标记：** `经典` · 消费侧碳核算
- **作者：** Zhifu Mi, Yunkun Zhang, Dabo Guan, Yuli Shan, Zhu Liu, Rong‐Gang Cong, Xiao-Chen Yuan, Yi-Ming Wei
- **年份 / 期刊：** 2016 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2016.06.094](https://doi.org/10.1016/j.apenergy.2016.06.094)
- **OpenAlex 引用次数：** 638
- **BibTeX 键：** `Mi2016consumption}`
- **与赛题关系：** 中国城市消费侧排放核算。
- **GB/T 7714：** Zhifu Mi, Yunkun Zhang, Dabo Guan, et al.. Consumption-based emission accounting for Chinese cities[J]. Applied Energy, 2016. DOI: 10.1016/j.apenergy.2016.06.094.

### 碳配额与责任

### 8. Sharing a quota on cumulative carbon emissions

- **标记：** `经典` · 碳配额与责任
- **作者：** Michael Raupach, Steven J. Davis, Glen P. Peters, Robbie M. Andrew, Josep G. Canadell, Philippe Ciais, Pierre Friedlingstein, Frank Jotzo, Detlef P. van Vuuren, Corinne Le Quéré
- **年份 / 期刊：** 2014 · Nature Climate Change
- **DOI：** [10.1038/nclimate2384](https://doi.org/10.1038/nclimate2384)
- **OpenAlex 引用次数：** 391
- **BibTeX 键：** `Raupach2014sharing}`
- **与赛题关系：** 累计碳配额分担，对应问题三区域碳预算。
- **GB/T 7714：** Michael Raupach, Steven J. Davis, Glen P. Peters, et al.. Sharing a quota on cumulative carbon emissions[J]. Nature Climate Change, 2014. DOI: 10.1038/nclimate2384.

### 电力碳流

### 9. Carbon Emission Flow in Networks

- **标记：** `经典` · 电力碳流
- **作者：** Chongqing Kang, Tianrui Zhou, Qixin Chen, Qianyao Xu, Qing Xia, Zhen Ji
- **年份 / 期刊：** 2012 · Scientific Reports
- **DOI：** [10.1038/srep00479](https://doi.org/10.1038/srep00479)
- **OpenAlex 引用次数：** 207
- **BibTeX 键：** `Kang2012carbon}`
- **与赛题关系：** 网络碳流概念模型（康重庆等）。
- **GB/T 7714：** Chongqing Kang, Tianrui Zhou, Qixin Chen, et al.. Carbon Emission Flow in Networks[J]. Scientific Reports, 2012. DOI: 10.1038/srep00479.

### 10. Carbon Emission Flow From Generation to Demand: A Network-Based Model

- **标记：** `经典` · 电力碳流
- **作者：** Chongqing Kang, Tianrui Zhou, Qixin Chen, Jianhui Wang, Yanlong Sun, Qing Xia, Huaguang Yan
- **年份 / 期刊：** 2015 · IEEE Transactions on Smart Grid
- **DOI：** [10.1109/tsg.2015.2388695](https://doi.org/10.1109/tsg.2015.2388695)
- **OpenAlex 引用次数：** 436
- **BibTeX 键：** `Kang2015carbon}`
- **与赛题关系：** 从发电到需求的碳流网络模型，问题二核心方法。
- **GB/T 7714：** Chongqing Kang, Tianrui Zhou, Qixin Chen, et al.. Carbon Emission Flow From Generation to Demand: A Network-Based Model[J]. IEEE Transactions on Smart Grid, 2015. DOI: 10.1109/tsg.2015.2388695.

### 11. Modeling Carbon Emission Flow in Multiple Energy Systems

- **标记：** `经典` · 电力碳流
- **作者：** Yaohua Cheng, Ning Zhang, Yi Wang, Jingwei Yang, Chongqing Kang, Qing Xia
- **年份 / 期刊：** 2018 · IEEE Transactions on Smart Grid
- **DOI：** [10.1109/tsg.2018.2830775](https://doi.org/10.1109/tsg.2018.2830775)
- **OpenAlex 引用次数：** 352
- **BibTeX 键：** `Cheng2018modeling}`
- **与赛题关系：** 综合能源系统碳流建模。
- **GB/T 7714：** Yaohua Cheng, Ning Zhang, Yi Wang, et al.. Modeling Carbon Emission Flow in Multiple Energy Systems[J]. IEEE Transactions on Smart Grid, 2018. DOI: 10.1109/tsg.2018.2830775.

### 12. Optimal Power Scheduling Using Data-Driven Carbon Emission Flow Modelling for Carbon Intensity Control

- **标记：** `经典` · 电力碳流
- **作者：** Yunqi Wang, Jing Qiu, Yuechuan Tao
- **年份 / 期刊：** 2021 · IEEE Transactions on Power Systems
- **DOI：** [10.1109/tpwrs.2021.3126701](https://doi.org/10.1109/tpwrs.2021.3126701)
- **OpenAlex 引用次数：** 171
- **BibTeX 键：** `Wang2021optimal}`
- **与赛题关系：** 数据驱动碳流与碳强度削减的电力调度。
- **GB/T 7714：** Yunqi Wang, Jing Qiu, Yuechuan Tao. Optimal Power Scheduling Using Data-Driven Carbon Emission Flow Modelling for Carbon Intensity Control[J]. IEEE Transactions on Power Systems, 2021. DOI: 10.1109/tpwrs.2021.3126701.

### 不确定性决策

### 13. Decision making under uncertainty in energy systems: State of the art

- **标记：** `经典` · 不确定性决策
- **作者：** Alireza Soroudi, Turaj Amraee
- **年份 / 期刊：** 2013 · Renewable and Sustainable Energy Reviews
- **DOI：** [10.1016/j.rser.2013.08.039](https://doi.org/10.1016/j.rser.2013.08.039)
- **OpenAlex 引用次数：** 482
- **BibTeX 键：** `Soroudi2013decision}`
- **与赛题关系：** 能源系统不确定决策综述。
- **GB/T 7714：** Alireza Soroudi, Turaj Amraee. Decision making under uncertainty in energy systems: State of the art[J]. Renewable and Sustainable Energy Reviews, 2013. DOI: 10.1016/j.rser.2013.08.039.

### 鲁棒调度

### 14. A Two-Stage Robust Optimization for Centralized-Optimal Dispatch of Photovoltaic Inverters in Active Distribution Networks

- **标记：** `经典` · 鲁棒调度
- **作者：** Tao Ding, Cheng Li, Yongheng Yang, Jiangfeng Jiang, Zhaohong Bie, Frede Blaabjerg
- **年份 / 期刊：** 2016 · IEEE Transactions on Sustainable Energy
- **DOI：** [10.1109/tste.2016.2605926](https://doi.org/10.1109/tste.2016.2605926)
- **OpenAlex 引用次数：** 235
- **BibTeX 键：** `Ding2016two}`
- **与赛题关系：** 光伏逆变器两阶段鲁棒调度范例。
- **GB/T 7714：** Tao Ding, Cheng Li, Yongheng Yang, et al.. A Two-Stage Robust Optimization for Centralized-Optimal Dispatch of Photovoltaic Inverters in Active Distribution Networks[J]. IEEE Transactions on Sustainable Energy, 2016. DOI: 10.1109/tste.2016.2605926.

### 区域碳转移

### 15. Provincial transfers of enabled carbon emissions in China: A supply-side perspective

- **标记：** `经典` · 区域碳转移
- **作者：** Rui Xie, Guangxiao Hu, Youguo Zhang, Yu Liu
- **年份 / 期刊：** 2017 · Energy Policy
- **DOI：** [10.1016/j.enpol.2017.04.021](https://doi.org/10.1016/j.enpol.2017.04.021)
- **OpenAlex 引用次数：** 75
- **BibTeX 键：** `Xie2017provincial}`
- **与赛题关系：** 中国省际隐含碳转移（供给侧）。
- **GB/T 7714：** Rui Xie, Guangxiao Hu, Youguo Zhang, et al.. Provincial transfers of enabled carbon emissions in China: A supply-side perspective[J]. Energy Policy, 2017. DOI: 10.1016/j.enpol.2017.04.021.

## 近三年文献（2024–2026）

### 碳流追踪

### 1. Modeling and evaluation of probabilistic carbon emission flow for power systems considering load and renewable energy uncertainties

- **标记：** `近三年` · 碳流追踪
- **作者：** Xiaocong Sun, Minglei Bao, Yi Ding, Hengyu Hui, Yonghua Song, Chenghang Zheng, Xiang Gao
- **年份 / 期刊：** 2024 · Energy
- **DOI：** [10.1016/j.energy.2024.130768](https://doi.org/10.1016/j.energy.2024.130768)
- **OpenAlex 引用次数：** 44
- **BibTeX 键：** `Sun2024modeling}`
- **与赛题关系：** 计及负荷与新能源不确定性的概率碳流。
- **GB/T 7714：** Xiaocong Sun, Minglei Bao, Yi Ding, et al.. Modeling and evaluation of probabilistic carbon emission flow for power systems considering load and renewable energy uncertainties[J]. Energy, 2024. DOI: 10.1016/j.energy.2024.130768.

### 2. Calculating Probabilistic Carbon Emission Flow: An Adaptive Regression-Based Framework

- **标记：** `近三年` · 碳流追踪
- **作者：** Mingchen Ma, Yaowang Li, Ershun Du, Haiyang Jiang, Ning Zhang, Wei Wang, Min Wang
- **年份 / 期刊：** 2024 · IEEE Transactions on Sustainable Energy
- **DOI：** [10.1109/tste.2024.3358344](https://doi.org/10.1109/tste.2024.3358344)
- **OpenAlex 引用次数：** 23
- **BibTeX 键：** `Ma2024calculating}`
- **与赛题关系：** 自适应回归的概率碳流计算。
- **GB/T 7714：** Mingchen Ma, Yaowang Li, Ershun Du, et al.. Calculating Probabilistic Carbon Emission Flow: An Adaptive Regression-Based Framework[J]. IEEE Transactions on Sustainable Energy, 2024. DOI: 10.1109/tste.2024.3358344.

### 3. A Distributed Computing Algorithm for Electricity Carbon Emission Flow and Carbon Emission Intensity

- **标记：** `近三年` · 碳流追踪
- **作者：** Xinping Wu, Wei Yang, Ning Zhang, Chunlei Zhou, Jinwei Song, Chongqing Kang
- **年份 / 期刊：** 2024 · Protection and Control of Modern Power Systems
- **DOI：** [10.23919/pcmp.2023.000379](https://doi.org/10.23919/pcmp.2023.000379)
- **OpenAlex 引用次数：** 34
- **BibTeX 键：** `Wu2024distributed}`
- **与赛题关系：** 电力碳流与碳强度的分布式计算，适合多区域。
- **GB/T 7714：** Xinping Wu, Wei Yang, Ning Zhang, et al.. A Distributed Computing Algorithm for Electricity Carbon Emission Flow and Carbon Emission Intensity[J]. Protection and Control of Modern Power Systems, 2024. DOI: 10.23919/pcmp.2023.000379.

### 4. A study on carbon emission flow tracking for new type power systems

- **标记：** `近三年` · 碳流追踪
- **作者：** Jiang Hu, Ke Qin, Rui Ma, Wenxia Liu, Jiayuan Zhang, Luming Pang, Jiawang Zhang
- **年份 / 期刊：** 2025 · International Journal of Electrical Power & Energy Systems
- **DOI：** [10.1016/j.ijepes.2025.110455](https://doi.org/10.1016/j.ijepes.2025.110455)
- **OpenAlex 引用次数：** 22
- **BibTeX 键：** `Hu2025study}`
- **与赛题关系：** 新型电力系统碳流追踪（2025）。
- **GB/T 7714：** Jiang Hu, Ke Qin, Rui Ma, et al.. A study on carbon emission flow tracking for new type power systems[J]. International Journal of Electrical Power & Energy Systems, 2025. DOI: 10.1016/j.ijepes.2025.110455.

### 5. Towards carbon‐free electricity: A flow‐based framework for power grid carbon accounting and decarbonization

- **标记：** `近三年` · 碳流追踪
- **作者：** Xin Chen, Hungpo Chao, Wenbo Shi, Na Li
- **年份 / 期刊：** 2024 · Energy Conversion and Economics
- **DOI：** [10.1049/enc2.12134](https://doi.org/10.1049/enc2.12134)
- **OpenAlex 引用次数：** 25
- **BibTeX 键：** `Chen2024towards}`
- **与赛题关系：** 面向无碳电力的基于潮流的电网碳核算与决策框架。
- **GB/T 7714：** Xin Chen, Hungpo Chao, Wenbo Shi, et al.. Towards carbon‐free electricity: A flow‐based framework for power grid carbon accounting and decarbonization[J]. Energy Conversion and Economics, 2024. DOI: 10.1049/enc2.12134.

### 低碳调度

### 6. Carbon-Aware Optimal Power Flow

- **标记：** `近三年` · 低碳调度
- **作者：** Xin Chen, Xu Andy Sun, Weidong Shi, Na Li
- **年份 / 期刊：** 2024 · IEEE Transactions on Power Systems
- **DOI：** [10.1109/tpwrs.2024.3514516](https://doi.org/10.1109/tpwrs.2024.3514516)
- **OpenAlex 引用次数：** 37
- **BibTeX 键：** `Chen2024carbon}`
- **与赛题关系：** 碳感知最优潮流（Carbon-Aware OPF）。
- **GB/T 7714：** Xin Chen, Xu Andy Sun, Weidong Shi, et al.. Carbon-Aware Optimal Power Flow[J]. IEEE Transactions on Power Systems, 2024. DOI: 10.1109/tpwrs.2024.3514516.

### 7. Low-Carbon Economic Dispatch of Integrated Energy Systems Considering Full-Process Carbon Emission Tracking and Low Carbon Demand Response

- **标记：** `近三年` · 低碳调度
- **作者：** Yumin Zhang, Pengkai Sun, Xingquan Ji, Ming Yang, Pingfeng Ye
- **年份 / 期刊：** 2024 · IEEE Transactions on Network Science and Engineering
- **DOI：** [10.1109/tnse.2024.3420771](https://doi.org/10.1109/tnse.2024.3420771)
- **OpenAlex 引用次数：** 41
- **BibTeX 键：** `Zhang2024low}`
- **与赛题关系：** 计及全过程碳流的综合能源低碳经济调度。
- **GB/T 7714：** Yumin Zhang, Pengkai Sun, Xingquan Ji, et al.. Low-Carbon Economic Dispatch of Integrated Energy Systems Considering Full-Process Carbon Emission Tracking and Low Carbon Demand Response[J]. IEEE Transactions on Network Science and Engineering, 2024. DOI: 10.1109/tnse.2024.3420771.

### 8. Low-carbon Economic Dispatch of Integrated Energy Systems Considering Extended Carbon Emission Flow

- **标记：** `近三年` · 低碳调度
- **作者：** Yumin Zhang, Pengkai Sun, Xingquan Ji, Fushuan Wen, Ming Yang, Pingfeng Ye
- **年份 / 期刊：** 2024 · Journal of Modern Power Systems and Clean Energy
- **DOI：** [10.35833/mpce.2023.000743](https://doi.org/10.35833/mpce.2023.000743)
- **OpenAlex 引用次数：** 28
- **BibTeX 键：** `Zhang2024low2}`
- **与赛题关系：** 扩展碳流的综合能源低碳经济调度。
- **GB/T 7714：** Yumin Zhang, Pengkai Sun, Xingquan Ji, et al.. Low-carbon Economic Dispatch of Integrated Energy Systems Considering Extended Carbon Emission Flow[J]. Journal of Modern Power Systems and Clean Energy, 2024. DOI: 10.35833/mpce.2023.000743.

### 9. Low-carbon economic dispatch strategy for integrated power system based on the substitution effect of carbon tax and carbon trading

- **标记：** `近三年` · 低碳调度
- **作者：** Tiancheng Ouyang, Yinxuan Li, Shutao Xie, Chengchao Wang, Chunlan Mo
- **年份 / 期刊：** 2024 · Energy
- **DOI：** [10.1016/j.energy.2024.130960](https://doi.org/10.1016/j.energy.2024.130960)
- **OpenAlex 引用次数：** 44
- **BibTeX 键：** `Ouyang2024low}`
- **与赛题关系：** 计及替代效应的综合电力系统低碳经济调度。
- **GB/T 7714：** Tiancheng Ouyang, Yinxuan Li, Shutao Xie, et al.. Low-carbon economic dispatch strategy for integrated power system based on the substitution effect of carbon tax and carbon trading[J]. Energy, 2024. DOI: 10.1016/j.energy.2024.130960.

### 鲁棒与不确定

### 10. Data-driven two-stage robust optimization dispatching model and benefit allocation strategy for a novel virtual power plant considering carbon-green certificate equivalence conversion mechanism

- **标记：** `近三年` · 鲁棒与不确定
- **作者：** Liwei Ju, ShuoShuo Lv, Zheyu Zhang, Gen Li, Wei Gan, Jiangpeng Fang
- **年份 / 期刊：** 2024 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2024.122974](https://doi.org/10.1016/j.apenergy.2024.122974)
- **OpenAlex 引用次数：** 59
- **BibTeX 键：** `Ju2024data}`
- **与赛题关系：** 数据驱动两阶段鲁棒调度与收益分配。
- **GB/T 7714：** Liwei Ju, ShuoShuo Lv, Zheyu Zhang, et al.. Data-driven two-stage robust optimization dispatching model and benefit allocation strategy for a novel virtual power plant considering carbon-green certificate equivalence conversion mechanism[J]. Applied Energy, 2024. DOI: 10.1016/j.apenergy.2024.122974.

### 11. Two stage robust economic dispatching of microgrid considering uncertainty of wind, solar and electricity load along with carbon emission predicted by neural network model

- **标记：** `近三年` · 鲁棒与不确定
- **作者：** Haotian Shen, Hualiang Zhang, Yujie Xu, Haisheng Chen, Zhilai Zhang, Wenkai Li, Xu Su, Yalin Xu, Yilin Zhu
- **年份 / 期刊：** 2024 · Energy
- **DOI：** [10.1016/j.energy.2024.131571](https://doi.org/10.1016/j.energy.2024.131571)
- **OpenAlex 引用次数：** 33
- **BibTeX 键：** `Shen2024two}`
- **与赛题关系：** 风光电价不确定下微网两阶段鲁棒经济调度。
- **GB/T 7714：** Haotian Shen, Hualiang Zhang, Yujie Xu, et al.. Two stage robust economic dispatching of microgrid considering uncertainty of wind, solar and electricity load along with carbon emission predicted by neural network model[J]. Energy, 2024. DOI: 10.1016/j.energy.2024.131571.

### 规划与项目组合

### 12. A two-stage low-carbon economic coordinated dispatching model for generation-load-storage resources considering flexible supply-demand balance

- **标记：** `近三年` · 规划与项目组合
- **作者：** Yuanyuan Zhang, Huiru Zhao, Ze Qi, Bingkang Li
- **年份 / 期刊：** 2024 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2024.123981](https://doi.org/10.1016/j.apenergy.2024.123981)
- **OpenAlex 引用次数：** 31
- **BibTeX 键：** `Zhang2024two}`
- **与赛题关系：** 源荷储两阶段低碳经济协调调度，对应五年项目与运行耦合。
- **GB/T 7714：** Yuanyuan Zhang, Huiru Zhao, Ze Qi, et al.. A two-stage low-carbon economic coordinated dispatching model for generation-load-storage resources considering flexible supply-demand balance[J]. Applied Energy, 2024. DOI: 10.1016/j.apenergy.2024.123981.

### 消费侧核算

### 13. A comprehensive consumption-based carbon accounting framework for power system towards low-carbon transition

- **标记：** `近三年` · 消费侧核算
- **作者：** Chen Ling, Qing Yang, Qingrui Wang, Pietro Bartocci, Lei Jiang, Zishuo Xu, Luyao Wang
- **年份 / 期刊：** 2024 · Renewable and Sustainable Energy Reviews
- **DOI：** [10.1016/j.rser.2024.114866](https://doi.org/10.1016/j.rser.2024.114866)
- **OpenAlex 引用次数：** 30
- **BibTeX 键：** `Ling2024comprehensive}`
- **与赛题关系：** 电力系统消费侧碳核算框架综述（2024）。
- **GB/T 7714：** Chen Ling, Qing Yang, Qingrui Wang, et al.. A comprehensive consumption-based carbon accounting framework for power system towards low-carbon transition[J]. Renewable and Sustainable Energy Reviews, 2024. DOI: 10.1016/j.rser.2024.114866.

### 数据与状态估计

### 14. A Survey of Power System State Estimation Using Multiple Data Sources: PMUs, SCADA, AMI, and Beyond

- **标记：** `近三年` · 数据与状态估计
- **作者：** Gang Cheng, Yuzhang Lin, Ali Abur, Antonio Gómez‐Expósito, Wenchuan Wu
- **年份 / 期刊：** 2023 · IEEE Transactions on Smart Grid
- **DOI：** [10.1109/tsg.2023.3286401](https://doi.org/10.1109/tsg.2023.3286401)
- **OpenAlex 引用次数：** 175
- **BibTeX 键：** `Cheng2023survey}`
- **与赛题关系：** 多源量测（PMU/SCADA/AMI）状态估计综述，对应问题一多源数据校正。
- **GB/T 7714：** Gang Cheng, Yuzhang Lin, Ali Abur, et al.. A Survey of Power System State Estimation Using Multiple Data Sources: PMUs, SCADA, AMI, and Beyond[J]. IEEE Transactions on Smart Grid, 2023. DOI: 10.1109/tsg.2023.3286401.

### 多区域协同

### 15. Cooperative optimal dispatch of multi-microgrids for low carbon economy based on personalized federated reinforcement learning

- **标记：** `近三年` · 多区域协同
- **作者：** Ting Yang, Zheming Xu, Shijie Ji, Guoliang Liu, Xinhong Li, Haibo Kong
- **年份 / 期刊：** 2024 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2024.124641](https://doi.org/10.1016/j.apenergy.2024.124641)
- **OpenAlex 引用次数：** 29
- **BibTeX 键：** `Yang2024cooperative}`
- **与赛题关系：** 多微网低碳协同优化调度。
- **GB/T 7714：** Ting Yang, Zheming Xu, Shijie Ji, et al.. Cooperative optimal dispatch of multi-microgrids for low carbon economy based on personalized federated reinforcement learning[J]. Applied Energy, 2024. DOI: 10.1016/j.apenergy.2024.124641.

### 责任与泄漏

### 16. Trade flows, carbon leakage, and the EU Emissions Trading System

- **标记：** `近三年` · 责任与泄漏
- **作者：** Maria Wang, Tero Kuusi
- **年份 / 期刊：** 2024 · Energy Economics
- **DOI：** [10.1016/j.eneco.2024.107556](https://doi.org/10.1016/j.eneco.2024.107556)
- **OpenAlex 引用次数：** 60
- **BibTeX 键：** `Wang2024trade}`
- **与赛题关系：** 贸易流、碳泄漏与排放权交易，启发跨区责任分担。
- **GB/T 7714：** Maria Wang, Tero Kuusi. Trade flows, carbon leakage, and the EU Emissions Trading System[J]. Energy Economics, 2024. DOI: 10.1016/j.eneco.2024.107556.

## 方法论奠基文献（2026-08-20 增补）

补齐解决方案各环节的方法论出处：问题一数据调和与状态估计、问题二生产/消费/共担责任核算、问题三碳配额分配与扩展规划、问题四可调鲁棒与滚动优化。全部经 doi.org content negotiation 核验。

### 数据调和与状态估计（问题一）

### 1. Data reconciliation — Progress and challenges

- **标记：** `增补` · 数据调和
- **作者：** Cameron M. Crowe
- **年份 / 期刊：** 1996 · Journal of Process Control
- **DOI：** [10.1016/0959-1524(96)00012-1](https://doi.org/10.1016/0959-1524(96)00012-1)
- **OpenAlex 引用次数：** 253
- **BibTeX 键：** `Crowe1996data`
- **与赛题关系：** 数据调和（在物料/能量守恒约束下用加权最小二乘校正观测）经典综述，问题一校正模型的方法论出处。
- **GB/T 7714：** Crowe C M. Data reconciliation — Progress and challenges[J]. Journal of Process Control, 1996, 6(2-3): 89-98. DOI: 10.1016/0959-1524(96)00012-1.

### 2. The Importance of Data Reconciliation and Gross Error Detection

- **标记：** `增补` · 数据调和
- **作者：** Shankar Narasimhan, Cornelius Jordache
- **年份 / 出处：** 1999 · 专著《Data Reconciliation and Gross Error Detection》首章（Elsevier）
- **DOI：** [10.1016/b978-088415255-2/50002-1](https://doi.org/10.1016/b978-088415255-2/50002-1)
- **OpenAlex 引用次数：** 60
- **BibTeX 键：** `Narasimhan1999data`
- **与赛题关系：** 数据调和与粗差检测标准专著：冗余度、可观测性、粗差检验统计量，直接支撑问题一异常识别与影响度分析。
- **GB/T 7714：** Narasimhan S, Jordache C. The Importance of Data Reconciliation and Gross Error Detection[M]//Data Reconciliation and Gross Error Detection. Elsevier, 1999: 1-31. DOI: 10.1016/b978-088415255-2/50002-1.

### 3. Power System Static-State Estimation, Part I: Exact Model

- **标记：** `增补` · 状态估计
- **作者：** Fred Schweppe, J. Wildes
- **年份 / 期刊：** 1970 · IEEE Transactions on Power Apparatus and Systems
- **DOI：** [10.1109/TPAS.1970.292678](https://doi.org/10.1109/TPAS.1970.292678)
- **OpenAlex 引用次数：** 1386
- **BibTeX 键：** `Schweppe1970power`
- **与赛题关系：** 电力系统加权最小二乘状态估计奠基论文，问题一 QP 校正目标函数的理论源头。
- **GB/T 7714：** Schweppe F C, Wildes J. Power System Static-State Estimation, Part I: Exact Model[J]. IEEE Transactions on Power Apparatus and Systems, 1970, PAS-89(1): 120-125. DOI: 10.1109/TPAS.1970.292678.

### 4. Power System State Estimation: Theory and Implementation

- **标记：** `增补` · 状态估计
- **作者：** Ali Abur, Antonio Gómez Expósito
- **年份 / 出版社：** 2004 · CRC Press（专著）
- **DOI：** [10.1201/9780203913673](https://doi.org/10.1201/9780203913673)
- **OpenAlex 引用次数：** 2999
- **BibTeX 键：** `Abur2004power`
- **与赛题关系：** 标准化残差最大检验（LNR）、坏数据辨识与量测冗余理论的教科书，支撑问题一异常检测与"哪些观测影响大"的分析。
- **GB/T 7714：** Abur A, Expósito A G. Power System State Estimation: Theory and Implementation[M]. CRC Press, 2004. DOI: 10.1201/9780203913673.

### 责任核算（问题二）

### 5. From production-based to consumption-based national emission inventories

- **标记：** `增补` · 责任核算
- **作者：** Glen P. Peters
- **年份 / 期刊：** 2008 · Ecological Economics
- **DOI：** [10.1016/j.ecolecon.2007.10.014](https://doi.org/10.1016/j.ecolecon.2007.10.014)
- **OpenAlex 引用次数：** 1160
- **BibTeX 键：** `Peters2008production`
- **与赛题关系：** 生产侧与消费侧碳清单的系统对比，问题二"发电地/用电地承担"两种口径的定义出处。
- **GB/T 7714：** Peters G P. From production-based to consumption-based national emission inventories[J]. Ecological Economics, 2008, 65(1): 13-23. DOI: 10.1016/j.ecolecon.2007.10.014.

### 6. Shared producer and consumer responsibility — Theory and practice

- **标记：** `增补` · 责任核算
- **作者：** Manfred Lenzen, Joy Murray, Fabian Sack, Thomas Wiedmann
- **年份 / 期刊：** 2007 · Ecological Economics
- **DOI：** [10.1016/j.ecolecon.2006.05.018](https://doi.org/10.1016/j.ecolecon.2006.05.018)
- **OpenAlex 引用次数：** 658
- **BibTeX 键：** `Lenzen2007shared`
- **与赛题关系：** 生产者-消费者共担责任理论；其"责任守恒（不重复、不遗漏）"公理是问题二共担方案设计与校验的依据。
- **GB/T 7714：** Lenzen M, Murray J, Sack F, et al. Shared producer and consumer responsibility — Theory and practice[J]. Ecological Economics, 2007, 61(1): 27-42. DOI: 10.1016/j.ecolecon.2006.05.018.

### 7. A consistent input–output formulation of shared producer and consumer responsibility

- **标记：** `增补` · 责任核算
- **作者：** Blanca Gallego, Manfred Lenzen
- **年份 / 期刊：** 2005 · Economic Systems Research
- **DOI：** [10.1080/09535310500283492](https://doi.org/10.1080/09535310500283492)
- **OpenAlex 引用次数：** 264
- **BibTeX 键：** `Gallego2005consistent`
- **与赛题关系：** 共担责任的一致性数学形式（分担系数体系），问题二 λ 加权共担公式的形式化出处。
- **GB/T 7714：** Gallego B, Lenzen M. A consistent input–output formulation of shared producer and consumer responsibility[J]. Economic Systems Research, 2005, 17(4): 365-391. DOI: 10.1080/09535310500283492.

### 配额分配与规划（问题三）

### 8. Carbon dioxide emissions allocation: A review

- **标记：** `增补` · 配额分配
- **作者：** P. Zhou, M. Wang
- **年份 / 期刊：** 2016 · Ecological Economics
- **DOI：** [10.1016/j.ecolecon.2016.03.001](https://doi.org/10.1016/j.ecolecon.2016.03.001)
- **OpenAlex 引用次数：** 363
- **BibTeX 键：** `Zhou2016carbon`
- **与赛题关系：** 碳排放配额分配方法系统综述（公平/效率/混合准则），问题三省内区域碳预算分配的准则选择依据。
- **GB/T 7714：** Zhou P, Wang M. Carbon dioxide emissions allocation: A review[J]. Ecological Economics, 2016, 125: 47-59. DOI: 10.1016/j.ecolecon.2016.03.001.

### 9. State-of-the-art generation expansion planning: A review

- **标记：** `增补` · 规划
- **作者：** Nikolaos E. Koltsaklis, Athanasios S. Dagoumas
- **年份 / 期刊：** 2018 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2018.08.087](https://doi.org/10.1016/j.apenergy.2018.08.087)
- **OpenAlex 引用次数：** 329
- **BibTeX 键：** `Koltsaklis2018generation`
- **与赛题关系：** 电源扩展规划 MILP 建模范式综述（投资-运行耦合、多年期约束），问题三五年项目组合模型的框架依据。
- **GB/T 7714：** Koltsaklis N E, Dagoumas A S. State-of-the-art generation expansion planning: A review[J]. Applied Energy, 2018, 230: 563-589. DOI: 10.1016/j.apenergy.2018.08.087.

### 鲁棒与滚动优化（问题四）

### 10. Adjustable robust solutions of uncertain linear programs

- **标记：** `增补` · 鲁棒优化
- **作者：** A. Ben-Tal, A. Goryashko, E. Guslitzer, A. Nemirovski
- **年份 / 期刊：** 2004 · Mathematical Programming
- **DOI：** [10.1007/s10107-003-0454-y](https://doi.org/10.1007/s10107-003-0454-y)
- **OpenAlex 引用次数：** 1407
- **BibTeX 键：** `BenTal2004adjustable`
- **与赛题关系：** 可调（两阶段）鲁棒优化奠基：区分"此时此地"与"观望"决策，对应问题四已开工项目不可逆、后期可调整的结构。
- **GB/T 7714：** Ben-Tal A, Goryashko A, Guslitzer E, et al. Adjustable robust solutions of uncertain linear programs[J]. Mathematical Programming, 2004, 99(2): 351-376. DOI: 10.1007/s10107-003-0454-y.

### 11. Adaptive Robust Optimization for the Security Constrained Unit Commitment Problem

- **标记：** `增补` · 鲁棒优化
- **作者：** Dimitris Bertsimas, Eugene Litvinov, Xu Andy Sun, Jinye Zhao, Tongxin Zheng
- **年份 / 期刊：** 2013 · IEEE Transactions on Power Systems
- **DOI：** [10.1109/TPWRS.2012.2205021](https://doi.org/10.1109/TPWRS.2012.2205021)
- **OpenAlex 引用次数：** 1659
- **BibTeX 键：** `Bertsimas2013adaptive`
- **与赛题关系：** 预算不确定集 + 两阶段鲁棒在电力系统的标杆应用（含列约束生成求解思路），问题四鲁棒调控模型的直接范例。
- **GB/T 7714：** Bertsimas D, Litvinov E, Sun X A, et al. Adaptive Robust Optimization for the Security Constrained Unit Commitment Problem[J]. IEEE Transactions on Power Systems, 2013, 28(1): 52-63. DOI: 10.1109/TPWRS.2012.2205021.

### 12. A rolling horizon optimization framework for the simultaneous energy supply and demand planning in microgrids

- **标记：** `增补` · 滚动优化
- **作者：** Javier Silvente, Georgios M. Kopanos, Efstratios N. Pistikopoulos, Antonio Espuña
- **年份 / 期刊：** 2015 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2015.05.090](https://doi.org/10.1016/j.apenergy.2015.05.090)
- **OpenAlex 引用次数：** 292
- **BibTeX 键：** `Silvente2015rolling`
- **与赛题关系：** 能源系统滚动时域优化框架，问题四"逐年观测-滚动重优化"调控机制的方法出处。
- **GB/T 7714：** Silvente J, Kopanos G M, Pistikopoulos E N, et al. A rolling horizon optimization framework for the simultaneous energy supply and demand planning in microgrids[J]. Applied Energy, 2015, 155: 485-501. DOI: 10.1016/j.apenergy.2015.05.090.

## SerpApi 补充检索（2026-08-20）

经 SerpApi（Google Scholar 引擎）定向检索、Crossref 核验 DOI、doi.org 拉取 BibTeX。补强五个方向：Q1 电力-排放数据调和实证、Q2 合作博弈责任分摊、Q3 中国省级碳配额分配实证、Q4 两阶段鲁棒求解算法与联络线鲁棒调度。

### 数据调和实证（问题一）

### 1. A physics-informed data reconciliation framework for real-time electricity and emissions tracking

- **标记：** `SerpApi` · 数据调和实证
- **作者：** Jacques A. de Chalendar, Sally M. Benson
- **年份 / 期刊：** 2021 · Applied Energy
- **DOI：** [10.1016/j.apenergy.2021.117761](https://doi.org/10.1016/j.apenergy.2021.117761)
- **OpenAlex 引用次数：** 2
- **BibTeX 键：** `deChalendar2021physics`
- **与赛题关系：** 在电量守恒物理约束下对美国电网多源监测数据做调和并实时追踪排放——与本题问题一 + 问题二的组合几乎同构，是最直接的实证范例。
- **GB/T 7714：** de Chalendar J A, Benson S M. A physics-informed data reconciliation framework for real-time electricity and emissions tracking[J]. Applied Energy, 2021, 304: 117761. DOI: 10.1016/j.apenergy.2021.117761.

### 2. Tracking emissions in the US electricity system

- **标记：** `SerpApi` · 碳追踪实证
- **作者：** Jacques A. de Chalendar, John Taggart, Sally M. Benson
- **年份 / 期刊：** 2019 · Proceedings of the National Academy of Sciences
- **DOI：** [10.1073/pnas.1912950116](https://doi.org/10.1073/pnas.1912950116)
- **OpenAlex 引用次数：** 121
- **BibTeX 键：** `deChalendar2019tracking`
- **与赛题关系：** 用真实平衡区交换数据做消费侧小时级碳强度追踪的标杆工作，支撑问题一数据基础与问题二消费侧核算的衔接。
- **GB/T 7714：** de Chalendar J A, Taggart J, Benson S M. Tracking emissions in the US electricity system[J]. Proceedings of the National Academy of Sciences, 2019, 116(51): 25497-25502. DOI: 10.1073/pnas.1912950116.

### 合作博弈责任分摊（问题二）

### 3. A cooperative game analysis for the allocation of carbon emissions reduction responsibility in China's power industry

- **标记：** `SerpApi` · 责任分摊
- **作者：** Quande Qin, Yuan Liu, Jia-Ping Huang
- **年份 / 期刊：** 2020 · Energy Economics
- **DOI：** [10.1016/j.eneco.2020.104960](https://doi.org/10.1016/j.eneco.2020.104960)
- **OpenAlex 引用次数：** 82
- **BibTeX 键：** `Qin2020cooperative`
- **与赛题关系：** 中国电力行业减排责任的合作博弈（Shapley 型）分摊,问题二共担方案的博弈论备选路线依据。
- **GB/T 7714：** Qin Q, Liu Y, Huang J P. A cooperative game analysis for the allocation of carbon emissions reduction responsibility in China's power industry[J]. Energy Economics, 2020, 92: 104960. DOI: 10.1016/j.eneco.2020.104960.

### 4. Cooperative Game for Carbon Obligation Allocation Among Distribution System Operators to Incentivize the Proliferation of Renewable Energy

- **标记：** `SerpApi` · 责任分摊
- **作者：** Quan Zhou, Mohammad Shahidehpour, Tao Sun, Donghan Feng, Mingyu Yan
- **年份 / 期刊：** 2019 · IEEE Transactions on Smart Grid
- **DOI：** [10.1109/tsg.2019.2903686](https://doi.org/10.1109/tsg.2019.2903686)
- **OpenAlex 引用次数：** 36
- **BibTeX 键：** `Zhou2019cooperative`
- **与赛题关系：** 电网主体间碳义务的合作博弈分摊并论证核的存在性,支撑问题二共担方案的激励相容性讨论。
- **GB/T 7714：** Zhou Q, Shahidehpour M, Sun T, et al. Cooperative Game for Carbon Obligation Allocation Among Distribution System Operators to Incentivize the Proliferation of Renewable Energy[J]. IEEE Transactions on Smart Grid, 2019, 10(6): 6355-6365. DOI: 10.1109/tsg.2019.2903686.

### 中国省级碳配额分配（问题三）

### 5. Regional allocation of CO2 emissions allowance over provinces in China by 2020

- **标记：** `SerpApi` · 配额分配
- **作者：** Ke Wang, Xian Zhang, Yi-Ming Wei, Shiwei Yu
- **年份 / 期刊：** 2013 · Energy Policy
- **DOI：** [10.1016/j.enpol.2012.11.030](https://doi.org/10.1016/j.enpol.2012.11.030)
- **OpenAlex 引用次数：** 245
- **BibTeX 键：** `Wang2013regional`
- **与赛题关系：** 中国省域碳配额分配经典实证（公平/效率准则组合）,问题三区域碳预算分配准则的国内出处。
- **GB/T 7714：** Wang K, Zhang X, Wei Y M, et al. Regional allocation of CO2 emissions allowance over provinces in China by 2020[J]. Energy Policy, 2013, 54: 214-229. DOI: 10.1016/j.enpol.2012.11.030.

### 6. Allocation of carbon emission quotas in China's provincial power sector based on entropy method and ZSG-DEA

- **标记：** `SerpApi` · 配额分配
- **作者：** Xiaoyan Cui, Tao Zhao, Juan Wang
- **年份 / 期刊：** 2021 · Journal of Cleaner Production
- **DOI：** [10.1016/j.jclepro.2020.124683](https://doi.org/10.1016/j.jclepro.2020.124683)
- **OpenAlex 引用次数：** 168
- **BibTeX 键：** `Cui2021allocation`
- **与赛题关系：** 省级电力部门碳配额的熵权 + 零和 DEA 分配,与本题"区域电力碳预算"对象一致。
- **GB/T 7714：** Cui X, Zhao T, Wang J. Allocation of carbon emission quotas in China's provincial power sector based on entropy method and ZSG-DEA[J]. Journal of Cleaner Production, 2021, 284: 124683. DOI: 10.1016/j.jclepro.2020.124683.

### 7. Research on the allocation scheme of carbon emission allowances for China's provincial power grids

- **标记：** `SerpApi` · 配额分配
- **作者：** Muren Bai, Cunbin Li
- **年份 / 期刊：** 2024 · Energy
- **DOI：** [10.1016/j.energy.2024.131551](https://doi.org/10.1016/j.energy.2024.131551)
- **OpenAlex 引用次数：** 34
- **BibTeX 键：** `Bai2024allocation`
- **与赛题关系：** 面向省级电网的碳配额分配最新方案,问题三分配层的近期对标。
- **GB/T 7714：** Bai M, Li C. Research on the allocation scheme of carbon emission allowances for China's provincial power grids[J]. Energy, 2024, 299: 131551. DOI: 10.1016/j.energy.2024.131551.

### 鲁棒求解与联络线调度（问题四）

### 8. Solving two-stage robust optimization problems using a column-and-constraint generation method

- **标记：** `SerpApi` · 鲁棒求解算法
- **作者：** Bo Zeng, Long Zhao
- **年份 / 期刊：** 2013 · Operations Research Letters
- **DOI：** [10.1016/j.orl.2013.05.003](https://doi.org/10.1016/j.orl.2013.05.003)
- **OpenAlex 引用次数：** 1796
- **BibTeX 键：** `Zeng2013solving`
- **与赛题关系：** 两阶段鲁棒优化的标准精确算法（列约束生成 C&CG）,问题四两阶段模型的求解方法出处。
- **GB/T 7714：** Zeng B, Zhao L. Solving two-stage robust optimization problems using a column-and-constraint generation method[J]. Operations Research Letters, 2013, 41(5): 457-461. DOI: 10.1016/j.orl.2013.05.003.

### 9. Adaptive Robust Tie-Line Scheduling Considering Wind Power Uncertainty for Interconnected Power Systems

- **标记：** `SerpApi` · 鲁棒调度
- **作者：** Zhigang Li, Wenchuan Wu, Mohammad Shahidehpour, Boming Zhang
- **年份 / 期刊：** 2016 · IEEE Transactions on Power Systems
- **DOI：** [10.1109/tpwrs.2015.2466546](https://doi.org/10.1109/tpwrs.2015.2466546)
- **OpenAlex 引用次数：** 120
- **BibTeX 键：** `Li2016adaptive`
- **与赛题关系：** 互联电网联络线交换计划的自适应鲁棒调度,与问题四"区域间输电作为补偿手段"的结构直接对应。
- **GB/T 7714：** Li Z, Wu W, Shahidehpour M, et al. Adaptive Robust Tie-Line Scheduling Considering Wind Power Uncertainty for Interconnected Power Systems[J]. IEEE Transactions on Power Systems, 2016, 31(4): 2701-2713. DOI: 10.1109/tpwrs.2015.2466546.

## 检索说明

1. OpenAlex `title.search` 与 DOI 直查；经典条目用题面核心模型名定位。SerpApi（Google Scholar 引擎）补检的条目先经 Crossref `query.bibliographic` 确认 DOI。
2. 每条 DOI 再向 `https://doi.org/` 做 content negotiation 取 BibTeX。
3. 未收录无 DOI 或无法核验的条目；已剔除明显跑题与撤稿文献。
4. 正文引用请用 GB/T 7714-2015；LaTeX 可直接使用 `refs.bib`。
