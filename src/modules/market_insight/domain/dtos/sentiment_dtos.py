from pydantic import BaseModel


# ========== 输入 DTO（用于接收 DE 模块数据） ==========

class LimitUpPoolItemDTO(BaseModel):
    """涨停池单项 DTO（MI 领域层）"""
    
    third_code: str
    stock_name: str
    pct_chg: float
    close: float
    amount: float
    consecutive_boards: int
    industry: str


class BrokenBoardItemDTO(BaseModel):
    """炸板池单项 DTO（MI 领域层）"""
    
    third_code: str
    stock_name: str
    pct_chg: float
    close: float
    amount: float
    open_count: int
    industry: str


class PreviousLimitUpItemDTO(BaseModel):
    """昨日涨停表现单项 DTO（MI 领域层）"""
    
    third_code: str
    stock_name: str
    pct_chg: float
    close: float
    amount: float
    yesterday_consecutive_boards: int
    industry: str


# ========== 输出 DTO（分析结果） ==========

class BoardTier(BaseModel):
    """连板梯队"""
    
    board_count: int
    stocks: list[str]


class ConsecutiveBoardLadder(BaseModel):
    """连板梯队分布分析结果"""
    
    max_height: int
    tiers: list[BoardTier]
    total_limit_up_count: int


class PreviousLimitUpPerformance(BaseModel):
    """昨日涨停今日表现分析结果"""
    
    total_count: int
    up_count: int
    down_count: int
    avg_pct_chg: float
    profit_rate: float
    strongest: list[PreviousLimitUpItemDTO]
    weakest: list[PreviousLimitUpItemDTO]


class BrokenBoardAnalysis(BaseModel):
    """炸板分析结果"""
    
    broken_count: int
    total_attempted: int
    broken_rate: float
    broken_stocks: list[BrokenBoardItemDTO]
