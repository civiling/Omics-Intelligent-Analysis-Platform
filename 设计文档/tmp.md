# 最终平台形态建议

本平台定位为面向科研用户的单细胞与多组学智能分析平台。平台不应简单堆叠 Seurat、Scanpy、DESeq2、CellChat、SCENIC 等工具，而应围绕“数据能否分析、适合做什么分析、结果是否可靠、如何解释结果”构建完整分析闭环。

平台的核心逻辑为：

```text
用户上传数据
→ 数据格式识别
→ Metadata 检查与实验设计识别
→ 自动判定可执行分析模式
→ 运行标准化工作流
→ 输出可视化结果
→ 生成带可信度标注的分析报告
```

## 1. 平台主菜单建议

最终平台可形成以下主菜单：

1. 数据质控与可分析性评估
2. 细胞组成与注释
3. 差异表达分析
4. 富集与通路分析
5. 细胞比例变化
6. 肿瘤微环境分析
7. 细胞通讯分析
8. 轨迹与状态转变
9. 调控网络分析
10. 自动报告生成

每个主菜单下面不是固定死的，而是根据用户数据自动解锁。

## 2. 菜单自动解锁规则

1. 只有单样本：

   开放 1、2、4 的描述性部分。

2. 有 normal / tumor 但重复不足：

   开放 1、2、3 探索性、4 探索性、5 探索性。

3. 有完整多样本 metadata：

   开放 1、2、3 正式、4 正式、5 正式。

4. 有肿瘤数据：

   额外开放 6。

5. 有细胞类型注释：

   开放 7。

6. 有时间点或状态连续性：

   开放 8。

7. 有足够表达矩阵和物种数据库：

   开放 9。

**平台的关键目标不是“所有分析都能跑”，而是根据用户数据条件自动判断哪些分析可以做、哪些只能作为探索性结果、哪些不能做正式结论。**

---

# 数据接入与格式识别子系统（重要）

数据接入与格式识别子系统是平台入口，必须优先稳定。该子系统负责接收用户上传的数据，并判断其是否适合进入后续分析流程。

真实科研用户上传的数据格式一定很乱，因此第一阶段必须做该子系统。

## 1. 支持的数据格式

平台第一阶段应优先支持：

1. 10x h5
2. 10x mtx
3. csv.gz
4. tsv.gz
5. h5ad
6. rds
7. loom
8. Seurat object
9. AnnData object
10. bulk RNA-seq count matrix
11. metadata.csv

## 2. 核心功能

系统需要自动判断：

1. 自动判断 gene × cell 还是 cell × gene
2. 自动判断 raw count 还是 normalized expression
3. 自动识别人 / 鼠物种
4. 自动识别 gene symbol / Ensembl ID
5. 自动识别 sample_id
6. 检查重复基因名
7. 检查空细胞、空基因
8. 检查是否压缩文件
9. 检查文件之间是否匹配

## 3. 输出结果

数据接入完成后，平台应生成一份数据可分析性摘要：

1. 数据格式识别结果
2. 表达矩阵维度
3. 是否为 raw count
4. 是否适合差异分析
5. 是否适合细胞注释
6. 是否需要补充 metadata
7. 是否存在明显格式问题

示例输出：

> 已识别为单细胞表达矩阵，行为基因，列为细胞 barcode，数值为整数 count。当前数据可用于 QC、聚类、细胞类型注释和 marker gene 分析。由于缺少 sample-level metadata，暂不能进行正式组间差异分析。

**这个子系统决定用户能不能顺利进平台，是第一阶段必须优先建设的核心模块。**

---

# Metadata 构建与实验设计识别子系统

Metadata 构建与实验设计识别子系统用于解决科研用户常见的分组信息缺失问题。单细胞数据是否能做差异分析，不只取决于表达矩阵本身，还取决于样本分组、患者编号、批次、组织来源等实验设计信息是否完整。

这是平台区别于普通生信网页工具的核心价值。

## 1. 需要支持的 metadata 来源

