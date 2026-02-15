请分析以下概念列表中的产业链关系：

## 概念列表
{concepts_list}

## 分析要求
1. 识别概念间的产业链关联关系
2. 只使用允许的关系类型：IS_UPSTREAM_OF、IS_DOWNSTREAM_OF、COMPETES_WITH、IS_PART_OF、ENABLER_FOR
3. 为每个关系评估置信度（0.0-1.0）
4. 提供清晰的推理依据

## 输出格式
请严格按照以下 JSON 格式输出，不要包含任何额外文字：
{{
  "relations": [
    {{
      "source": "源概念代码",
      "target": "目标概念代码",
      "type": "关系类型",
      "confidence": 置信度,
      "reasoning": "推理说明"
    }}
  ]
}}

## 注意事项
- 只分析提供的概念，不要引入外部概念
- 每个关系都要有明确的产业逻辑
- 置信度要反映关系的不确定性程度
- 推理说明要简洁但充分
