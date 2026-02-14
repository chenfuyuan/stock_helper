"""initial_schema

按本项目 ORM 模型生成初始数据库表：stock_info、stock_daily、stock_finance、llm_configs。

Revision ID: c0ff00000001
Revises:
Create Date: 2026-02-11

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c0ff00000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----- stock_info（data_engineering：股票基础信息） -----
    op.create_table(
        "stock_info",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="第三方代码"),
        sa.Column("symbol", sa.String(length=10), nullable=False, comment="股票代码"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="股票名称"),
        sa.Column("area", sa.String(length=50), nullable=True, comment="所在地域"),
        sa.Column("industry", sa.String(length=50), nullable=True, comment="所属行业"),
        sa.Column("market", sa.String(length=20), nullable=True, comment="市场类型"),
        sa.Column("list_date", sa.Date(), nullable=True, comment="上市日期"),
        sa.Column("fullname", sa.String(length=200), nullable=True, comment="股票全称"),
        sa.Column("enname", sa.String(length=200), nullable=True, comment="英文全称"),
        sa.Column("cnspell", sa.String(length=50), nullable=True, comment="拼音缩写"),
        sa.Column("exchange", sa.String(length=20), nullable=True, comment="交易所代码"),
        sa.Column("curr_type", sa.String(length=20), nullable=True, comment="交易货币"),
        sa.Column(
            "list_status",
            sa.String(length=10),
            nullable=True,
            comment="上市状态 L上市 D退市 P暂停上市",
        ),
        sa.Column("delist_date", sa.Date(), nullable=True, comment="退市日期"),
        sa.Column(
            "is_hs",
            sa.String(length=10),
            nullable=True,
            comment="是否沪深港通标的，N否 H沪股通 S深股通",
        ),
        sa.Column("source", sa.String(length=20), nullable=True, comment="数据来源"),
        sa.Column(
            "last_finance_sync_date", sa.Date(), nullable=True, comment="上次财务数据同步时间"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stock_info_id"), "stock_info", ["id"], unique=False)
    op.create_index(op.f("ix_stock_info_industry"), "stock_info", ["industry"], unique=False)
    op.create_index(op.f("ix_stock_info_market"), "stock_info", ["market"], unique=False)
    op.create_index(op.f("ix_stock_info_symbol"), "stock_info", ["symbol"], unique=True)
    op.create_index(op.f("ix_stock_info_third_code"), "stock_info", ["third_code"], unique=True)

    # ----- stock_daily（data_engineering：日线行情） -----
    op.create_table(
        "stock_daily",
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="第三方代码"),
        sa.Column("trade_date", sa.Date(), nullable=False, comment="交易日期"),
        sa.Column("open", sa.Float(), nullable=True, comment="开盘价"),
        sa.Column("high", sa.Float(), nullable=True, comment="最高价"),
        sa.Column("low", sa.Float(), nullable=True, comment="最低价"),
        sa.Column("close", sa.Float(), nullable=True, comment="收盘价"),
        sa.Column("pre_close", sa.Float(), nullable=True, comment="昨收价"),
        sa.Column("change", sa.Float(), nullable=True, comment="涨跌额"),
        sa.Column("pct_chg", sa.Float(), nullable=True, comment="涨跌幅"),
        sa.Column("vol", sa.Float(), nullable=True, comment="成交量"),
        sa.Column("amount", sa.Float(), nullable=True, comment="成交额"),
        sa.Column("adj_factor", sa.Float(), nullable=True, comment="复权因子"),
        sa.Column("turnover_rate", sa.Float(), nullable=True, comment="换手率"),
        sa.Column("turnover_rate_f", sa.Float(), nullable=True, comment="换手率(自由流通股)"),
        sa.Column("volume_ratio", sa.Float(), nullable=True, comment="量比"),
        sa.Column("pe", sa.Float(), nullable=True, comment="市盈率"),
        sa.Column("pe_ttm", sa.Float(), nullable=True, comment="市盈率TTM"),
        sa.Column("pb", sa.Float(), nullable=True, comment="市净率"),
        sa.Column("ps", sa.Float(), nullable=True, comment="市销率"),
        sa.Column("ps_ttm", sa.Float(), nullable=True, comment="市销率TTM"),
        sa.Column("dv_ratio", sa.Float(), nullable=True, comment="股息率"),
        sa.Column("dv_ttm", sa.Float(), nullable=True, comment="股息率TTM"),
        sa.Column("total_share", sa.Float(), nullable=True, comment="总股本"),
        sa.Column("float_share", sa.Float(), nullable=True, comment="流通股本"),
        sa.Column("free_share", sa.Float(), nullable=True, comment="自由流通股本"),
        sa.Column("total_mv", sa.Float(), nullable=True, comment="总市值"),
        sa.Column("circ_mv", sa.Float(), nullable=True, comment="流通市值"),
        sa.Column("source", sa.String(length=20), nullable=True, comment="数据来源"),
        sa.PrimaryKeyConstraint("third_code", "trade_date"),
    )
    op.create_index(op.f("ix_stock_daily_third_code"), "stock_daily", ["third_code"], unique=False)
    op.create_index(op.f("ix_stock_daily_trade_date"), "stock_daily", ["trade_date"], unique=False)

    # ----- stock_finance（data_engineering：财务指标） -----
    op.create_table(
        "stock_finance",
        sa.Column("third_code", sa.String(length=20), nullable=False, comment="第三方代码"),
        sa.Column("ann_date", sa.Date(), nullable=False, comment="公告日期"),
        sa.Column("end_date", sa.Date(), nullable=False, comment="报告期"),
        sa.Column("eps", sa.Float(), nullable=True, comment="基本每股收益"),
        sa.Column("dt_eps", sa.Float(), nullable=True, comment="稀释每股收益"),
        sa.Column("total_revenue_ps", sa.Float(), nullable=True, comment="每股营业总收入"),
        sa.Column("revenue_ps", sa.Float(), nullable=True, comment="每股营业收入"),
        sa.Column("capital_rese_ps", sa.Float(), nullable=True, comment="每股资本公积"),
        sa.Column("surplus_rese_ps", sa.Float(), nullable=True, comment="每股盈余公积"),
        sa.Column("undist_profit_ps", sa.Float(), nullable=True, comment="每股未分配利润"),
        sa.Column("extra_item", sa.Float(), nullable=True, comment="非经常性损益"),
        sa.Column("profit_dedt", sa.Float(), nullable=True, comment="扣除非经常性损益后的净利润"),
        sa.Column("gross_margin", sa.Float(), nullable=True, comment="毛利率"),
        sa.Column("current_ratio", sa.Float(), nullable=True, comment="流动比率"),
        sa.Column("quick_ratio", sa.Float(), nullable=True, comment="速动比率"),
        sa.Column("cash_ratio", sa.Float(), nullable=True, comment="保守速动比率"),
        sa.Column("inv_turn", sa.Float(), nullable=True, comment="存货周转率"),
        sa.Column("ar_turn", sa.Float(), nullable=True, comment="应收账款周转率"),
        sa.Column("ca_turn", sa.Float(), nullable=True, comment="流动资产周转率"),
        sa.Column("fa_turn", sa.Float(), nullable=True, comment="固定资产周转率"),
        sa.Column("assets_turn", sa.Float(), nullable=True, comment="总资产周转率"),
        sa.Column("invturn_days", sa.Float(), nullable=True, comment="存货周转天数"),
        sa.Column("arturn_days", sa.Float(), nullable=True, comment="应收账款周转天数"),
        sa.Column("op_income", sa.Float(), nullable=True, comment="经营活动净收益"),
        sa.Column("valuechange_income", sa.Float(), nullable=True, comment="价值变动净收益"),
        sa.Column("interst_income", sa.Float(), nullable=True, comment="利息费用"),
        sa.Column("daa", sa.Float(), nullable=True, comment="折旧与摊销"),
        sa.Column("ebit", sa.Float(), nullable=True, comment="息税前利润"),
        sa.Column("ebitda", sa.Float(), nullable=True, comment="息税折旧摊销前利润"),
        sa.Column("fcff", sa.Float(), nullable=True, comment="企业自由现金流量"),
        sa.Column("fcfe", sa.Float(), nullable=True, comment="股权自由现金流量"),
        sa.Column("current_exint", sa.Float(), nullable=True, comment="无息流动负债"),
        sa.Column("noncurrent_exint", sa.Float(), nullable=True, comment="无息非流动负债"),
        sa.Column("interestdebt", sa.Float(), nullable=True, comment="带息债务"),
        sa.Column("netdebt", sa.Float(), nullable=True, comment="净债务"),
        sa.Column("tangible_asset", sa.Float(), nullable=True, comment="有形资产"),
        sa.Column("working_capital", sa.Float(), nullable=True, comment="营运资金"),
        sa.Column("networking_capital", sa.Float(), nullable=True, comment="营运流动资本"),
        sa.Column("invest_capital", sa.Float(), nullable=True, comment="全部投入资本"),
        sa.Column("retained_earnings", sa.Float(), nullable=True, comment="留存收益"),
        sa.Column("diluted2_eps", sa.Float(), nullable=True, comment="期末摊薄每股收益"),
        sa.Column("bps", sa.Float(), nullable=True, comment="每股净资产"),
        sa.Column("ocfps", sa.Float(), nullable=True, comment="每股经营活动产生的现金流量净额"),
        sa.Column("retainedps", sa.Float(), nullable=True, comment="每股留存收益"),
        sa.Column("cfps", sa.Float(), nullable=True, comment="每股现金流量净额"),
        sa.Column("ebit_ps", sa.Float(), nullable=True, comment="每股息税前利润"),
        sa.Column("fcff_ps", sa.Float(), nullable=True, comment="每股企业自由现金流量"),
        sa.Column("fcfe_ps", sa.Float(), nullable=True, comment="每股股权自由现金流量"),
        sa.Column("netprofit_margin", sa.Float(), nullable=True, comment="销售净利率"),
        sa.Column("grossprofit_margin", sa.Float(), nullable=True, comment="销售毛利率"),
        sa.Column("cogs_of_sales", sa.Float(), nullable=True, comment="销售成本率"),
        sa.Column("expense_of_sales", sa.Float(), nullable=True, comment="销售期间费用率"),
        sa.Column("profit_to_gr", sa.Float(), nullable=True, comment="净利润/营业总收入"),
        sa.Column("saleexp_to_gr", sa.Float(), nullable=True, comment="销售费用/营业总收入"),
        sa.Column("adminexp_of_gr", sa.Float(), nullable=True, comment="管理费用/营业总收入"),
        sa.Column("finaexp_of_gr", sa.Float(), nullable=True, comment="财务费用/营业总收入"),
        sa.Column("impai_ttm", sa.Float(), nullable=True, comment="资产减值损失/营业总收入"),
        sa.Column("gc_of_gr", sa.Float(), nullable=True, comment="营业总成本/营业总收入"),
        sa.Column("op_of_gr", sa.Float(), nullable=True, comment="营业利润/营业总收入"),
        sa.Column("ebit_of_gr", sa.Float(), nullable=True, comment="息税前利润/营业总收入"),
        sa.Column("roe", sa.Float(), nullable=True, comment="净资产收益率"),
        sa.Column("roe_waa", sa.Float(), nullable=True, comment="加权平均净资产收益率"),
        sa.Column("roe_dt", sa.Float(), nullable=True, comment="净资产收益率(扣除非经常损益)"),
        sa.Column("roa", sa.Float(), nullable=True, comment="总资产报酬率"),
        sa.Column("npta", sa.Float(), nullable=True, comment="总资产净利润"),
        sa.Column("roic", sa.Float(), nullable=True, comment="投入资本回报率"),
        sa.Column("roe_yearly", sa.Float(), nullable=True, comment="年化净资产收益率"),
        sa.Column("roa2_yearly", sa.Float(), nullable=True, comment="年化总资产报酬率"),
        sa.Column("roe_avg", sa.Float(), nullable=True, comment="平均净资产收益率"),
        sa.Column("opincome_of_ebt", sa.Float(), nullable=True, comment="经营活动净收益/利润总额"),
        sa.Column(
            "investincome_of_ebt", sa.Float(), nullable=True, comment="价值变动净收益/利润总额"
        ),
        sa.Column(
            "n_op_profit_of_ebt", sa.Float(), nullable=True, comment="营业外收支净额/利润总额"
        ),
        sa.Column("tax_to_ebt", sa.Float(), nullable=True, comment="所得税/利润总额"),
        sa.Column(
            "dtprofit_to_profit",
            sa.Float(),
            nullable=True,
            comment="扣除非经常损益后的净利润/净利润",
        ),
        sa.Column(
            "salescash_to_or",
            sa.Float(),
            nullable=True,
            comment="销售商品提供劳务收到的现金/营业收入",
        ),
        sa.Column(
            "ocf_to_or", sa.Float(), nullable=True, comment="经营活动产生的现金流量净额/营业收入"
        ),
        sa.Column(
            "ocf_to_opincome",
            sa.Float(),
            nullable=True,
            comment="经营活动产生的现金流量净额/经营活动净收益",
        ),
        sa.Column("capitalized_to_da", sa.Float(), nullable=True, comment="资本支出/折旧和摊销"),
        sa.Column("debt_to_assets", sa.Float(), nullable=True, comment="资产负债率"),
        sa.Column("assets_to_eqt", sa.Float(), nullable=True, comment="权益乘数"),
        sa.Column("dp_assets_to_eqt", sa.Float(), nullable=True, comment="权益乘数(杜邦分析)"),
        sa.Column("ca_to_assets", sa.Float(), nullable=True, comment="流动资产/总资产"),
        sa.Column("nca_to_assets", sa.Float(), nullable=True, comment="非流动资产/总资产"),
        sa.Column("tbassets_to_totalassets", sa.Float(), nullable=True, comment="有形资产/总资产"),
        sa.Column("int_to_talcap", sa.Float(), nullable=True, comment="带息债务/全部投入资本"),
        sa.Column(
            "eqt_to_talcapital",
            sa.Float(),
            nullable=True,
            comment="归属于母公司的股东权益/全部投入资本",
        ),
        sa.Column("currentdebt_to_debt", sa.Float(), nullable=True, comment="流动负债/负债合计"),
        sa.Column("longdeb_to_debt", sa.Float(), nullable=True, comment="非流动负债/负债合计"),
        sa.Column(
            "ocf_to_shortdebt",
            sa.Float(),
            nullable=True,
            comment="经营活动产生的现金流量净额/流动负债",
        ),
        sa.Column("debt_to_eqt", sa.Float(), nullable=True, comment="产权比率"),
        sa.Column("source", sa.String(length=20), nullable=True, comment="数据来源"),
        sa.PrimaryKeyConstraint("third_code", "ann_date", "end_date"),
    )
    op.create_index(op.f("ix_stock_finance_ann_date"), "stock_finance", ["ann_date"], unique=False)
    op.create_index(op.f("ix_stock_finance_end_date"), "stock_finance", ["end_date"], unique=False)
    op.create_index(
        op.f("ix_stock_finance_third_code"), "stock_finance", ["third_code"], unique=False
    )

    # ----- llm_configs（llm_platform：LLM 配置） -----
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=False),
        sa.Column("provider_type", sa.String(), nullable=False),
        sa.Column("api_key", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_configs_alias"), "llm_configs", ["alias"], unique=True)
    op.create_index(op.f("ix_llm_configs_id"), "llm_configs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_configs_id"), table_name="llm_configs")
    op.drop_index(op.f("ix_llm_configs_alias"), table_name="llm_configs")
    op.drop_table("llm_configs")

    op.drop_index(op.f("ix_stock_finance_third_code"), table_name="stock_finance")
    op.drop_index(op.f("ix_stock_finance_end_date"), table_name="stock_finance")
    op.drop_index(op.f("ix_stock_finance_ann_date"), table_name="stock_finance")
    op.drop_table("stock_finance")

    op.drop_index(op.f("ix_stock_daily_trade_date"), table_name="stock_daily")
    op.drop_index(op.f("ix_stock_daily_third_code"), table_name="stock_daily")
    op.drop_table("stock_daily")

    op.drop_index(op.f("ix_stock_info_third_code"), table_name="stock_info")
    op.drop_index(op.f("ix_stock_info_symbol"), table_name="stock_info")
    op.drop_index(op.f("ix_stock_info_market"), table_name="stock_info")
    op.drop_index(op.f("ix_stock_info_industry"), table_name="stock_info")
    op.drop_index(op.f("ix_stock_info_id"), table_name="stock_info")
    op.drop_table("stock_info")