系统应支持：

1. 用户手动上传 metadata
2. 平台生成 metadata 模板
3. 从文件名解析 sample_id
4. 从 GSM 编号解析 GEO 信息
5. 自动识别 normal / tumor / control / treatment
6. 识别 patient_id
7. 识别 paired design
8. 识别 batch
9. 识别 time_point
10. 识别 dose
11. 识别 tissue
12. 识别 disease_stage

## 2. Metadata 最小字段

平台应要求或辅助用户补充以下字段：

1. sample_id
2. file_name
3. condition
4. patient_id
5. batch
6. tissue
7. species
8. disease
9. time_point
10. dose
11. paired_status

其中，正式差异分析最关键的字段为：

1. sample_id
2. condition
3. patient_id
4. batch

## 3. 自动 metadata 草稿生成

系统应支持从文件名或公开数据库信息中自动推断 metadata 草稿。

例如用户上传：

```text
GSM5573466_sample1.csv.gz
GSM5573467_sample2.csv.gz
```

平台可自动生成：

```csv
sample_id,gsm_id,file_name,condition,patient_id,tissue
sample1,GSM5573466,GSM5573466_sample1.csv.gz,Normal,NGCII518,Primary_Gastric_Tissue
sample2,GSM5573467,GSM5573467_sample2.csv.gz,Tumor,NGCII518,Primary_Gastric_Tissue
```

但系统必须提示：

> 该 metadata 为平台根据文件名或公开数据库自动推断，正式分析前需要用户确认。

## 4. 实验设计识别

系统应自动识别以下实验设计：

1. 单样本分析
2. 多样本无分组分析
3. normal vs tumor
4. control vs treatment
5. paired normal / tumor
6. 多组比较
7. 时间序列
8. 剂量梯度
9. 批次设计
10. 疾病分期
11. 治疗前后比较

## 5. 平台自动判断内容

平台应该自动判断：

1. 是否可以做差异分析
2. 是否只能做探索性分析
3. 是否是配对设计
4. 是否有足够生物学重复
5. 是否需要用户补 metadata
6. 是否存在 condition
7. condition 是否至少包含两组
8. 每组是否有生物学重复
9. 是否有 patient_id
10. 是否有 batch 信息
11. 每种细胞类型中是否有足够样本数

## 6. 输出结果

输出不是简单报错，而是给用户一个明确结论：

1. 当前数据可做：单样本注释、多样本整合、探索性 normal vs tumor
2. 当前数据暂不能做：正式差异分析
3. 缺少信息：patient_id、batch、condition

示例判断：

> 当前数据包含 Normal 和 Tumor 两组，但每组生物学重复数不足，因此可进行探索性 pseudobulk 差异分析，不建议作为正式统计结论。

**Metadata 子系统是平台从“能跑脚本”升级到“能判断实验设计是否成立”的关键。**

---

# 分析模式自动判定子系统（包含结果可信度评分与质控门控子系统）（重要）

分析模式自动判定子系统负责根据用户上传数据和 metadata 自动推荐可执行分析，而不是让用户一开始就面对几十个分析选项。

该子系统应同时集成结果可信度评分和质控门控机制。

## 1. 自动判定逻辑

系统应先判断：

1. 样本数
2. 分组数
3. 每组重复数
4. 是否配对
5. 是否有细胞注释
6. 是否有肿瘤样本
7. 是否有时间点
8. 是否有 VDJ
9. 是否有空间数据

完整判定流程为：

```text
用户上传数据
→ 判断是否为表达矩阵
→ 判断是否为 raw count
→ 判断样本数量
→ 检查是否有 metadata
→ 检查是否有 condition
→ 检查每组样本数
→ 检查是否有 patient_id
→ 检查是否有 batch
→ 检查是否已有细胞类型注释
→ 推荐可执行分析模式
```

## 2. 自动推荐的分析模式

系统应自动推荐：

