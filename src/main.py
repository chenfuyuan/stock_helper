from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.middlewares.error_handler import ErrorHandlingMiddleware
from src.api.routes import api_router
from src.modules.knowledge_center.container import (
    KnowledgeCenterContainer,
    close_knowledge_center_driver,
)
from src.shared.config import settings
from src.shared.infrastructure.logging import setup_logging
from src.shared.infrastructure.scheduler.scheduler_service import SchedulerService

# 初始化日志配置
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    - startup: 启动定时任务调度器，初始化 LLM 注册表并从数据库加载配置
    - shutdown: 关闭定时任务调度器
    """
    # 启动事件
    logger.info("Application starting up...")

    # 启动调度器
    logger.info("Initializing Scheduler Service...")
    SchedulerService.start()

    # 从数据库加载持久化的调度配置并自动注册
    from src.modules.data_engineering.presentation.rest.scheduler_routes import JOB_REGISTRY
    from src.shared.infrastructure.db.session import AsyncSessionLocal
    
    await SchedulerService.load_persisted_jobs(
        registry=JOB_REGISTRY,
        session_factory=AsyncSessionLocal,
    )

    # 初始化 LLM 注册表（委托 Application 层服务，不直接依赖 Infrastructure）
    from src.modules.llm_platform.application.services.startup import (
        LLMPlatformStartup,
    )

    await LLMPlatformStartup.initialize()

    # 初始化 Knowledge Center 图谱约束（幂等）
    try:
        await KnowledgeCenterContainer().graph_repository().ensure_constraints()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Knowledge Center 图谱约束初始化失败，将在后续同步时重试: {exc}")
    logger.info("Application startup completed.")

    yield

    # 关闭事件
    logger.info("Application shutting down...")

    # 关闭调度器
    SchedulerService.shutdown()

    # 关闭 Knowledge Center Neo4j Driver
    close_knowledge_center_driver()
    logger.info("Application shutdown completed.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    lifespan=lifespan,
)


# 配置 CORS 中间件
if settings.BACKEND_CORS_ORIGINS:
    logger.info(f"Configuring CORS with origins: {settings.BACKEND_CORS_ORIGINS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加全局异常处理中间件
app.add_middleware(ErrorHandlingMiddleware)

# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """
    根路由
    用于快速检查服务是否存活
    """
    logger.debug("Root endpoint called")
    return {"message": "Welcome to Stock Helper API"}
