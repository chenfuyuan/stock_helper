"""
LLM 平台启动逻辑。

将 main.py 中的 LLM 注册表初始化抽取到本模块，main 仅调用 Application 层服务，不直接 import Infrastructure 实现。
"""

from loguru import logger

from src.modules.llm_platform.container import LLMPlatformContainer


class LLMPlatformStartup:
    """LLM 平台启动服务。"""

    @staticmethod
    async def initialize() -> None:
        """从数据库加载 LLM 配置并刷新注册表。"""
        from src.shared.infrastructure.db.session import AsyncSessionLocal

        logger.info("Initializing LLM Registry...")
        try:
            async with AsyncSessionLocal() as session:
                container = LLMPlatformContainer(session)
                registry = container.llm_registry()
                await registry.refresh()
            logger.info("LLM Registry initialization completed.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Registry: {str(e)}")
            # 不阻断启动，但记录严重错误