1. 描述性分析
2. 多样本整合分析
3. 探索性差异分析
4. 正式 pseudobulk 差异分析
5. 配对差异分析
6. 多组比较
7. 时间序列分析
8. 肿瘤微环境分析
9. 细胞通讯分析
10. 轨迹分析

## 3. 分析模式判定表

| 数据条件 | 推荐分析模式 | 结果等级 |
|---|---|---|
| 只有 1 个样本 | 单样本细胞组成分析 | 描述性分析 |
| 多个样本但无 condition | 多样本整合与细胞注释 | 描述性分析 |
| 有 condition 但只有 1 组 | 同组整合分析，不做组间差异 | 描述性分析 |
| 有 Normal/Tumor 但每组样本数不足 | 探索性 pseudobulk 差异分析 | 探索性结果 |
| Normal/Tumor 每组有多个生物学重复 | 正式 pseudobulk 差异分析 | 正式统计结果 |
| 有 patient_id 且样本成对 | 配对 pseudobulk 差异分析 | 正式统计结果 |
| condition ≥ 3 | 多组比较 / 趋势分析 | 视重复数决定 |
| 有 time_point | 时间序列分析 | 视实验设计决定 |
| 有 dose | 剂量响应分析 | 视实验设计决定 |
| 已完成细胞类型注释 | 细胞比例差异 / 细胞通讯 | 推断性结果 |
| 肿瘤数据 | 肿瘤微环境 / CNV 推断 | 推断性结果 |

## 4. 结果可信度分级

每个结果给出结论等级：

1. 描述性结果  
   单样本或无分组数据，仅描述细胞组成、marker 和通路特征。

2. 探索性结果  
   有分组但重复不足，可用于候选基因和候选通路筛选。

3. 正式统计结果  
   有完整 metadata 和足够生物学重复，可用于正式差异分析。

4. 推断性结果  
   细胞通讯、轨迹、转录因子调控、CNV 推断等基于模型或表达推断的结果。

## 5. 质控门控规则

平台不能所有结果都正常输出。系统应在关键节点自动判断是否允许继续分析：

1. 样本数是否足够
2. 细胞数是否足够
3. 每组是否有重复
4. 每个 cell type 是否满足最低细胞数
5. 线粒体比例是否异常
6. 是否存在强批次效应
7. 是否存在 doublet 风险
8. 是否存在 ambient RNA 风险
9. metadata 是否完整
10. 基因数是否异常

正式差异分析要求示例：

1. Normal ≥ 3 samples
2. Tumor ≥ 3 samples
3. 每个 cell type 每组至少 ≥ 2 或 ≥ 3 个样本有足够细胞数

## 6. 自动降级规则

如果不满足正式分析条件，系统应自动降级：

```text
正式差异分析 → 探索性差异分析
探索性差异分析 → 仅做描述性分析
```

示例提示语：

> 当前数据包含 Normal 和 Tumor 两组，但每组生物学重复数不足。平台将运行探索性 pseudobulk 差异分析，结果仅用于候选基因和通路筛选，不建议作为正式统计结论。

> 当前数据只有单个样本，平台将进行 QC、聚类、细胞类型注释、marker gene 和细胞组成分析，不进行组间差异分析。

**这个“自动降级”功能很重要，能避免平台生成误导性结论。**

---

# 标准数据对象管理子系统

标准数据对象管理子系统用于统一不同分析模块之间的数据结构，避免后端变成多个脚本和多个格式的混乱拼接。

后端不能每个工具各用各的格式，否则后期维护会崩。

## 1. 核心数据对象

建议把所有分析结果抽象成标准对象：

1. ExpressionMatrix
2. CellMetadata
3. SampleMetadata
4. QCResult
5. NormalizedMatrix
6. DimReductionResult
7. ClusterResult
8. CellTypeAnnotation
9. MarkerGeneResult
10. PseudobulkMatrix
11. DEGResult
12. RankedGeneList
13. GeneSet
14. EnrichmentResult
15. PathwayScoreMatrix
16. CellProportionResult
17. CommunicationResult
18. TrajectoryResult
19. RegulonResult
20. ReportObject

