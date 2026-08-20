# A 题参考文献

条目均经 OpenAlex 解析 DOI，并用 Crossref / doi.org 拉取 BibTeX，避免虚构文献。引用次数为 OpenAlex 统计，随时间变化。

- 经典（2023 年及以前）：**23** 篇
- 近三年（2024–2026）：**14** 篇
- 合计：**37** 篇
- BibTeX：[`refs.bib`](refs.bib)

## 与赛题子问题的对应

| 子问题 | 建议精读（BibTeX 键） |
|--------|------------------------|
| 问题1 最短完工时间、干线+无人机批次 | `Murray2015flying`, `Sacramento2019adaptive`, `Roberti2021exact`, `Madani2024hybrid`, `Boccia2024exact` |
| 问题2 轻型车/无人机配置与日均净收益 | `Ha2017min`, `Jeong2019truck`, `Stolaroff2018energy`, `Mishra2024integrated`, `Bao2025future` |
| 问题3 C 类时限与准时率 | `Deng2024stochastic`, `Yin2024exact`, `Cui2024dynamic`, `Wang2024truck` |
| 问题4 新增物流中心/共址选址 | `Perboli2011two`, `Kitjacharoenchai2019two`, `Kim2018traveling`, `Macrina2020drone` |
| 载具协同与不可达点 | `Munasinghe2024comprehensive`, `Shi2024optimal`, `Carlsson2017coordinated` |

## 经典文献

### 卡车-无人机协同路径

