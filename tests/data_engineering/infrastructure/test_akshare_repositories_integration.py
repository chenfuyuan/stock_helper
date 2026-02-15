"""
AkShare Repository 集成测试
验证 UPSERT 幂等性、按日期查询、唯一约束验证
"""

import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.data_engineering.domain.model.broken_board import BrokenBoardStock
from src.modules.data_engineering.domain.model.dragon_tiger import DragonTigerDetail
from src.modules.data_engineering.domain.model.limit_up_pool import LimitUpPoolStock
from src.modules.data_engineering.domain.model.previous_limit_up import PreviousLimitUpStock
from src.modules.data_engineering.domain.model.sector_capital_flow import SectorCapitalFlow
from src.modules.data_engineering.infrastructure.persistence.models.broken_board_model import (
    BrokenBoardModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.dragon_tiger_model import (
    DragonTigerModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.limit_up_pool_model import (
    LimitUpPoolModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.previous_limit_up_model import (
    PreviousLimitUpModel,
)
from src.modules.data_engineering.infrastructure.persistence.models.sector_capital_flow_model import (
    SectorCapitalFlowModel,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_broken_board_repo import (
    PgBrokenBoardRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_dragon_tiger_repo import (
    PgDragonTigerRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_limit_up_pool_repo import (
    PgLimitUpPoolRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_previous_limit_up_repo import (
    PgPreviousLimitUpRepository,
)
from src.modules.data_engineering.infrastructure.persistence.repositories.pg_sector_capital_flow_repo import (
    PgSectorCapitalFlowRepository,
)

pytestmark = pytest.mark.integration


class TestPgLimitUpPoolRepository:
    """PgLimitUpPoolRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        return PgLimitUpPoolRepository(test_db_session)

    @pytest.fixture
    def sample_data(self):
        return [
            LimitUpPoolStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.01,
                close=12.0,
                amount=200000000.0,
                turnover_rate=2.5,
                consecutive_boards=2,
                first_limit_up_time="09:25:00",
                last_limit_up_time="09:25:00",
                industry="银行业",
            ),
            LimitUpPoolStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000002.SZ",
                stock_name="万科A",
                pct_chg=10.02,
                close=15.0,
                amount=150000000.0,
                turnover_rate=1.8,
                consecutive_boards=1,
                first_limit_up_time="09:30:00",
                last_limit_up_time="09:30:00",
                industry="房地产",
            ),
        ]

    async def test_save_all_upsert(self, repository, sample_data):
        """测试批量 UPSERT 操作"""
        # 第一次插入
        count = await repository.save_all(sample_data)
        assert count == 2

        # 验证数据已插入
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 2
        assert result[0].third_code == "000001.SZ"
        assert result[1].third_code == "000002.SZ"

        # 第二次插入相同数据（应该更新）
        updated_data = [
            LimitUpPoolStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=10.03,  # 更新涨跌幅
                close=12.1,  # 更新价格
                amount=210000000.0,  # 更新成交额
                turnover_rate=2.6,
                consecutive_boards=3,  # 更新连板天数
                first_limit_up_time="09:25:00",
                last_limit_up_time="09:25:00",
                industry="银行业",
            )
        ]
        count = await repository.save_all(updated_data)
        assert count == 1

        # 验证数据已更新
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 2  # 总记录数不变
        
        # 查找更新后的记录
        updated_record = next(r for r in result if r.third_code == "000001.SZ")
        assert updated_record.pct_chg == 10.03
        assert updated_record.close == 12.1
        assert updated_record.consecutive_boards == 3

    async def test_get_by_date_empty(self, repository):
        """测试查询空数据"""
        result = await repository.get_by_date(date(2024, 2, 15))
        assert result == []

    async def test_save_all_empty_list(self, repository):
        """测试保存空列表"""
        count = await repository.save_all([])
        assert count == 0

    async def test_unique_constraint_violation(self, repository, sample_data):
        """测试唯一约束（通过 UPSERT 验证）"""
        # 插入数据
        await repository.save_all(sample_data)

        # 尝试插入违反唯一约束的数据（应该更新而不是报错）
        duplicate_data = [
            LimitUpPoolStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",  # 相同的唯一键
                stock_name="平安银行",
                pct_chg=10.05,
                close=12.2,
                amount=220000000.0,
                turnover_rate=2.7,
                consecutive_boards=4,
                first_limit_up_time="09:25:00",
                last_limit_up_time="09:25:00",
                industry="银行业",
            )
        ]
        
        # 应该成功执行（UPSERT）
        count = await repository.save_all(duplicate_data)
        assert count == 1

        # 验证只有一条记录
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 2
        
        # 验证记录已更新
        updated_record = next(r for r in result if r.third_code == "000001.SZ")
        assert updated_record.pct_chg == 10.05


class TestPgBrokenBoardRepository:
    """PgBrokenBoardRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        return PgBrokenBoardRepository(test_db_session)

    @pytest.fixture
    def sample_data(self):
        return [
            BrokenBoardStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=8.5,
                close=11.5,
                amount=180000000.0,
                turnover_rate=2.2,
                open_count=3,
                first_limit_up_time="09:25:00",
                last_open_time="10:15:00",
                industry="银行业",
            ),
        ]

    async def test_save_all_upsert(self, repository, sample_data):
        """测试炸板池数据 UPSERT"""
        # 第一次插入
        count = await repository.save_all(sample_data)
        assert count == 1

        # 验证数据已插入
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 1
        assert result[0].third_code == "000001.SZ"
        assert result[0].open_count == 3

        # 更新数据
        updated_data = [
            BrokenBoardStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=8.5,
                close=11.5,
                amount=180000000.0,
                turnover_rate=2.2,
                open_count=4,  # 更新开板次数
                first_limit_up_time="09:25:00",
                last_open_time="10:20:00",  # 更新最后开板时间
                industry="银行业",
            )
        ]
        count = await repository.save_all(updated_data)
        assert count == 1

        # 验证数据已更新
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 1
        assert result[0].open_count == 4
        assert result[0].last_open_time == "10:20:00"


class TestPgPreviousLimitUpRepository:
    """PgPreviousLimitUpRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        return PgPreviousLimitUpRepository(test_db_session)

    @pytest.fixture
    def sample_data(self):
        return [
            PreviousLimitUpStock(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=5.2,
                close=12.5,
                amount=160000000.0,
                turnover_rate=2.0,
                yesterday_consecutive_boards=2,
                industry="银行业",
            ),
        ]

    async def test_save_all_upsert(self, repository, sample_data):
        """测试昨日涨停表现数据 UPSERT"""
        count = await repository.save_all(sample_data)
        assert count == 1

        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 1
        assert result[0].yesterday_consecutive_boards == 2


class TestPgDragonTigerRepository:
    """PgDragonTigerRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        return PgDragonTigerRepository(test_db_session)

    @pytest.fixture
    def sample_data(self):
        return [
            DragonTigerDetail(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=8.5,
                close=12.5,
                reason="机构专用",
                net_amount=50000000.0,
                buy_amount=100000000.0,
                sell_amount=50000000.0,
                buy_seats=[{"seat_name": "机构席位A", "buy_amount": 50000000.0}],
                sell_seats=[{"seat_name": "游资席位A", "sell_amount": 50000000.0}],
            ),
            DragonTigerDetail(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=8.5,
                close=12.5,
                reason="游资接力",  # 同一股票不同上榜原因
                net_amount=30000000.0,
                buy_amount=80000000.0,
                sell_amount=50000000.0,
                buy_seats=[{"seat_name": "游资席位B", "buy_amount": 80000000.0}],
                sell_seats=[{"seat_name": "机构席位B", "sell_amount": 50000000.0}],
            ),
        ]

    async def test_save_all_upsert(self, repository, sample_data):
        """测试龙虎榜数据 UPSERT（复合唯一键）"""
        # 第一次插入
        count = await repository.save_all(sample_data)
        assert count == 2

        # 验证数据已插入
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 2
        
        # 验证不同上榜原因的记录都存在
        reasons = [r.reason for r in result]
        assert "机构专用" in reasons
        assert "游资接力" in reasons

        # 更新其中一条记录
        updated_data = [
            DragonTigerDetail(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                third_code="000001.SZ",
                stock_name="平安银行",
                pct_chg=8.5,
                close=12.5,
                reason="机构专用",  # 相同的唯一键
                net_amount=55000000.0,  # 更新净买入额
                buy_amount=105000000.0,
                sell_amount=50000000.0,
                buy_seats=[{"seat_name": "机构席位A", "buy_amount": 55000000.0}],
                sell_seats=[{"seat_name": "游资席位A", "sell_amount": 50000000.0}],
            )
        ]
        count = await repository.save_all(updated_data)
        assert count == 1

        # 验证数据已更新，总记录数不变
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 2
        
        # 查找更新后的记录
        updated_record = next(r for r in result if r.reason == "机构专用")
        assert updated_record.net_amount == 55000000.0


class TestPgSectorCapitalFlowRepository:
    """PgSectorCapitalFlowRepository 集成测试"""

    @pytest.fixture
    async def repository(self, test_db_session: AsyncSession):
        return PgSectorCapitalFlowRepository(test_db_session)

    @pytest.fixture
    def sample_data(self):
        return [
            SectorCapitalFlow(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                sector_name="人工智能",
                sector_type="概念资金流",
                net_amount=500000.0,
                inflow_amount=800000.0,
                outflow_amount=300000.0,
                pct_chg=3.5,
            ),
            SectorCapitalFlow(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                sector_name="新能源",
                sector_type="概念资金流",
                net_amount=-200000.0,
                inflow_amount=400000.0,
                outflow_amount=600000.0,
                pct_chg=-1.2,
            ),
            SectorCapitalFlow(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                sector_name="银行业",
                sector_type="行业资金流",
                net_amount=300000.0,
                inflow_amount=600000.0,
                outflow_amount=300000.0,
                pct_chg=2.1,
            ),
        ]

    async def test_save_all_upsert(self, repository, sample_data):
        """测试板块资金流向数据 UPSERT"""
        count = await repository.save_all(sample_data)
        assert count == 3

        # 验证数据已插入
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 3

        # 验证按板块类型过滤
        concept_result = await repository.get_by_date(date(2024, 2, 15), sector_type="概念资金流")
        assert len(concept_result) == 2
        assert all(r.sector_type == "概念资金流" for r in concept_result)

        industry_result = await repository.get_by_date(date(2024, 2, 15), sector_type="行业资金流")
        assert len(industry_result) == 1
        assert industry_result[0].sector_name == "银行业"

        # 更新数据
        updated_data = [
            SectorCapitalFlow(
                id=uuid.uuid4(),
                trade_date=date(2024, 2, 15),
                sector_name="人工智能",
                sector_type="概念资金流",  # 相同唯一键
                net_amount=520000.0,  # 更新净流入
                inflow_amount=820000.0,
                outflow_amount=300000.0,
                pct_chg=3.7,  # 更新涨跌幅
            )
        ]
        count = await repository.save_all(updated_data)
        assert count == 1

        # 验证数据已更新
        result = await repository.get_by_date(date(2024, 2, 15))
        assert len(result) == 3  # 总记录数不变
        
        # 查找更新后的记录
        updated_record = next(r for r in result if r.sector_name == "人工智能")
        assert updated_record.net_amount == 520000.0
        assert updated_record.pct_chg == 3.7

    async def test_get_by_date_with_sector_type_filter(self, repository, sample_data):
        """测试按板块类型过滤查询"""
        await repository.save_all(sample_data)

        # 查询所有类型
        all_result = await repository.get_by_date(date(2024, 2, 15))
        assert len(all_result) == 3

        # 查询特定类型
        concept_result = await repository.get_by_date(date(2024, 2, 15), sector_type="概念资金流")
        assert len(concept_result) == 2
        assert all(r.sector_type == "概念资金流" for r in concept_result)

        # 查询不存在的类型
        empty_result = await repository.get_by_date(date(2024, 2, 15), sector_type="不存在的类型")
        assert len(empty_result) == 0

    async def test_get_by_date_no_sector_type(self, repository, sample_data):
        """测试不指定板块类型的查询"""
        await repository.save_all(sample_data)

        # 不指定 sector_type 应该返回所有记录
        result = await repository.get_by_date(date(2024, 2, 15), sector_type=None)
        assert len(result) == 3
        
        # 默认参数也是 None
        result_default = await repository.get_by_date(date(2024, 2, 15))
        assert len(result_default) == 3