## 2. 对象流转示例

### 2.1 单样本分析

```text
ExpressionMatrix
→ QCResult
→ NormalizedMatrix
→ DimReductionResult
→ ClusterResult
→ MarkerGeneResult
→ CellTypeAnnotation
→ ReportObject
```

### 2.2 正式差异分析

```text
ExpressionMatrix + SampleMetadata + CellTypeAnnotation
→ PseudobulkMatrix
→ DEGResult
→ RankedGeneList
→ EnrichmentResult
→ ReportObject
```

### 2.3 通路分析

```text
ExpressionMatrix + GeneSet
→ PathwayScoreMatrix
→ CellType-specific Pathway Comparison
→ ReportObject
```

### 2.4 细胞通讯分析

```text
ExpressionMatrix + CellTypeAnnotation
→ CommunicationResult
→ Communication Pathway Result
→ ReportObject
```

## 3. 设计意义

标准对象的好处是：

1. 差异分析结果可以接 GO/KEGG/GSEA
2. marker gene 结果可以接富集分析
3. 细胞注释结果可以接细胞通讯
4. pseudobulk 矩阵可以接正式通路比较
5. 所有结果都可以进入报告系统

**这是平台可扩展性的基础。没有统一对象，后续功能越多，维护成本越高。**

---

# Workflow Runtime 工作流执行子系统（重要）

Workflow Runtime 工作流执行子系统负责管理分析任务的运行、状态、日志、结果和失败重试。

后面功能变多后，不能靠前端直接调用脚本。需要一个工作流引擎统一负责任务创建、排队、运行、追踪、缓存和版本记录。

## 1. 推荐架构

建议采用如下结构：

```text
前端
→ 后端 API
→ Task Queue
→ Worker
→ Docker/Singularity 分析容器
→ Result Store
→ Report Engine
```

也可以扩展为：

```text
前端页面
→ 后端 API
→ 任务队列
→ Workflow Runtime
→ Worker
→ Docker / Conda / Singularity 分析环境
→ 结果存储
→ 报告生成
```

## 2. 核心功能

工作流引擎负责：

1. 任务创建
2. 任务排队
3. 任务状态追踪
4. 失败重试
5. 日志保存
6. 参数记录
7. 中间结果缓存
8. 断点续跑
9. 资源限制
10. 运行版本记录
11. 容器化运行
12. 结果归档

## 3. 任务状态

任务状态至少包括：

1. pending
2. queued
3. running
4. failed
5. completed
6. cancelled

## 4. 每个任务需要保存的信息

每个任务要保存：

1. 任务 ID
2. 项目 ID
3. 用户 ID
4. 输入文件
5. 运行参数
6. 分析模式
7. 软件版本
8. 数据库版本
9. 开始时间
10. 结束时间
11. 运行日志
12. 中间结果路径
13. 输出结果路径
14. 错误信息
15. 是否允许重跑

## 5. 工作流示例

### 5.1 单细胞基础分析工作流

```text
InputMatrix
→ FormatCheck
→ QC
→ FilterCells
→ Normalize
→ PCA
→ UMAP
→ Clustering
→ MarkerDetection
→ CellTypeAnnotation
→ Visualization
→ Report
```

### 5.2 pseudobulk 差异分析工作流

```text
InputMatrix + Metadata + CellTypeAnnotation
→ CellType Split
→ Sample-level Count Aggregation
→ PseudobulkMatrix
→ DESeq2 / edgeR
→ DEGResult
→ GO/KEGG/GSEA
→ Visualization
→ Report
```

**这一步决定平台能不能从 demo 变成实际可用系统。**

---

# 参考数据库与知识库子系统

参考数据库与知识库子系统用于支撑细胞注释、通路富集、细胞通讯、转录因子调控、肿瘤分析和自动解释。

做细胞注释、富集、通路、肿瘤分析时，必须有稳定数据库。

