from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.presentation.api.api_v1.api import api_router
from app.presentation.middlewares.error_handler import ErrorHandlingMiddleware
from app.core.scheduler import SchedulerService
from app.jobs.sync_job import sync_incremental_finance_job
# from app.jobs.sync_job import sync_daily_data_job

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
    
    # 默认不再自动添加任务，全部通过 API 动态管理
    # scheduler = SchedulerService.get_scheduler()
    # scheduler.add_job(sync_incremental_finance_job, 'cron', hour=2, minute=0, id='sync_incremental_finance_job', replace_existing=True)
    
    # 添加定时任务：每 1 分钟执行一次
    # 注意：如果不想自动运行，请注释掉下面这行
    # scheduler = SchedulerService.get_scheduler()
    # scheduler.add_job(sync_daily_data_job, 'interval', minutes=1, id='sync_daily_job', replace_existing=True)

@app.on_event("shutdown")
async def shutdown_event():
    # 关闭调度器
    SchedulerService.shutdown()

# 配置 CORS 中间件
# 允许前端跨域访问
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
