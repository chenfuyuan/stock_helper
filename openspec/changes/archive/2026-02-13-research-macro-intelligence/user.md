# 宏观环境分析任务: {stock_name} ({third_code})
**当前日期**: {current_date}
**所属行业**: {industry}

---

## 第一部分：货币与流动性环境 (Monetary & Liquidity)
*以下为 Web 搜索获取的近期货币政策与流动性相关情报：*

{monetary_context}

---

## 第二部分：产业政策与监管动态 (Industry Policy & Regulation)
*以下为 Web 搜索获取的"{industry}"行业相关产业政策与监管动态情报：*

{policy_context}

---

## 第三部分：宏观经济周期定位 (Macro Economic Cycle)
*以下为 Web 搜索获取的近期宏观经济数据与周期定位情报：*

{economic_context}

---

## 第四部分：行业景气与资金流向 (Industry Sentiment & Capital Flows)
*以下为 Web 搜索获取的"{industry}"行业景气度与市场趋势情报：*

{industry_context}

---

## 信息来源汇总 (Information Sources)
*以下为上述搜索情报涉及的所有信息来源 URL，供你在 information_sources 字段中引用：*

{all_source_urls}

---

## 任务指令
请基于上述四个维度的搜索情报（且仅基于上述情报），对 **{stock_name}**（所属行业：{industry}）所处的宏观环境进行系统性评估：
1. **逐维度分析**：针对四个维度分别给出评分 (0-100) 和关键发现，须引用搜索情报中的具体内容。
2. **综合判定**：基于四维评估，判定宏观环境为 Favorable (有利) / Neutral (中性) / Unfavorable (不利)。
3. **机会与风险**：识别宏观层面的主要机会和风险。
4. **来源标注**：在 information_sources 中列出你引用信息的来源 URL。
5. **输出**：直接输出 JSON 字符串。