## 1. 第一阶段应接入的数据库

第一阶段建议管理：

1. Gene annotation database
2. GO
3. KEGG
4. Reactome
5. MSigDB Hallmark
6. marker gene database
7. Cell marker database
8. PanglaoDB
9. CellMarker
10. Azimuth reference
11. Human Protein Atlas
12. GEO dataset metadata

## 2. 第二阶段可扩展数据库

后续可扩展：

1. cell type reference atlas
2. CellChatDB
3. CellPhoneDB ligand-receptor database
4. DoRothEA TF-target database
5. SCENIC motif database
6. PROGENy pathway database
7. TCGA / GTEx reference
8. COSMIC
9. OncoKB
10. ImmPort

## 3. 数据库版本管理

每个数据库都需要记录：

1. 数据库名称
2. 版本号
3. 物种
4. 更新时间
5. 来源链接
6. 适用分析模块
7. 引用信息
8. 本地路径
9. 是否启用

## 4. 知识库作用

该子系统支持：

1. 细胞类型 marker 证据
2. GO/KEGG/Reactome 富集
3. Hallmark pathway analysis
4. 肿瘤相关通路解释
5. ligand-receptor 细胞通讯推断
6. TF-target 调控网络分析
7. 文献证据检索
8. 报告自动解释

**数据库版本必须可追溯，否则同一数据今天跑和半年后跑，结果可能不一致。正式科研报告必须有数据库版本追踪。**

---

# 细胞类型自动注释与人工复核子系统

细胞类型注释是单细胞分析中的核心环节，也是最容易出错的环节。平台不应只给出自动注释结果，还应提供 marker 证据和人工复核入口。

细胞注释不能只靠一个算法，建议做三层：

1. 自动注释
2. marker gene 证据
3. 人工复核

## 1. 自动注释方法

第一阶段可支持：

1. marker-based annotation
2. SingleR
3. Azimuth
4. CellTypist
5. scType

后续可加入：

1. LLM-assisted annotation
2. reference atlas mapping
3. custom marker panel annotation

## 2. 注释结果应包含

注释结果应包含：

1. cluster ID
2. predicted cell type
3. confidence score
4. positive marker genes
5. negative marker genes
6. reference database
7. annotation method
8. manual review status

## 3. 注释证据展示

报告中不能只写“系统注释为 T cell”，而应显示证据。

示例：

```text
Cluster 3
Predicted cell type: T cell
Supporting markers: CD3D, CD3E, TRAC
Negative markers: EPCAM, COL1A1, PECAM1
Confidence: High
Reference: CellMarker / PanglaoDB
```

## 4. 人工复核功能

平台应允许用户：

1. 修改 cluster 注释
2. 合并相似 cluster
3. 拆分细胞大类和亚型
4. 上传自定义 marker
5. 标记低置信度注释
6. 保留修改历史

示例：

1. cluster 3 从 T cell 改为 CD8 T cell
2. cluster 7 从 Fibroblast 改为 CAF

## 5. 与后续分析的关系

细胞类型注释结果会影响：

1. 细胞组成分析
2. 细胞比例差异分析
3. cell-type-specific DEG
4. pseudobulk 差异分析
5. 通路分析
6. 细胞通讯分析
7. 肿瘤微环境分析

**细胞注释必须可解释、可复核、可修改，否则后续差异分析和通路解释都可能建立在错误分类上。**

---

# 前端页面：包含可视化子系统、自动报告与解释生成子系统、文献证据与 RAG 解释子系统（重要）

前端页面不仅是结果展示界面，还应承担数据上传、metadata 检查、分析模式推荐、结果可视化、报告生成和证据解释的功能。

前端不应只是展示图表，而应帮助用户理解“这个结果能说明什么、不能说明什么、可信度如何、下一步该怎么做”。

## 1. 前端主菜单建议

建议主菜单包括：