### 1. The flying sidekick traveling salesman problem: Optimization of drone-assisted parcel delivery

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Chase Murray, Amanda Chu
- **年份 / 期刊：** 2015 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2015.03.005](https://doi.org/10.1016/j.trc.2015.03.005)
- **OpenAlex 引用次数：** 1667
- **BibTeX 键：** `Murray2015flying}`
- **与赛题关系：** FSTSP 奠基：卡车携带无人机协同配送，对应问题1的干线+末端协同与完工时间目标。
- **GB/T 7714：** Chase Murray, Amanda Chu. The flying sidekick traveling salesman problem: Optimization of drone-assisted parcel delivery[J]. Transportation Research Part C Emerging Technologies, 2015. DOI: 10.1016/j.trc.2015.03.005.

### 2. Vehicle Routing Problems for Drone Delivery

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Kevin Dorling, Jordan Heinrichs, Geoffrey G. Messier, Sebastian Magierowski
- **年份 / 期刊：** 2016 · IEEE Transactions on Systems Man and Cybernetics Systems
- **DOI：** [10.1109/tsmc.2016.2582745](https://doi.org/10.1109/tsmc.2016.2582745)
- **OpenAlex 引用次数：** 1303
- **BibTeX 键：** `Dorling2016vehicle}`
- **与赛题关系：** VRPD 与无人机能耗/续航建模，对应无人机航程与载重-速度约束。
- **GB/T 7714：** Kevin Dorling, Jordan Heinrichs, Geoffrey G. Messier, et al.. Vehicle Routing Problems for Drone Delivery[J]. IEEE Transactions on Systems Man and Cybernetics Systems, 2016. DOI: 10.1109/tsmc.2016.2582745.

### 3. The vehicle routing problem with drones: several worst-case results

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Xingyin Wang, Stefan Poikonen, Bruce Golden
- **年份 / 期刊：** 2016 · Optimization Letters
- **DOI：** [10.1007/s11590-016-1035-3](https://doi.org/10.1007/s11590-016-1035-3)
- **OpenAlex 引用次数：** 542
- **BibTeX 键：** `Wang2016vehicle}`
- **与赛题关系：** VRPD 最坏情形界，给出卡车-无人机相对纯卡车的效率关系。
- **GB/T 7714：** Xingyin Wang, Stefan Poikonen, Bruce Golden. The vehicle routing problem with drones: several worst-case results[J]. Optimization Letters, 2016. DOI: 10.1007/s11590-016-1035-3.

### 4. The vehicle routing problem with drones: Extended models and connections

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Stefan Poikonen, Xingyin Wang, Bruce Golden
- **年份 / 期刊：** 2017 · Networks
- **DOI：** [10.1002/net.21746](https://doi.org/10.1002/net.21746)
- **OpenAlex 引用次数：** 340
- **BibTeX 键：** `Poikonen2017vehicle}`
- **与赛题关系：** VRPD 扩展模型，连接 TSP-D 与多车辆情形。
- **GB/T 7714：** Stefan Poikonen, Xingyin Wang, Bruce Golden. The vehicle routing problem with drones: Extended models and connections[J]. Networks, 2017. DOI: 10.1002/net.21746.

### 5. Coordinated Logistics with a Truck and a Drone

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** John Gunnar Carlsson, Siyuan Song
- **年份 / 期刊：** 2017 · Management Science
- **DOI：** [10.1287/mnsc.2017.2824](https://doi.org/10.1287/mnsc.2017.2824)
- **OpenAlex 引用次数：** 422
- **BibTeX 键：** `Carlsson2017coordinated}`
- **与赛题关系：** 卡车+无人机协同物流的连续近似分析，适合理解服务范围与效率。
- **GB/T 7714：** John Gunnar Carlsson, Siyuan Song. Coordinated Logistics with a Truck and a Drone[J]. Management Science, 2017. DOI: 10.1287/mnsc.2017.2824.

### 6. On the min-cost Traveling Salesman Problem with Drone

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Quang Minh Ha, Yves Deville, Quang Dung Pham, Minh Hoàng Hà
- **年份 / 期刊：** 2017 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2017.11.015](https://doi.org/10.1016/j.trc.2017.11.015)
- **OpenAlex 引用次数：** 612
- **BibTeX 键：** `Ha2017min}`
- **与赛题关系：** 最小成本 TSP-D，兼顾成本与路径，对应问题2经济性。
- **GB/T 7714：** Quang Minh Ha, Yves Deville, Quang Dung Pham, et al.. On the min-cost Traveling Salesman Problem with Drone[J]. Transportation Research Part C Emerging Technologies, 2017. DOI: 10.1016/j.trc.2017.11.015.

### 7. Optimization Approaches for the Traveling Salesman Problem with Drone

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Niels Agatz, Paul Bouman, Marie Schmidt
- **年份 / 期刊：** 2018 · Transportation Science
- **DOI：** [10.1287/trsc.2017.0791](https://doi.org/10.1287/trsc.2017.0791)
- **OpenAlex 引用次数：** 19
- **BibTeX 键：** `Agatz2018optimization}`
- **与赛题关系：** TSP-D 精确/启发式优化方法综述式研究，问题1算法设计基准。
- **GB/T 7714：** Niels Agatz, Paul Bouman, Marie Schmidt. Optimization Approaches for the Traveling Salesman Problem with Drone[J]. Transportation Science, 2018. DOI: 10.1287/trsc.2017.0791.

### 8. Dynamic programming approaches for the traveling salesman problem with drone

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Paul Bouman, Niels Agatz, Marie Schmidt
- **年份 / 期刊：** 2018 · Networks
- **DOI：** [10.1002/net.21864](https://doi.org/10.1002/net.21864)
- **OpenAlex 引用次数：** 347
- **BibTeX 键：** `Bouman2018dynamic}`
- **与赛题关系：** TSP-D 动态规划精确算法。
- **GB/T 7714：** Paul Bouman, Niels Agatz, Marie Schmidt. Dynamic programming approaches for the traveling salesman problem with drone[J]. Networks, 2018. DOI: 10.1002/net.21864.

### 9. The multiple flying sidekicks traveling salesman problem: Parcel delivery with multiple drones

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Chase Murray, Ritwik Raj
- **年份 / 期刊：** 2019 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2019.11.003](https://doi.org/10.1016/j.trc.2019.11.003)
- **OpenAlex 引用次数：** 547
- **BibTeX 键：** `Murray2019multiple}`
- **与赛题关系：** 多无人机 FSTSP（mFSTSP），对应每物流点多架无人机。
- **GB/T 7714：** Chase Murray, Ritwik Raj. The multiple flying sidekicks traveling salesman problem: Parcel delivery with multiple drones[J]. Transportation Research Part C Emerging Technologies, 2019. DOI: 10.1016/j.trc.2019.11.003.

### 10. An adaptive large neighborhood search metaheuristic for the vehicle routing problem with drones

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** David Sacramento, David Pisinger, Stefan Røpke
- **年份 / 期刊：** 2019 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2019.02.018](https://doi.org/10.1016/j.trc.2019.02.018)
- **OpenAlex 引用次数：** 542
- **BibTeX 键：** `Sacramento2019adaptive}`
- **与赛题关系：** VRPD 的 ALNS 元启发式，适合中大规模算例。
- **GB/T 7714：** David Sacramento, David Pisinger, Stefan Røpke. An adaptive large neighborhood search metaheuristic for the vehicle routing problem with drones[J]. Transportation Research Part C Emerging Technologies, 2019. DOI: 10.1016/j.trc.2019.02.018.

### 11. Vehicle routing problem with drones

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Zheng Wang, Jiuh‐Biing Sheu
- **年份 / 期刊：** 2019 · Transportation Research Part B Methodological
- **DOI：** [10.1016/j.trb.2019.03.005](https://doi.org/10.1016/j.trb.2019.03.005)
- **OpenAlex 引用次数：** 535
- **BibTeX 键：** `Wang2019vehicle}`
- **与赛题关系：** VRPD 建模与求解，末端多点服务。
- **GB/T 7714：** Zheng Wang, Jiuh‐Biing Sheu. Vehicle routing problem with drones[J]. Transportation Research Part B Methodological, 2019. DOI: 10.1016/j.trb.2019.03.005.

### 12. Multiple traveling salesman problem with drones: Mathematical model and heuristic approach

- **标记：** `经典` · 卡车-无人机协同路径
- **作者：** Patchara Kitjacharoenchai, Mario Ventresca, Mohammad Moshref‐Javadi, Seokcheon Lee, J. M. A. Tanchoco, Patrick A. Brunese
- **年份 / 期刊：** 2019 · Computers & Industrial Engineering
- **DOI：** [10.1016/j.cie.2019.01.020](https://doi.org/10.1016/j.cie.2019.01.020)
- **OpenAlex 引用次数：** 396
- **BibTeX 键：** `Kitjacharoenchai2019multiple}`
- **与赛题关系：** 多旅行商+无人机，多车多机协同。
- **GB/T 7714：** Patchara Kitjacharoenchai, Mario Ventresca, Mohammad Moshref‐Javadi, et al.. Multiple traveling salesman problem with drones: Mathematical model and heuristic approach[J]. Computers & Industrial Engineering, 2019. DOI: 10.1016/j.cie.2019.01.020.

### 载重、航程与末端

### 13. Truck-drone hybrid delivery routing: Payload-energy dependency and No-Fly zones

- **标记：** `经典` · 载重、航程与末端
- **作者：** Ho Young Jeong, Byung Duk Song, Seokcheon Lee
- **年份 / 期刊：** 2019 · International Journal of Production Economics
- **DOI：** [10.1016/j.ijpe.2019.01.010](https://doi.org/10.1016/j.ijpe.2019.01.010)
- **OpenAlex 引用次数：** 342
- **BibTeX 键：** `Jeong2019truck}`
- **与赛题关系：** 载重-能耗耦合与禁飞区，对应载重分段速度与航程限制。
- **GB/T 7714：** Ho Young Jeong, Byung Duk Song, Seokcheon Lee. Truck-drone hybrid delivery routing: Payload-energy dependency and No-Fly zones[J]. International Journal of Production Economics, 2019. DOI: 10.1016/j.ijpe.2019.01.010.

### 双层网络与选址

### 14. The Two-Echelon Capacitated Vehicle Routing Problem: Models and Math-Based Heuristics

- **标记：** `经典` · 双层网络与选址
- **作者：** Guido Perboli, Roberto Tadei, Daniele Vigo
- **年份 / 期刊：** 2011 · Transportation Science
- **DOI：** [10.1287/trsc.1110.0368](https://doi.org/10.1287/trsc.1110.0368)
- **OpenAlex 引用次数：** 427
- **BibTeX 键：** `Perboli2011two}`
- **与赛题关系：** 双层容量车辆路径（2E-CVRP）经典模型，对应干线-末端两级结构。
- **GB/T 7714：** Guido Perboli, Roberto Tadei, Daniele Vigo. The Two-Echelon Capacitated Vehicle Routing Problem: Models and Math-Based Heuristics[J]. Transportation Science, 2011. DOI: 10.1287/trsc.1110.0368.

### 15. An adaptive large neighborhood search heuristic for Two-Echelon Vehicle Routing Problems arising in city logistics

- **标记：** `经典` · 双层网络与选址
- **作者：** Vera Hemmelmayr, Jean‐François Cordeau, Teodor Gabriel Crainic
- **年份 / 期刊：** 2012 · Computers & Operations Research
- **DOI：** [10.1016/j.cor.2012.04.007](https://doi.org/10.1016/j.cor.2012.04.007)
- **OpenAlex 引用次数：** 513
- **BibTeX 键：** `Hemmelmayr2012adaptive}`
- **与赛题关系：** 城市配送 2E-VRP 的 ALNS。
- **GB/T 7714：** Vera Hemmelmayr, Jean‐François Cordeau, Teodor Gabriel Crainic. An adaptive large neighborhood search heuristic for Two-Echelon Vehicle Routing Problems arising in city logistics[J]. Computers & Operations Research, 2012. DOI: 10.1016/j.cor.2012.04.007.

### 16. Two echelon vehicle routing problem with drones in last mile delivery

- **标记：** `经典` · 双层网络与选址
- **作者：** Patchara Kitjacharoenchai, Byung‐Cheol Min, Seokcheon Lee
- **年份 / 期刊：** 2019 · International Journal of Production Economics
- **DOI：** [10.1016/j.ijpe.2019.107598](https://doi.org/10.1016/j.ijpe.2019.107598)
- **OpenAlex 引用次数：** 320
- **BibTeX 键：** `Kitjacharoenchai2019two}`
- **与赛题关系：** 末端含无人机的双层 VRP，最贴近本题无人车干线+无人机末端。
- **GB/T 7714：** Patchara Kitjacharoenchai, Byung‐Cheol Min, Seokcheon Lee. Two echelon vehicle routing problem with drones in last mile delivery[J]. International Journal of Production Economics, 2019. DOI: 10.1016/j.ijpe.2019.107598.

### 17. Traveling Salesman Problem With a Drone Station

- **标记：** `经典` · 双层网络与选址
- **作者：** Sung-Woo Kim, Ilkyeong Moon
- **年份 / 期刊：** 2018 · IEEE Transactions on Systems Man and Cybernetics Systems
- **DOI：** [10.1109/tsmc.2018.2867496](https://doi.org/10.1109/tsmc.2018.2867496)
- **OpenAlex 引用次数：** 276
- **BibTeX 键：** `Kim2018traveling}`
- **与赛题关系：** 带无人机基站的 TSP，对应物流点作为起降基站。
- **GB/T 7714：** Sung-Woo Kim, Ilkyeong Moon. Traveling Salesman Problem With a Drone Station[J]. IEEE Transactions on Systems Man and Cybernetics Systems, 2018. DOI: 10.1109/tsmc.2018.2867496.

### 综述

### 18. Optimization approaches for civil applications of unmanned aerial vehicles (UAVs) or aerial drones: A survey

- **标记：** `经典` · 综述
- **作者：** Alena Otto, Niels Agatz, James F. Campbell, Bruce Golden, Erwin Pesch
- **年份 / 期刊：** 2018 · Networks
- **DOI：** [10.1002/net.21818](https://doi.org/10.1002/net.21818)
- **OpenAlex 引用次数：** 958
- **BibTeX 键：** `Otto2018optimization}`
- **与赛题关系：** 民用无人机优化问题综述。
- **GB/T 7714：** Alena Otto, Niels Agatz, James F. Campbell, et al.. Optimization approaches for civil applications of unmanned aerial vehicles (UAVs) or aerial drones: A survey[J]. Networks, 2018. DOI: 10.1002/net.21818.

### 19. Last-mile delivery concepts: a survey from an operational research perspective

- **标记：** `经典` · 综述
- **作者：** Nils Boysen, Stefan Fedtke, Stefan Schwerdfeger
- **年份 / 期刊：** 2020 · OR Spectrum
- **DOI：** [10.1007/s00291-020-00607-8](https://doi.org/10.1007/s00291-020-00607-8)
- **OpenAlex 引用次数：** 603
- **BibTeX 键：** `Boysen2020last}`
- **与赛题关系：** 末端配送概念 OR 综述，便于定位无人机/无人车在末端谱系中的位置。
- **GB/T 7714：** Nils Boysen, Stefan Fedtke, Stefan Schwerdfeger. Last-mile delivery concepts: a survey from an operational research perspective[J]. OR Spectrum, 2020. DOI: 10.1007/s00291-020-00607-8.

### 20. Drone-aided routing: A literature review

- **标记：** `经典` · 综述
- **作者：** Giusy Macrina, Luigi Di Puglia Pugliese, Francesca Guerriero, Gilbert Laporte
- **年份 / 期刊：** 2020 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2020.102762](https://doi.org/10.1016/j.trc.2020.102762)
- **OpenAlex 引用次数：** 503
- **BibTeX 键：** `Macrina2020drone}`
- **与赛题关系：** 无人机辅助路径问题文献综述。
- **GB/T 7714：** Giusy Macrina, Luigi Di Puglia Pugliese, Francesca Guerriero, et al.. Drone-aided routing: A literature review[J]. Transportation Research Part C Emerging Technologies, 2020. DOI: 10.1016/j.trc.2020.102762.

### 21. Two-echelon vehicle routing problems: A literature review

- **标记：** `经典` · 综述
- **作者：** Natasja Sluijk, Alexandre M. Florio, Joris Kinable, Nico Dellaert, Tom Van Woensel
- **年份 / 期刊：** 2022 · European Journal of Operational Research
- **DOI：** [10.1016/j.ejor.2022.02.022](https://doi.org/10.1016/j.ejor.2022.02.022)
- **OpenAlex 引用次数：** 227
- **BibTeX 键：** `Sluijk2022two}`
- **与赛题关系：** 双层车辆路径文献综述（至 2022）。
- **GB/T 7714：** Natasja Sluijk, Alexandre M. Florio, Joris Kinable, et al.. Two-echelon vehicle routing problems: A literature review[J]. European Journal of Operational Research, 2022. DOI: 10.1016/j.ejor.2022.02.022.

### 环境与能耗

### 22. Energy use and life cycle greenhouse gas emissions of drones for commercial package delivery

- **标记：** `经典` · 环境与能耗
- **作者：** Joshuah K. Stolaroff, Constantine Samaras, E. R. O'Neill, Alia Lubers, Alexandra S. Mitchell, Daniel P. Ceperley
- **年份 / 期刊：** 2018 · Nature Communications
- **DOI：** [10.1038/s41467-017-02411-5](https://doi.org/10.1038/s41467-017-02411-5)
- **OpenAlex 引用次数：** 495
- **BibTeX 键：** `Stolaroff2018energy}`
- **与赛题关系：** 商业无人机配送能耗与生命周期排放，辅助讨论问题2经济-环境权衡。
- **GB/T 7714：** Joshuah K. Stolaroff, Constantine Samaras, E. R. O'Neill, et al.. Energy use and life cycle greenhouse gas emissions of drones for commercial package delivery[J]. Nature Communications, 2018. DOI: 10.1038/s41467-017-02411-5.

### 精确算法

### 23. Exact Methods for the Traveling Salesman Problem with Drone

- **标记：** `经典` · 精确算法
- **作者：** Roberto Roberti, Mario Ruthmair
- **年份 / 期刊：** 2021 · Transportation Science
- **DOI：** [10.1287/trsc.2020.1017](https://doi.org/10.1287/trsc.2020.1017)
- **OpenAlex 引用次数：** 227
- **BibTeX 键：** `Roberti2021exact}`
- **与赛题关系：** TSP-D 精确方法，问题1可用作小规模对照。
- **GB/T 7714：** Roberto Roberti, Mario Ruthmair. Exact Methods for the Traveling Salesman Problem with Drone[J]. Transportation Science, 2021. DOI: 10.1287/trsc.2020.1017.

## 近三年文献（2024–2026）

### 协同路径与同步

### 1. Hybrid truck-drone delivery system with multi-visits and multi-launch and retrieval locations: Mathematical model and adaptive variable neighborhood search with neighborhood categorization

- **标记：** `近三年` · 协同路径与同步
- **作者：** Batool Madani, Malick Ndiaye, Saı̈d Salhi
- **年份 / 期刊：** 2024 · European Journal of Operational Research
- **DOI：** [10.1016/j.ejor.2024.02.010](https://doi.org/10.1016/j.ejor.2024.02.010)
- **OpenAlex 引用次数：** 49
- **BibTeX 键：** `Madani2024hybrid}`
- **与赛题关系：** 多访问、多起降点的混合卡车-无人机，贴近多物流点起降。
- **GB/T 7714：** Batool Madani, Malick Ndiaye, Saı̈d Salhi. Hybrid truck-drone delivery system with multi-visits and multi-launch and retrieval locations: Mathematical model and adaptive variable neighborhood search with neighborhood categorization[J]. European Journal of Operational Research, 2024. DOI: 10.1016/j.ejor.2024.02.010.

### 2. Exact and heuristic approaches for the Truck–Drone Team Logistics Problem

- **标记：** `近三年` · 协同路径与同步
- **作者：** Maurizio Boccia, Andrea Mancuso, Adriano Masone, Claudio Sterle
- **年份 / 期刊：** 2024 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2024.104691](https://doi.org/10.1016/j.trc.2024.104691)
- **OpenAlex 引用次数：** 38
- **BibTeX 键：** `Boccia2024exact}`
- **与赛题关系：** Truck–Drone Team Logistics 精确与启发式。
- **GB/T 7714：** Maurizio Boccia, Andrea Mancuso, Adriano Masone, et al.. Exact and heuristic approaches for the Truck–Drone Team Logistics Problem[J]. Transportation Research Part C Emerging Technologies, 2024. DOI: 10.1016/j.trc.2024.104691.

### 3. Dynamic vehicle routing problem with drone resupply for same-day delivery

- **标记：** `近三年` · 协同路径与同步
- **作者：** Juan C. Pina-Pardo, Daniel F. Silva, Alice E. Smith, Ricardo A. Gatica
- **年份 / 期刊：** 2024 · Transportation Research Part C Emerging Technologies
- **DOI：** [10.1016/j.trc.2024.104611](https://doi.org/10.1016/j.trc.2024.104611)
- **OpenAlex 引用次数：** 37
- **BibTeX 键：** `PinaPardo2024dynamic}`
- **与赛题关系：** 当日达场景下无人机补给的动态 VRP，对应批次与动态调度。
- **GB/T 7714：** Juan C. Pina-Pardo, Daniel F. Silva, Alice E. Smith, et al.. Dynamic vehicle routing problem with drone resupply for same-day delivery[J]. Transportation Research Part C Emerging Technologies, 2024. DOI: 10.1016/j.trc.2024.104611.

### 4. Dynamic collaborative truck-drone delivery with en-route synchronization and random requests

- **标记：** `近三年` · 协同路径与同步
- **作者：** Haipeng Cui, Keyu Li, Shuai Jia, Qiang Meng
- **年份 / 期刊：** 2024 · Transportation Research Part E Logistics and Transportation Review
- **DOI：** [10.1016/j.tre.2024.103802](https://doi.org/10.1016/j.tre.2024.103802)
- **OpenAlex 引用次数：** 35
- **BibTeX 键：** `Cui2024dynamic}`
- **与赛题关系：** 途中同步与随机需求的动态卡车-无人机协同。
- **GB/T 7714：** Haipeng Cui, Keyu Li, Shuai Jia, et al.. Dynamic collaborative truck-drone delivery with en-route synchronization and random requests[J]. Transportation Research Part E Logistics and Transportation Review, 2024. DOI: 10.1016/j.tre.2024.103802.

### 不确定与时限

### 5. Truck–drone routing problem with stochastic demand

- **标记：** `近三年` · 不确定与时限
- **作者：** Feilong Wang, Hongqi Li, Hanxi Xiong
- **年份 / 期刊：** 2024 · European Journal of Operational Research
- **DOI：** [10.1016/j.ejor.2024.11.036](https://doi.org/10.1016/j.ejor.2024.11.036)
- **OpenAlex 引用次数：** 33
- **BibTeX 键：** `Wang2024truck}`
- **与赛题关系：** 随机需求卡车-无人机路径，对应需求波动。
- **GB/T 7714：** Feilong Wang, Hongqi Li, Hanxi Xiong. Truck–drone routing problem with stochastic demand[J]. European Journal of Operational Research, 2024. DOI: 10.1016/j.ejor.2024.11.036.

### 6. Stochastic and robust truck-and-drone routing problems with deadlines: A Benders decomposition approach

- **标记：** `近三年` · 不确定与时限
- **作者：** Menghua Deng, Yuanbo Li, Jianpeng Ding, Yanlin Zhou, Lianming Zhang
- **年份 / 期刊：** 2024 · Transportation Research Part E Logistics and Transportation Review
- **DOI：** [10.1016/j.tre.2024.103709](https://doi.org/10.1016/j.tre.2024.103709)
- **OpenAlex 引用次数：** 32
- **BibTeX 键：** `Deng2024stochastic}`
- **与赛题关系：** 带截止期的随机/鲁棒卡车-无人机，直接对应 C 类时限包裹。
- **GB/T 7714：** Menghua Deng, Yuanbo Li, Jianpeng Ding, et al.. Stochastic and robust truck-and-drone routing problems with deadlines: A Benders decomposition approach[J]. Transportation Research Part E Logistics and Transportation Review, 2024. DOI: 10.1016/j.tre.2024.103709.

### 7. Exact solution method for vehicle-and-drone cooperative delivery routing of blood products

- **标记：** `近三年` · 不确定与时限
- **作者：** Yunqiang Yin, Ling Qing, Dujuan Wang, T.C.E. Cheng, Joshua Ignatius
- **年份 / 期刊：** 2024 · Computers & Operations Research
- **DOI：** [10.1016/j.cor.2024.106559](https://doi.org/10.1016/j.cor.2024.106559)
- **OpenAlex 引用次数：** 33
- **BibTeX 键：** `Yin2024exact}`
- **与赛题关系：** 血液制品车机协同精确算法，强时限配送。
- **GB/T 7714：** Yunqiang Yin, Ling Qing, Dujuan Wang, et al.. Exact solution method for vehicle-and-drone cooperative delivery routing of blood products[J]. Computers & Operations Research, 2024. DOI: 10.1016/j.cor.2024.106559.

### 8. Hybrid truck–drone delivery under aerial traffic congestion

- **标记：** `近三年` · 不确定与时限
- **作者：** Ruifeng She, Yanfeng Ouyang
- **年份 / 期刊：** 2024 · Transportation Research Part B Methodological
- **DOI：** [10.1016/j.trb.2024.102970](https://doi.org/10.1016/j.trb.2024.102970)
- **OpenAlex 引用次数：** 40
- **BibTeX 键：** `She2024hybrid}`
- **与赛题关系：** 空域拥堵下的混合卡车-无人机，启发末端绕行与速度折减。
- **GB/T 7714：** Ruifeng She, Yanfeng Ouyang. Hybrid truck–drone delivery under aerial traffic congestion[J]. Transportation Research Part B Methodological, 2024. DOI: 10.1016/j.trb.2024.102970.

### 学习与大规模求解

### 9. Multi-agent deep reinforcement learning-based truck-drone collaborative routing with dynamic emergency response

- **标记：** `近三年` · 学习与大规模求解
- **作者：** Wenhao Peng, Dujuan Wang, Yunqiang Yin, T.C.E. Cheng
- **年份 / 期刊：** 2025 · Transportation Research Part E Logistics and Transportation Review
- **DOI：** [10.1016/j.tre.2025.103974](https://doi.org/10.1016/j.tre.2025.103974)
- **OpenAlex 引用次数：** 62
- **BibTeX 键：** `Peng2025multi}`
- **与赛题关系：** 多智能体强化学习卡车-无人机路径，适合大规模启发式。
- **GB/T 7714：** Wenhao Peng, Dujuan Wang, Yunqiang Yin, et al.. Multi-agent deep reinforcement learning-based truck-drone collaborative routing with dynamic emergency response[J]. Transportation Research Part E Logistics and Transportation Review, 2025. DOI: 10.1016/j.tre.2025.103974.

### 应急与复杂地形

### 10. Optimal decision-making of post-disaster emergency material scheduling based on helicopter–truck–drone collaboration

- **标记：** `近三年` · 应急与复杂地形
- **作者：** Yong Shi, Junhao Yang, Qian Han, Hao Song, Haixiang Guo
- **年份 / 期刊：** 2024 · Omega
- **DOI：** [10.1016/j.omega.2024.103104](https://doi.org/10.1016/j.omega.2024.103104)
- **OpenAlex 引用次数：** 62
- **BibTeX 键：** `Shi2024optimal}`
- **与赛题关系：** 灾后直升机-卡车-无人机应急调度，对应湖区/山区不可达点。
- **GB/T 7714：** Yong Shi, Junhao Yang, Qian Han, et al.. Optimal decision-making of post-disaster emergency material scheduling based on helicopter–truck–drone collaboration[J]. Omega, 2024. DOI: 10.1016/j.omega.2024.103104.

### UAV-UGV 协同

### 11. A Comprehensive Review of UAV-UGV Collaboration: Advancements and Challenges

- **标记：** `近三年` · UAV-UGV 协同
- **作者：** Isuru Munasinghe, Asanka G. Perera, Ravinesh C. Deo
- **年份 / 期刊：** 2024 · Journal of Sensor and Actuator Networks
- **DOI：** [10.3390/jsan13060081](https://doi.org/10.3390/jsan13060081)
- **OpenAlex 引用次数：** 104
- **BibTeX 键：** `Munasinghe2024comprehensive}`
- **与赛题关系：** UAV-UGV 协同综述，对应无人车+无人机两种载具。
- **GB/T 7714：** Isuru Munasinghe, Asanka G. Perera, Ravinesh C. Deo. A Comprehensive Review of UAV-UGV Collaboration: Advancements and Challenges[J]. Journal of Sensor and Actuator Networks, 2024. DOI: 10.3390/jsan13060081.

### 充电、选址与评价

### 12. Integrated truck drone delivery services with an optimal charging stations

- **标记：** `近三年` · 充电、选址与评价
- **作者：** Dev Mishra, Manoj Kumar Tiwari
- **年份 / 期刊：** 2024 · Expert Systems with Applications
- **DOI：** [10.1016/j.eswa.2024.124254](https://doi.org/10.1016/j.eswa.2024.124254)
- **OpenAlex 引用次数：** 31
- **BibTeX 键：** `Mishra2024integrated}`
- **与赛题关系：** 卡车-无人机与充电站联合优化，对应问题2充电设施配置。
- **GB/T 7714：** Dev Mishra, Manoj Kumar Tiwari. Integrated truck drone delivery services with an optimal charging stations[J]. Expert Systems with Applications, 2024. DOI: 10.1016/j.eswa.2024.124254.

### 13. The Future of Last-Mile Delivery: Lifecycle Environmental and Economic Impacts of Drone-Truck Parallel Systems

- **标记：** `近三年` · 充电、选址与评价
- **作者：** Danwen Bao, Yu Yan, Yuhan Li, Jiajun Chu
- **年份 / 期刊：** 2025 · Drones
- **DOI：** [10.3390/drones9010054](https://doi.org/10.3390/drones9010054)
- **OpenAlex 引用次数：** 41
- **BibTeX 键：** `Bao2025future}`
- **与赛题关系：** 无人机-卡车末端的全周期环境与经济影响。
- **GB/T 7714：** Danwen Bao, Yu Yan, Yuhan Li, et al.. The Future of Last-Mile Delivery: Lifecycle Environmental and Economic Impacts of Drone-Truck Parallel Systems[J]. Drones, 2025. DOI: 10.3390/drones9010054.

### 算法

### 14. A competitive heuristic algorithm for vehicle routing problems with drones

- **标记：** `近三年` · 算法
- **作者：** Xuan Ren, Aurélien Froger, Ola Jabali, Gongqian Liang
- **年份 / 期刊：** 2024 · European Journal of Operational Research
- **DOI：** [10.1016/j.ejor.2024.05.031](https://doi.org/10.1016/j.ejor.2024.05.031)
- **OpenAlex 引用次数：** 14
- **BibTeX 键：** `Ren2024competitive}`
- **与赛题关系：** VRPD 竞争性启发式，可作问题1求解器对照。
- **GB/T 7714：** Xuan Ren, Aurélien Froger, Ola Jabali, et al.. A competitive heuristic algorithm for vehicle routing problems with drones[J]. European Journal of Operational Research, 2024. DOI: 10.1016/j.ejor.2024.05.031.

## 检索说明

1. OpenAlex `title.search` 与 DOI 直查；经典条目用题面核心模型名定位。
2. 每条 DOI 再向 `https://doi.org/` 做 content negotiation 取 BibTeX。
3. 未收录无 DOI 或无法核验的条目；已剔除明显跑题与撤稿文献。
4. 正文引用请用 GB/T 7714-2015；LaTeX 可直接使用 `refs.bib`。
