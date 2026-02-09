# LLM 平台模块

`llm_platform` 模块为与各种大语言模型 (LLM) 交互提供统一接口。它抽象了不同提供商（OpenAI、Anthropic 等）之间的差异，并允许进行动态配置管理。

## 核心概念

### LLM 配置 (`LLMConfig`)
一个领域实体，存储连接 LLM 所需的所有详细信息。
- **属性**: `alias` (别名), `vendor` (厂商), `provider_type` (提供商类型), `api_key` (API 密钥), `model_name` (模型名称), `base_url` (基础 URL), `priority` (优先级)。
- **源码**: `domain/entities/llm_config.py`

### LLM 注册表 (`LLMRegistry`)
一个单例服务，维护一组活跃的 LLM 配置。
- **功能**: 启动时从数据库加载配置，并允许运行时刷新。
- **源码**: `infrastructure/registry.py`

### 适配器 (Adapters)
该模块使用适配器模式来支持不同的 LLM 提供商。
- **基础适配器 (Base Adapter)**: 定义了文本生成和嵌入的标准接口。
- **具体实现**: `infrastructure/adapters/openai.py` 等。

## 使用方法

### 管理配置
配置存储在数据库（`llm_configs` 表）中。可以通过以下方式管理：
1.  **REST API**: `POST /api/v1/llm/configs`
2.  **脚本**: `scripts/add_llm_config_template.py`

### 调用 LLM
其他模块不应直接实例化 LLM 客户端。相反，它们应该从 `LLMRegistry` 请求 LLM 服务或客户端，或者使用 `LLMService` 应用服务。

```python
# 使用示例 (概念性)
llm_service = LLMService(registry)
response = await llm_service.chat(
    alias="deepseek-v3",
    messages=[{"role": "user", "content": "你好"}]
)
```