1. 首页 / 项目概览
2. 数据上传与格式识别
3. Metadata 构建与实验设计
4. 数据质控
5. 细胞聚类与注释
6. 细胞组成分析
7. 差异表达分析
8. 富集与通路分析
9. 细胞比例变化
10. 肿瘤微环境分析
11. 细胞通讯分析
12. 轨迹与状态转变
13. 调控网络分析
14. 报告生成

第一阶段可以先上线：

1. 数据上传与格式识别
2. Metadata 构建
3. 数据质控
4. 细胞聚类与注释
5. 细胞组成分析
6. 差异表达分析
7. 富集与通路分析
8. 报告生成

## 2. 可视化子系统

科研用户需要的不只是表格。科研用户最终要写文章、做 PPT、做报告，图的导出质量很关键。

### 2.1 基础图

基础图包括：

1. QC violin plot
2. UMAP
3. tSNE
4. cluster plot
5. cell type plot
6. sample split UMAP
7. marker gene feature plot
8. dot plot
9. violin plot
10. heatmap
11. cell proportion barplot
12. volcano plot
13. MA plot
14. GSEA enrichment plot
15. GO/KEGG bubble plot
16. pathway heatmap

### 2.2 高级图

高级图包括：

1. cell-cell communication network
2. ligand-receptor chord plot
3. trajectory plot
4. pseudotime heatmap
5. CNV heatmap
6. regulon activity heatmap
7. spatial feature plot

### 2.3 可视化功能要求

可视化系统要支持：

1. 交互式查看
2. 导出 PNG/PDF/SVG
3. 调整分组
4. 调整颜色
5. 选择基因
6. 选择 cell type
7. 选择对比组
8. 支持图表进入报告

## 3. 自动报告与解释生成子系统

报告不要只是把图贴出来，而要分层。

报告应包括：

1. 数据概况
2. 质控结果
3. metadata 与实验设计
4. 分析模式判定
5. 分析流程
6. 细胞聚类结果
7. 细胞类型注释结果
8. 细胞类型组成
9. 主要 marker
10. 差异分析结果
11. 通路分析结果
12. 关键发现
13. 局限性
14. 后续实验建议
15. 方法学说明
16. 参数与软件版本
17. 数据库版本
18. 结果可信度说明

## 4. 报告类型

报告可以分三种：

1. 简版报告：给普通用户快速看
2. 标准科研报告：给课题组内部汇报
3. 方法学报告：给文章方法部分或项目归档

## 5. 报告中的证据绑定

每个结论都要绑定证据：

1. 结论
2. 对应图表
3. 对应统计表
4. 对应参数
5. 对应数据库
6. 可信度等级

报告中每个结论应带有结果等级：

1. 描述性结果
2. 探索性结果
3. 正式统计结果
4. 推断性结果

示例：

> 该样本中识别到上皮细胞、T 细胞、B 细胞、浆细胞、巨噬细胞、成纤维细胞和内皮细胞等主要细胞群。该结果属于描述性结果。

> Tumor 组上皮细胞中细胞周期相关基因呈上调趋势。由于当前样本重复数有限，该结果属于探索性结果。

> 在 cell-type-specific pseudobulk 差异分析基础上，Tumor epithelial cells 中 DNA replication 和 E2F targets 通路显著富集。该结果属于正式统计结果。

**报告系统是平台商业化和交付感最强的模块。**

## 6. 文献证据与 RAG 解释子系统

后续可以加入文献解释，但要谨慎。

RAG 子系统用于将分析结果与文献证据、数据库注释和生物学背景连接起来，但必须区分数据结果、文献事实和平台推断。

适合做：

1. marker gene 文献解释
2. 通路生物学解释
3. 肿瘤微环境解释
4. 候选基因功能注释
5. 正常/肿瘤差异的文献证据
6. 细胞类型功能解释
7. DEG 生物学解释
8. GO/KEGG/Reactome 通路解释
9. 细胞通讯解释
10. 后续实验建议

报告必须区分：

1. 数据中观察到的结果
2. 文献中已有的解释
3. 平台推断的可能机制

