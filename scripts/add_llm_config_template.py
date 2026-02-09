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

    send_request(config_data)

def add_qwen_model():
    """
    添加硅基流动 (SiliconFlow) 的 Qwen/Qwen3-8B 模型配置
    """
    config_data = {
        "alias": "qwen-3-8b",
        "vendor": "SiliconFlow",
        "provider_type": "openai",
        "api_key": SILICONFLOW_API_KEY,
        "base_url": "https://api.siliconflow.cn/v1",
        "model_name": "Qwen/Qwen3-8B", 
        "description": "通义千问 Qwen3 8B 模型",
        "priority": 5,
        "tags": ["fast", "chinese", "qwen"],
        "is_active": True
    }

    send_request(config_data)

def send_request(config_data):
    print(f"Adding config for {config_data['alias']}...")
    try:
        response = requests.post(API_BASE_URL, json=config_data)
        if response.status_code == 201:
            print(f"✅ Successfully added {config_data['alias']}!")
        elif response.status_code == 409:
            # Try to update if it exists (optional, or just log it)
            # For now, just say it exists.
            # Or better, we could implement update logic, but let's stick to simple add.
            print(f"⚠️ {config_data['alias']} already exists.")
        else:
            print(f"❌ Failed. Status: {response.status_code}, Error: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")

if __name__ == "__main__":
    # 您可以选择运行哪一个
    add_siliconflow_model()
    add_qwen_model() # 取消注释以添加 Qwen 模型
