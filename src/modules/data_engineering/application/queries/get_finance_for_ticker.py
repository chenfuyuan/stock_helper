"""
按标的返回最近 N 期财务指标数据的 Application 接口。
供 Research 等模块通过 Application 层获取财务数据，不直接依赖 repository 或 domain 实现。
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)
from src.modules.data_engineering.domain.ports.repositories.financial_data_repo import (
    IFinancialDataRepository,
)


class FinanceIndicatorDTO(BaseModel):
    """
    财务指标 DTO，仅暴露 Research 等消费方需要的字段。
    不含 StockFinance 的全部内部字段。
    """

    end_date: date = Field(..., description="报告期")
    ann_date: date = Field(..., description="公告日期")
    third_code: str = Field(..., description="第三方代码")
    source: str = Field(default="tushare", description="数据来源")

    # 盈利能力
    gross_margin: Optional[float] = Field(None, description="毛利率")
    netprofit_margin: Optional[float] = Field(None, description="销售净利率")
    roe_waa: Optional[float] = Field(None, description="加权平均净资产收益率")
    roic: Optional[float] = Field(None, description="投入资本回报率")

    # 每股指标
    eps: Optional[float] = Field(None, description="基本每股收益")
    bps: Optional[float] = Field(None, description="每股净资产")
    profit_dedt: Optional[float] = Field(None, description="扣非净利润")
    ocfps: Optional[float] = Field(None, description="每股经营现金流")
    fcff_ps: Optional[float] = Field(None, description="每股企业自由现金流")

    # 资产负债与流动性
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")
    debt_to_assets: Optional[float] = Field(None, description="资产负债率")
    interestdebt: Optional[float] = Field(None, description="带息债务")
    netdebt: Optional[float] = Field(None, description="净债务")

    # 运营效率
    invturn_days: Optional[float] = Field(None, description="存货周转天数")
    arturn_days: Optional[float] = Field(None, description="应收账款周转天数")
    assets_turn: Optional[float] = Field(None, description="总资产周转率")

    # 用于 YoY 增速计算
    total_revenue_ps: Optional[float] = Field(
        None, description="每股营业总收入"
    )
    fcff: Optional[float] = Field(None, description="企业自由现金流量")

    model_config = {"frozen": True}


def _to_dto(f: StockFinance) -> FinanceIndicatorDTO:
    """将领域实体转为 DTO。"""
    return FinanceIndicatorDTO(
        end_date=f.end_date,
        ann_date=f.ann_date,
        third_code=f.third_code,
        source=getattr(f, "source", "tushare") or "tushare",
        gross_margin=f.gross_margin,
        netprofit_margin=f.netprofit_margin,
        roe_waa=f.roe_waa,
        roic=f.roic,
        eps=f.eps,
        bps=f.bps,
        profit_dedt=f.profit_dedt,
        ocfps=f.ocfps,
        fcff_ps=f.fcff_ps,
        current_ratio=f.current_ratio,
        quick_ratio=f.quick_ratio,
        debt_to_assets=f.debt_to_assets,
        interestdebt=f.interestdebt,
        netdebt=f.netdebt,
        invturn_days=f.invturn_days,
        arturn_days=f.arturn_days,
        assets_turn=f.assets_turn,
        total_revenue_ps=f.total_revenue_ps,
        fcff=f.fcff,
    )


class GetFinanceForTickerUseCase:
    """
    按标的（third_code）查询最近 N 期财务指标，返回 DTO 列表。
    其他模块仅通过本用例获取财务数据，不直接依赖 repository。
    """

    def __init__(self, financial_repo: IFinancialDataRepository):
        self._repo = financial_repo

    async def execute(
        self,
        ticker: str,
        limit: int = 5,
    ) -> List[FinanceIndicatorDTO]:
        """
        执行查询。ticker 为第三方代码（如 000001.SZ）。
        返回按 end_date 降序的财务指标 DTO 列表（最新期在前）。
        """
        finances: List[StockFinance] = (
            await self._repo.get_by_third_code_recent(
                third_code=ticker,
                limit=limit,
            )
        )
        return [_to_dto(f) for f in finances]
