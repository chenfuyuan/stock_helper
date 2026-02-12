from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.shared.config import settings
from src.shared.infrastructure.logging import setup_logging
from src.api.routes import api_router
from src.api.middlewares.error_handler import ErrorHandlingMiddleware
from src.shared.infrastructure.scheduler import SchedulerService

# 初始化日志配置
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
)

# 事件处理
@app.on_event("startup")
async def startup_event():
    """
    应用启动事件处理
    - 启动定时任务调度器
    - 初始化 LLM 注册表并从数据库加载配置
    """
    logger.info("Application starting up...")
    
    # 启动调度器
    logger.info("Initializing Scheduler Service...")
    SchedulerService.start()
    
    # 初始化 LLM 注册表（委托 Application 层服务，不直接依赖 Infrastructure）
    from src.modules.llm_platform.application.services.startup import LLMPlatformStartup
    await LLMPlatformStartup.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件处理
    - 关闭定时任务调度器
    """
    logger.info("Application shutting down...")
    
    # 关闭调度器
    SchedulerService.shutdown()
    logger.info("Application shutdown completed.")

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
