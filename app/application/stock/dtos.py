from pydantic import BaseModel

class SyncStockOutput(BaseModel):
    """
    股票同步用例输出 DTO
    """
    status: str
    synced_count: int
    message: str
