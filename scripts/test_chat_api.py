import requests
import json

API_URL = "http://localhost:8000/api/v1/llm-platform/chat/generate"


def test_chat(alias=None, tags=None, prompt="你好，请介绍你自己"):
    payload = {"prompt": prompt, "temperature": 0.7}
    if alias:
        payload["alias"] = alias
    if tags:
        payload["tags"] = tags

    print(f"\nTesting with alias={alias}, tags={tags}...")
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print("✅ Success!")
            print(f"Response: {response.json()['response']}")
        else:
            print(f"❌ Failed. Status: {response.status_code}")
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")


if __name__ == "__main__":
    # Test 1: Specific alias (DeepSeek)
    test_chat(alias="deepseek-v3", prompt="你是谁？")

    # Test 2: Specific tags (Qwen)
    test_chat(tags=["qwen"], prompt="请用一句话描述Python")

    # Test 3: Default routing (Priority based)
    test_chat(prompt="讲个笑话")