示例：

```text
数据结果：Tumor epithelial cells 中 EPCAM+ 细胞显示 cell cycle pathway 增强。
文献证据：胃癌细胞增殖常伴随 E2F/MYC 相关基因集增强。
平台解释：该结果提示肿瘤上皮细胞可能存在增殖活跃状态。
```

不能把推断写成事实。

**RAG 子系统可以显著提高报告质量，但必须做证据边界控制。**

## 7. 前端结果组织方式

建议每个分析页面包含：

1. 分析状态
2. 输入数据摘要
3. 分析参数
4. 核心图表
5. 核心表格
6. 结果解释
7. 可信度标签
8. 下载入口
9. 加入报告按钮

---

# 阶段建设建议

## Phase 1：单细胞 RNA-seq 基础闭环

目标：能稳定分析用户上传的表达矩阵，并生成可靠报告。

建设内容：

1. 数据上传
2. 格式识别
3. metadata 模板
4. QC
5. 过滤
6. 归一化
7. PCA / UMAP
8. 聚类
9. 注释
10. marker
11. 细胞组成
12. pseudobulk DEG
13. GO/KEGG/GSEA
14. 自动报告

不急着做：

1. SCENIC
2. 空间转录组
3. TCR/BCR
4. 多组学
5. 复杂细胞通讯

第一阶段最小闭环可以是：

```text
上传表达矩阵
→ 自动识别格式
→ 质控
→ 聚类
→ 细胞类型注释
→ marker gene
→ 细胞组成
→ metadata 检查
→ 可选 pseudobulk 差异分析
→ GO/KEGG/GSEA 富集
→ 自动报告
```

## Phase 2：数据质量与正式统计能力增强

目标：让结果更可靠。

建设内容：

1. doublet 检测
2. ambient RNA 校正
3. 批次效应诊断
4. 多样本整合方法选择
5. 细胞类型注释置信度评分
6. 用户自定义 marker 注释
7. paired design
8. 多组比较
9. 时间/剂量设计
10. 细胞比例差异统计
11. 差异分析可信度评分
12. cell-type-specific DEG
13. cell-type-specific pathway activity
14. 用户指定基因/基因集分析

这些功能比轨迹、SCENIC 更应该先做，因为它们是日常需求。

## Phase 3：肿瘤单细胞专用模块

目标：形成特色场景。

如果用户中有大量肿瘤研究者，建议第三阶段重点做肿瘤模块。

建设内容：

1. 恶性细胞识别
2. inferCNV / CopyKAT
3. CNV 推断
4. 肿瘤上皮细胞亚群分析
5. 肿瘤微环境组成分析
6. TME 分析
7. T cell exhaustion score
8. cytotoxicity score
9. macrophage subtype / inflammation score
10. macrophage state
11. CAF subtype
12. angiogenesis score
13. immune checkpoint expression
14. antigen presentation score
15. tumor-normal epithelial comparison

这类模块对胃癌、肺癌、肝癌、乳腺癌、结直肠癌等数据都很有价值。

肿瘤模块可以作为平台的第一个“专病分析模板”。

## Phase 4：机制解释模块

目标：从“结果展示”升级到“机制提示”。

建设内容：

1. 细胞通讯分析
2. 轨迹分析
3. 通路活性比较
4. pseudotime-associated genes
5. pseudotime pathway score
6. TF regulon analysis
7. DoRothEA / PROGENy
8. NicheNet ligand-target 推断
9. ligand-target 推断
10. 候选机制摘要

### 细胞通讯

可支持：

1. CellChat
2. CellPhoneDB
3. LIANA
4. NicheNet
5. normal vs tumor communication comparison
6. ligand-receptor evidence table
7. communication pathway visualization

### 轨迹分析

可支持：

1. Monocle3
2. Slingshot
3. PAGA
4. pseudotime genes
5. branch-specific genes
6. pseudotime pathway score

平台要提示：

