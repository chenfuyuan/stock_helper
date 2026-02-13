# 催化剂事件扫描任务: {stock_name} ({third_code})
**当前日期**: {current_date}
**所属行业**: {industry}

---

## 第一部分：公司重大事件与动态 (Company Events & Developments)
*以下为 Web 搜索获取的"{stock_name}"近期公司重大事件与动态相关情报：*

{company_events_context}

---

## 第二部分：行业催化与竞争格局 (Industry Catalysts & Competitive Dynamics)
*以下为 Web 搜索获取的"{stock_name}"所处"{industry}"行业催化事件与竞争格局相关情报：*

{industry_catalyst_context}

---

## 第三部分：市场情绪与机构动向 (Market Sentiment & Institutional Activity)
*以下为 Web 搜索获取的"{stock_name}"市场情绪、机构评级与资金动向相关情报：*

{market_sentiment_context}

---

## 第四部分：财报预期与业绩催化 (Earnings Expectations & Performance Catalysts)
*以下为 Web 搜索获取的"{stock_name}"业绩预期、财报动态与订单合同相关情报：*

{earnings_context}

---

## 信息来源汇总 (Information Sources)
*以下为上述搜索情报涉及的所有信息来源 URL，供你在 information_sources 字段中引用：*

{all_source_urls}

---

## 任务指令
请基于上述四个维度的搜索情报（且仅基于上述情报），对 **{stock_name}**（所属行业：{industry}）的催化事件进行系统性扫描与评估：
1. **逐维度分析**：针对四个维度分别给出评分 (0-100) 和关键发现，须引用搜索情报中的具体内容。
2. **综合判定**：基于四维评估，判定催化事件整体方向为 Positive (正面催化) / Neutral (中性) / Negative (负面催化)。
3. **催化事件提炼**：分别列出正面催化事件和负面催化事件（风险），每项标注预期影响、时间线和触发概率。
4. **来源标注**：在 information_sources 中列出你引用信息的来源 URL。
5. **输出**：直接输出 JSON 字符串。
