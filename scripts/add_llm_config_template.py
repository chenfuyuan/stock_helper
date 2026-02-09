import requests
import json
import os

# 配置
API_BASE_URL = "http://localhost:8000/api/v1/llm-platform/configs"
SILICONFLOW_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx" # 替换为您的 API Key

def add_siliconflow_model():
    """
    添加硅基流动 (SiliconFlow) 的 DeepSeek-V3 模型配置
    """
    
    # 1. 定义配置数据 (Template)
    config_data = {
        "alias": "deepseek-v3",
        "vendor": "SiliconFlow",
        "provider_type": "openai",  # 硅基流动兼容 OpenAI 接口
        "api_key": SILICONFLOW_API_KEY,
        "base_url": "https://api.siliconflow.cn/v1",
        "model_name": "deepseek-ai/DeepSeek-V3",
        "description": "硅基流动提供的 DeepSeek-V3 模型，高性能通用大模型",
        "priority": 10,  # 优先级，数字越大优先级越高
        "tags": ["fast", "economy", "general"], # 标签，用于路由选择
        "is_active": True
    }

    print(f"Adding config for {config_data['alias']}...")
    print(json.dumps(config_data, indent=2))

    # 2. 发送 POST 请求
    try:
        response = requests.post(API_BASE_URL, json=config_data)
        
        # 3. 处理响应
        if response.status_code == 201:
            print("\n✅ Successfully added configuration!")
            print("Response:", json.dumps(response.json(), indent=2))
        elif response.status_code == 409:
            print(f"\n⚠️ Configuration with alias '{config_data['alias']}' already exists.")
        else:
            print(f"\n❌ Failed to add configuration. Status Code: {response.status_code}")
            print("Error:", response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to {API_BASE_URL}. Is the server running?")

if __name__ == "__main__":
    add_siliconflow_model()
