from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.db.session import get_db_session

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db_session),
):
    """
    健康检查端点
    检查应用状态及数据库连接
    """
    try:
        # 检查数据库连接
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "details": str(e),
        }