1. 细胞通讯是基于表达的推断
2. pseudotime 是状态连续性推断，不等同于真实时间

这两个模块的结果解释难度高，最好配合自动报告和证据边界提示一起上线。

## Phase 5：调控网络与高级机制分析

包括：

1. SCENIC / pySCENIC
2. DoRothEA
3. PROGENy
4. VIPER
5. TF regulon activity
6. transcription factor-target network
7. upstream regulator inference

这类功能适合机制研究，但计算重，数据库依赖强，结果解释门槛高。

建议作为高级模块，不要放在最初版本。

## Phase 6：跨组学整合

后续如果要从“单细胞平台”扩展成“多组学智能分析基座”，需要加入：

1. bulk RNA-seq
2. single-cell RNA-seq
3. spatial transcriptomics
4. scATAC-seq
5. CITE-seq
6. TCR/BCR-seq
7. metagenomics
8. metabolomics
9. proteomics

对应功能：

1. bulk DEG + scRNA cell type mapping
2. bulk deconvolution
3. spatial cell type mapping
4. spatial niche analysis
5. RNA-ATAC integration
6. TCR clonotype expansion
7. microbiome-host correlation
8. metabolite-pathway-gene integration
9. multi-omics report generation

这一步是平台长期方向，不建议第一阶段同时做。

---

# 后续最值得优先做的功能清单

如果按投入产出比排序，建议优先级如下：

| 优先级 | 子系统/功能 | 原因 |
|---|---|---|
| P0 | 数据格式识别 | 没有它用户数据进不来 |
| P0 | metadata 构建 | 决定能不能差异分析 |
| P0 | QC + 聚类 + 注释 | 单细胞基础闭环 |
| P0 | 自动报告 | 提升交付价值 |
| P1 | pseudobulk DEG | 正式差异分析核心 |
| P1 | GO/KEGG/GSEA | 科研用户高频需求 |
| P1 | 细胞比例差异 | 肿瘤/免疫数据常用 |
| P1 | 结果可信度评级 | 防止误导用户 |
| P2 | 肿瘤微环境模块 | 适合形成特色 |
| P2 | CNV 推断 | 肿瘤 scRNA 很有价值 |
| P2 | 细胞通讯 | 高频但解释复杂 |
| P3 | 轨迹分析 | 适合分化/状态转变 |
| P3 | SCENIC/TF regulon | 高级机制分析 |
| P4 | 空间/多组学 | 长期扩展 |

---

# 平台最终应该形成的能力

最终不是做一个“Seurat 网页版”，而是做一个“根据数据条件自动判断能做什么、不能做什么，并生成带证据边界报告的智能分析平台”。

成熟后应该具备四层能力：

1. 第一层：数据能不能用
2. 第二层：能做哪些分析
3. 第三层：结果是否可靠
4. 第四层：这些结果在生物学上如何解释

**这比单纯堆工具更有价值。**

所以，前面那套菜单能覆盖多数科研用户的常规单细胞需求；后续继续启动时，优先补“数据接入、metadata、工作流、标准对象、质控门控、报告、知识库”这些平台子系统，再逐步加入肿瘤、通讯、轨迹、调控网络和多组学模块。

---

# 暂不建设内容

本阶段暂不建设项目管理、权限和审计子系统。

暂不包含：

1. 用户管理
2. 项目管理
3. 样本管理
4. 文件管理
5. 任务管理
6. 结果归档
7. 权限控制
8. 数据删除
9. 下载管理
10. 审计日志
11. 项目级权限隔离
12. 团队协作
13. 操作历史追踪
14. 企业级数据安全策略

科研平台后续如果进入多人使用、对外服务或商业化部署阶段，应重新纳入该子系统。

后续需要重点记录：

1. 谁上传了数据
2. 谁运行了分析
3. 谁修改了 metadata
4. 谁修改了细胞注释
5. 谁下载了报告
6. 什么时候运行的
7. 用了哪个版本流程

这不是第一天就必须做满，但系统设计时要预留。