"""add_akshare_market_data_tables

新增 AkShare 市场数据相关表：涨停池、炸板池、昨日涨停表现、龙虎榜、板块资金流向

Revision ID: c0ff00000012
Revises: c0ff00000011
Create Date: 2026-02-15

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c0ff00000012"
down_revision = "c0ff00000011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- de_limit_up_pool（涨停池） -----
    op.create_table(
        "de_limit_up_pool",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码（系统标准格式）"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="涨跌幅（百分比）"),
        sa.Column("close", sa.Float(), nullable=False, comment="最新价"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额"),
        sa.Column("turnover_rate", sa.Float(), nullable=False, comment="换手率"),
        sa.Column("consecutive_boards", sa.Integer(), nullable=False, comment="连板天数（首板为 1）"),
        sa.Column("first_limit_up_time", sa.String(length=20), nullable=True, comment="首次封板时间"),
        sa.Column("last_limit_up_time", sa.String(length=20), nullable=True, comment="最后封板时间"),
        sa.Column("industry", sa.String(length=100), nullable=False, comment="所属行业"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "third_code", name="uq_limit_up_pool"),
    )
    op.create_index(op.f("ix_de_limit_up_pool_id"), "de_limit_up_pool", ["id"], unique=False)
    op.create_index(
        op.f("ix_de_limit_up_pool_trade_date"), "de_limit_up_pool", ["trade_date"], unique=False
    )
    op.create_index(
        op.f("ix_de_limit_up_pool_third_code"), "de_limit_up_pool", ["third_code"], unique=False
    )

    # ----- de_broken_board_pool（炸板池） -----
    op.create_table(
        "de_broken_board_pool",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码（系统标准格式）"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="涨跌幅（百分比）"),
        sa.Column("close", sa.Float(), nullable=False, comment="最新价"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额"),
        sa.Column("turnover_rate", sa.Float(), nullable=False, comment="换手率"),
        sa.Column("open_count", sa.Integer(), nullable=False, comment="开板次数"),
        sa.Column("first_limit_up_time", sa.String(length=20), nullable=True, comment="首次封板时间"),
        sa.Column("last_open_time", sa.String(length=20), nullable=True, comment="最后开板时间"),
        sa.Column("industry", sa.String(length=100), nullable=False, comment="所属行业"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "third_code", name="uq_broken_board"),
    )
    op.create_index(
        op.f("ix_de_broken_board_pool_id"), "de_broken_board_pool", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_de_broken_board_pool_trade_date"),
        "de_broken_board_pool",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_de_broken_board_pool_third_code"),
        "de_broken_board_pool",
        ["third_code"],
        unique=False,
    )

    # ----- de_previous_limit_up（昨日涨停表现） -----
    op.create_table(
        "de_previous_limit_up",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column(
            "trade_date", sa.Date(), nullable=False, comment="交易日期（今日日期，即表现观察日）"
        ),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码（系统标准格式）"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="今日涨跌幅（百分比）"),
        sa.Column("close", sa.Float(), nullable=False, comment="最新价"),
        sa.Column("amount", sa.Float(), nullable=False, comment="成交额"),
        sa.Column("turnover_rate", sa.Float(), nullable=False, comment="换手率"),
        sa.Column(
            "yesterday_consecutive_boards", sa.Integer(), nullable=False, comment="昨日连板天数"
        ),
        sa.Column("industry", sa.String(length=100), nullable=False, comment="所属行业"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "third_code", name="uq_previous_limit_up"),
    )
    op.create_index(
        op.f("ix_de_previous_limit_up_id"), "de_previous_limit_up", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_de_previous_limit_up_trade_date"),
        "de_previous_limit_up",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_de_previous_limit_up_third_code"),
        "de_previous_limit_up",
        ["third_code"],
        unique=False,
    )

    # ----- de_dragon_tiger（龙虎榜） -----
    op.create_table(
        "de_dragon_tiger",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="股票代码（系统标准格式）"),
        sa.Column("stock_name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="涨跌幅（百分比）"),
        sa.Column("close", sa.Float(), nullable=False, comment="收盘价"),
        sa.Column("reason", sa.String(length=200), nullable=False, comment="上榜原因"),
        sa.Column("net_amount", sa.Float(), nullable=False, comment="龙虎榜净买入额"),
        sa.Column("buy_amount", sa.Float(), nullable=False, comment="买入总额"),
        sa.Column("sell_amount", sa.Float(), nullable=False, comment="卖出总额"),
        sa.Column(
            "buy_seats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="买入席位详情（JSONB）",
        ),
        sa.Column(
            "sell_seats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="卖出席位详情（JSONB）",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_date", "third_code", "reason", name="uq_dragon_tiger"),
    )
    op.create_index(op.f("ix_de_dragon_tiger_id"), "de_dragon_tiger", ["id"], unique=False)
    op.create_index(
        op.f("ix_de_dragon_tiger_trade_date"), "de_dragon_tiger", ["trade_date"], unique=False
    )
    op.create_index(
        op.f("ix_de_dragon_tiger_third_code"), "de_dragon_tiger", ["third_code"], unique=False
    )

    # ----- de_sector_capital_flow（板块资金流向） -----
    op.create_table(
        "de_sector_capital_flow",
        sa.Column("id", sa.Integer(), nullable=False, comment="主键"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("sector_name", sa.String(length=100), nullable=False, comment="板块名称"),
        sa.Column("sector_type", sa.String(length=50), nullable=False, comment="板块类型（如'概念资金流'）"),
        sa.Column("net_amount", sa.Float(), nullable=False, comment="净流入额（万元）"),
        sa.Column("inflow_amount", sa.Float(), nullable=False, comment="流入额（万元）"),
        sa.Column("outflow_amount", sa.Float(), nullable=False, comment="流出额（万元）"),
        sa.Column("pct_chg", sa.Float(), nullable=False, comment="板块涨跌幅（百分比）"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_date", "sector_name", "sector_type", name="uq_sector_capital_flow"
        ),
    )
    op.create_index(
        op.f("ix_de_sector_capital_flow_id"), "de_sector_capital_flow", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_de_sector_capital_flow_trade_date"),
        "de_sector_capital_flow",
        ["trade_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_de_sector_capital_flow_sector_name"),
        "de_sector_capital_flow",
        ["sector_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_de_sector_capital_flow_sector_type"),
        "de_sector_capital_flow",
        ["sector_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_de_sector_capital_flow_sector_type"), table_name="de_sector_capital_flow")
    op.drop_index(op.f("ix_de_sector_capital_flow_sector_name"), table_name="de_sector_capital_flow")
    op.drop_index(op.f("ix_de_sector_capital_flow_trade_date"), table_name="de_sector_capital_flow")
    op.drop_index(op.f("ix_de_sector_capital_flow_id"), table_name="de_sector_capital_flow")
    op.drop_table("de_sector_capital_flow")

    op.drop_index(op.f("ix_de_dragon_tiger_third_code"), table_name="de_dragon_tiger")
    op.drop_index(op.f("ix_de_dragon_tiger_trade_date"), table_name="de_dragon_tiger")
    op.drop_index(op.f("ix_de_dragon_tiger_id"), table_name="de_dragon_tiger")
    op.drop_table("de_dragon_tiger")

    op.drop_index(op.f("ix_de_previous_limit_up_third_code"), table_name="de_previous_limit_up")
    op.drop_index(op.f("ix_de_previous_limit_up_trade_date"), table_name="de_previous_limit_up")
    op.drop_index(op.f("ix_de_previous_limit_up_id"), table_name="de_previous_limit_up")
    op.drop_table("de_previous_limit_up")

    op.drop_index(op.f("ix_de_broken_board_pool_third_code"), table_name="de_broken_board_pool")
    op.drop_index(op.f("ix_de_broken_board_pool_trade_date"), table_name="de_broken_board_pool")
    op.drop_index(op.f("ix_de_broken_board_pool_id"), table_name="de_broken_board_pool")
    op.drop_table("de_broken_board_pool")

    op.drop_index(op.f("ix_de_limit_up_pool_third_code"), table_name="de_limit_up_pool")
    op.drop_index(op.f("ix_de_limit_up_pool_trade_date"), table_name="de_limit_up_pool")
    op.drop_index(op.f("ix_de_limit_up_pool_id"), table_name="de_limit_up_pool")
    op.drop_table("de_limit_up_pool")
