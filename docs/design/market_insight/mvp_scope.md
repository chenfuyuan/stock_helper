# Market Insight (MVP) - 实施规划

## 1. 目标 (Objective)
为了快速验证 **市场洞察 (Market Insight)** 模块的价值，构建一个 **"数据获取 -> 基础计算 -> 每日摘要"** 的最小闭环 (MVP)。

- **核心回答**: "今天什么板块强？" 和 "哪些票涨停了？"
- **交付物**: 每日收盘后自动生成的 Markdown 复盘日报。

## 2. 核心功能范围 (Scope)

### 2.1 数据层 (Data Layer)
- **ConceptFetcher**: 
  - Source: AkShare
  - Job: 获取所有概念板块列表及其成分股（每日更新，处理新概念/剔除旧概念）。
- **MarketDataFetcher**: 
  - Source: TuShare
  - Job: 获取全市场个股当日量价数据 (OHLCV, Limit Status)。

### 2.2 计算层 (Analysis Layer)
- **板块热度计算**: 
  - 算法: **等权平均 (Equal Weighted)**。单纯计算板块内所有成分股的涨跌幅平均值。
  - 目的: 快速反映板块赚钱效应，不引入复杂加权。
- **涨停扫描 (Limit Limit Scanner)**: 
  - 算法: 识别当日涨停个股 (Close == LimitUpPrice)。
  - 关联: 将涨停股映射回所属概念。

### 2.3 输出层 (Presentation Layer)
- **Report Generator**:
  - Format: Markdown File (`YYYY-MM-DD-market-insight.md`)
  - Sections:
    1.  **Top 10 强势概念**: 按板块涨幅排序。
    2.  **今日涨停天梯**: 
        - 按概念分组展示涨停股。
        - (MVP 暂不区分首板/连板，或者仅做简单标注)。

## 3. 暂不包含 (Out of Scope)
- 连板梯队图 (Space Ladder) - 需要历史连板数据。
- 情绪周期指标 (炸板率、晋级率)。
- 复杂的龙头战法识别。
- Web/GUI 界面。

## 4. 实施步骤 (Roadmap)
1.  **Infra Setup**: 建立 AkShare/TuShare 数据获取适配器。
2.  **Domain Logic**: 实现 `ConceptService` (聚合计算) 和 `StockService` (涨停识别)。
3.  **Application**: 编写 `DailyReviewJob` 串联流程。
4.  **Integration**: 验证生成结果并调整格式。
