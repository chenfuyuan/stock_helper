import pytest
import logging
from src.modules.llm_platform.application.services.llm_service import LLMService
from src.modules.llm_platform.infrastructure.registry import LLMRegistry
from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import PgLLMConfigRepository

# 设置日志，方便查看调用过程
logger = logging.getLogger(__name__)

@pytest.mark.asyncio
class TestLLMRealCall:
    """
    大模型真实调用集成测试类。
    使用数据库中已有的配置进行实际的网络请求测试。
    """

    async def test_all_active_models_call(self, db_session):
        """
        测试数据库中所有激活的模型是否都能正常调用。
        """
        # 1. 初始化基础设施
        repo = PgLLMConfigRepository(db_session)
        registry = LLMRegistry()
        registry.set_repository(repo)
        
        # 2. 从数据库加载配置到注册中心
        await registry.refresh()
        
        configs = registry.get_all_configs()
        active_configs = [c for c in configs if c.is_active]
        
        if not active_configs:
            pytest.skip("数据库中没有激活的大模型配置，跳过测试。请先使用 scripts/add_llm_config_template.py 添加配置。")

        # 3. 初始化应用服务
        service = LLMService(registry=registry)
        
        print(f"\n发现 {len(active_configs)} 个激活的模型配置，开始逐一测试...")

        # 4. 遍历测试每个模型
        success_count = 0
        failure_details = []

        for config in active_configs:
            print(f"\n[测试模型] Alias: {config.alias} | Vendor: {config.vendor} | Model: {config.model_name}")
            
            try:
                # 执行一次简单的对话生成
                response = await service.generate(
                    prompt="你好，请用一句话介绍你自己。",
                    alias=config.alias,
                    temperature=0.7
                )
                
                print(f"  ✅ 调用成功！")
                print(f"  💬 模型回复: {response}")
                
                assert response is not None
                assert len(response.strip()) > 0
                success_count += 1
                
            except Exception as e:
                print(f"  ❌ 调用失败: {str(e)}")
                failure_details.append(f"Model {config.alias} failed: {str(e)}")

        # 5. 总结测试结果
        print(f"\n测试结束: 成功 {success_count}/{len(active_configs)}")
        
        if failure_details:
            error_msg = "\n".join(failure_details)
            pytest.fail(f"部分模型调用失败:\n{error_msg}")

    async def test_routing_by_tags(self, db_session):
        """
        测试通过标签(Tags)进行路由调用。
        """
        repo = PgLLMConfigRepository(db_session)
        registry = LLMRegistry()
        registry.set_repository(repo)
        await registry.refresh()
        
        configs = registry.get_all_configs()
        if not configs:
            pytest.skip("数据库中无配置")

        # 寻找带有标签的模型
        tagged_configs = [c for c in configs if c.tags and c.is_active]
        if not tagged_configs:
            pytest.skip("数据库中没有带标签的激活模型，跳过标签路由测试。")

        service = LLMService(registry=registry)
        
        # 尝试使用第一个模型的第一个标签进行调用
        target_tag = tagged_configs[0].tags[0]
        print(f"\n[测试标签路由] 使用标签: {target_tag}")
        
        try:
            response = await service.generate(
                prompt="Ping",
                tags=[target_tag]
            )
            print(f"  ✅ 通过标签 [{target_tag}] 调用成功！")
            assert response is not None
        except Exception as e:
            pytest.fail(f"标签路由调用失败: {str(e)}")
