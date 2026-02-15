from datetime import date
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from src.modules.data_engineering.domain.model.stock_daily import StockDaily
from src.modules.data_engineering.domain.ports.repositories.market_quote_repo import (
    IMarketQuoteRepository,
)
from src.modules.data_engineering.infrastructure.persistence.models.daily_bar_model import (
    StockDailyModel,
)
from src.shared.infrastructure.base_repository import BaseRepository


class StockDailyRepositoryImpl(BaseRepository[StockDailyModel], IMarketQuoteRepository):
    def __init__(self, session):
        super().__init__(StockDailyModel, session)

    async def save_all(self, dailies: List[StockDaily]) -> int:
        if not dailies:
            return 0

        # Convert to dicts first
        raw_data_list = [d.model_dump(exclude_unset=True) for d in dailies]

        # Deduplicate based on primary key (third_code, trade_date)
        # Keep the last entry if duplicates exist
        deduplicated_data = {}
        for item in raw_data_list:
            key = (item.get("third_code"), item.get("trade_date"))
            deduplicated_data[key] = item

        data_list = list(deduplicated_data.values())

        # Batch processing
        batch_size = 1000
        total_saved = 0

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i : i + batch_size]

            stmt = insert(StockDailyModel).values(batch)
            stmt = stmt.on_conflict_do_update(
                index_elements=["third_code", "trade_date"],
                set_={col.name: col for col in stmt.excluded if col.name not in ["created_at"]},
            )

            await self.session.execute(stmt)
            total_saved += len(batch)

        await self.session.commit()
        return total_saved

    async def get_by_third_code_and_date_range(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """按第三方代码与日期区间查询日线，按交易日期升序返回。"""
        stmt = (
            select(StockDailyModel)
            .where(
                StockDailyModel.third_code == third_code,
                StockDailyModel.trade_date >= start_date,
                StockDailyModel.trade_date <= end_date,
            )
            .order_by(StockDailyModel.trade_date.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            StockDaily(
                third_code=r.third_code,
                trade_date=r.trade_date,
                open=r.open or 0.0,
                high=r.high or 0.0,
                low=r.low or 0.0,
                close=r.close or 0.0,
                pre_close=r.pre_close or 0.0,
                change=r.change or 0.0,
                pct_chg=r.pct_chg or 0.0,
                vol=r.vol or 0.0,
                amount=r.amount or 0.0,
                adj_factor=r.adj_factor,
                source=r.source or "tushare",
            )
            for r in rows
        ]

    async def get_latest_by_third_code(self, third_code: str) -> Optional[StockDaily]:
        """查询指定标的最新的一条日线数据"""
        stmt = (
            select(StockDailyModel)
            .where(StockDailyModel.third_code == third_code)
            .order_by(StockDailyModel.trade_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        r = result.scalar_one_or_none()

        if not r:
            return None

        # 与 get_valuation_dailies 一致：返回完整估值字段，供估值概览使用
        return StockDaily(
            third_code=r.third_code,
            trade_date=r.trade_date,
            open=r.open or 0.0,
            high=r.high or 0.0,
            low=r.low or 0.0,
            close=r.close or 0.0,
            pre_close=r.pre_close or 0.0,
            change=r.change or 0.0,
            pct_chg=r.pct_chg or 0.0,
            vol=r.vol or 0.0,
            amount=r.amount or 0.0,
            adj_factor=r.adj_factor,
            turnover_rate=r.turnover_rate,
            turnover_rate_f=r.turnover_rate_f,
            volume_ratio=r.volume_ratio,
            pe=r.pe,
            pe_ttm=r.pe_ttm,
            pb=r.pb,
            ps=r.ps,
            ps_ttm=r.ps_ttm,
            dv_ratio=r.dv_ratio,
            dv_ttm=r.dv_ttm,
            total_share=r.total_share,
            float_share=r.float_share,
            free_share=r.free_share,
            total_mv=r.total_mv,
            circ_mv=r.circ_mv,
            source=r.source or "tushare",
        )

    async def get_latest_trade_date(self) -> Optional[date]:
        """查询数据库中最新的交易日期（max(trade_date)）"""
        stmt = select(func.max(StockDailyModel.trade_date))
        result = await self.session.execute(stmt)
        latest_date = result.scalar_one_or_none()
        return latest_date

    async def get_valuation_dailies(
        self, third_code: str, start_date: date, end_date: date
    ) -> List[StockDaily]:
        """
        按第三方代码与日期区间查询日线（含估值字段），用于估值分析。
        返回的 StockDaily 包含完整的估值字段：pe_ttm、pb、ps_ttm、dv_ratio、total_mv 等。
        按交易日期升序返回。
        """
        stmt = (
            select(StockDailyModel)
            .where(
                StockDailyModel.third_code == third_code,
                StockDailyModel.trade_date >= start_date,
                StockDailyModel.trade_date <= end_date,
            )
            .order_by(StockDailyModel.trade_date.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            StockDaily(
                third_code=r.third_code,
                trade_date=r.trade_date,
                open=r.open or 0.0,
                high=r.high or 0.0,
                low=r.low or 0.0,
                close=r.close or 0.0,
                pre_close=r.pre_close or 0.0,
                change=r.change or 0.0,
                pct_chg=r.pct_chg or 0.0,
                vol=r.vol or 0.0,
                amount=r.amount or 0.0,
                adj_factor=r.adj_factor,
                turnover_rate=r.turnover_rate,
                turnover_rate_f=r.turnover_rate_f,
                volume_ratio=r.volume_ratio,
                pe=r.pe,
                pe_ttm=r.pe_ttm,
                pb=r.pb,
                ps=r.ps,
                ps_ttm=r.ps_ttm,
                dv_ratio=r.dv_ratio,
                dv_ttm=r.dv_ttm,
                total_share=r.total_share,
                float_share=r.float_share,
                free_share=r.free_share,
                total_mv=r.total_mv,
                circ_mv=r.circ_mv,
                source=r.source or "tushare",
            )
            for r in rows
        ]

    async def get_all_by_trade_date(self, trade_date: date) -> List[StockDaily]:
        """查询指定交易日的全市场日线数据"""
        from src.modules.data_engineering.infrastructure.persistence.models.stock_model import StockModel
        
        stmt = (
            select(StockDailyModel, StockModel.name)
            .join(StockModel, StockDailyModel.third_code == StockModel.third_code, isouter=True)
            .where(StockDailyModel.trade_date == trade_date)
            .order_by(StockDailyModel.third_code.asc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            StockDaily(
                third_code=r.third_code,
                stock_name=stock_name or "",
                trade_date=r.trade_date,
                open=r.open or 0.0,
                high=r.high or 0.0,
                low=r.low or 0.0,
                close=r.close or 0.0,
                pre_close=r.pre_close or 0.0,
                change=r.change or 0.0,
                pct_chg=r.pct_chg or 0.0,
                vol=r.vol or 0.0,
                amount=r.amount or 0.0,
                adj_factor=r.adj_factor,
                source=r.source or "tushare",
            )
            for r, stock_name in rows
        ]
