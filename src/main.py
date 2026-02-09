from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    # 启动调度器
    SchedulerService.start()
    
    # 初始化 LLM 注册表 (从 DB 加载配置)
    from src.shared.infrastructure.db.session import AsyncSessionLocal
    from src.modules.llm_platform.infrastructure.registry import LLMRegistry
    from src.modules.llm_platform.infrastructure.persistence.repositories.pg_config_repo import PgLLMConfigRepository
    
    async with AsyncSessionLocal() as session:
        repo = PgLLMConfigRepository(session)
        registry = LLMRegistry()
        registry.set_repository(repo)
        await registry.refresh()

@app.on_event("shutdown")
async def shutdown_event():
    # 关闭调度器
    SchedulerService.shutdown()

# 配置 CORS 中间件
if settings.BACKEND_CORS_ORIGINS:
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
    return {"message": "Welcome to Stock Helper API"}
