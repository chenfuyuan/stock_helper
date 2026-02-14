from datetime import date
from typing import Optional

from pydantic import ConfigDict, Field

from src.shared.domain.base_entity import BaseEntity


class StockFinance(BaseEntity):
    """
    股票财务指标领域实体
    Stock Financial Indicator Domain Entity
    """

    third_code: str = Field(..., description="第三方系统代码 (如 Tushare 的 ts_code)")
    ann_date: date = Field(..., description="公告日期")
    end_date: date = Field(..., description="报告期")

    # 每股指标
    eps: Optional[float] = Field(None, description="基本每股收益")
    dt_eps: Optional[float] = Field(None, description="稀释每股收益")
    total_revenue_ps: Optional[float] = Field(None, description="每股营业总收入")
    revenue_ps: Optional[float] = Field(None, description="每股营业收入")
    capital_rese_ps: Optional[float] = Field(None, description="每股资本公积")
    surplus_rese_ps: Optional[float] = Field(None, description="每股盈余公积")
    undist_profit_ps: Optional[float] = Field(None, description="每股未分配利润")
    extra_item: Optional[float] = Field(None, description="非经常性损益")
    profit_dedt: Optional[float] = Field(None, description="扣除非经常性损益后的净利润")

    # 盈利能力
    gross_margin: Optional[float] = Field(None, description="毛利率")
    current_ratio: Optional[float] = Field(None, description="流动比率")
    quick_ratio: Optional[float] = Field(None, description="速动比率")
    cash_ratio: Optional[float] = Field(None, description="保守速动比率")

    # 营运能力
    inv_turn: Optional[float] = Field(None, description="存货周转率")
    ar_turn: Optional[float] = Field(None, description="应收账款周转率")
    ca_turn: Optional[float] = Field(None, description="流动资产周转率")
    fa_turn: Optional[float] = Field(None, description="固定资产周转率")
    assets_turn: Optional[float] = Field(None, description="总资产周转率")
    invturn_days: Optional[float] = Field(None, description="存货周转天数")
    arturn_days: Optional[float] = Field(None, description="应收账款周转天数")

    # 偿债能力
    op_income: Optional[float] = Field(None, description="经营活动净收益")
    valuechange_income: Optional[float] = Field(None, description="价值变动净收益")
    interst_income: Optional[float] = Field(None, description="利息费用")
    daa: Optional[float] = Field(None, description="折旧与摊销")
    ebit: Optional[float] = Field(None, description="息税前利润")
    ebitda: Optional[float] = Field(None, description="息税折旧摊销前利润")

    # 现金流
    fcff: Optional[float] = Field(None, description="企业自由现金流量")
    fcfe: Optional[float] = Field(None, description="股权自由现金流量")
    current_exint: Optional[float] = Field(None, description="无息流动负债")
    noncurrent_exint: Optional[float] = Field(None, description="无息非流动负债")
    interestdebt: Optional[float] = Field(None, description="带息债务")
    netdebt: Optional[float] = Field(None, description="净债务")
    tangible_asset: Optional[float] = Field(None, description="有形资产")
    working_capital: Optional[float] = Field(None, description="营运资金")
    networking_capital: Optional[float] = Field(None, description="营运流动资本")
    invest_capital: Optional[float] = Field(None, description="全部投入资本")
    retained_earnings: Optional[float] = Field(None, description="留存收益")
    diluted2_eps: Optional[float] = Field(None, description="期末摊薄每股收益")
    bps: Optional[float] = Field(None, description="每股净资产")
    ocfps: Optional[float] = Field(None, description="每股经营活动产生的现金流量净额")
    retainedps: Optional[float] = Field(None, description="每股留存收益")
    cfps: Optional[float] = Field(None, description="每股现金流量净额")
    ebit_ps: Optional[float] = Field(None, description="每股息税前利润")
    fcff_ps: Optional[float] = Field(None, description="每股企业自由现金流量")
    fcfe_ps: Optional[float] = Field(None, description="每股股权自由现金流量")

    # 财务比率
    netprofit_margin: Optional[float] = Field(None, description="销售净利率")
    grossprofit_margin: Optional[float] = Field(None, description="销售毛利率")
    cogs_of_sales: Optional[float] = Field(None, description="销售成本率")
    expense_of_sales: Optional[float] = Field(None, description="销售期间费用率")
    profit_to_gr: Optional[float] = Field(None, description="净利润/营业总收入")
    saleexp_to_gr: Optional[float] = Field(None, description="销售费用/营业总收入")
    adminexp_of_gr: Optional[float] = Field(None, description="管理费用/营业总收入")
    finaexp_of_gr: Optional[float] = Field(None, description="财务费用/营业总收入")
    impai_ttm: Optional[float] = Field(None, description="资产减值损失/营业总收入")
    gc_of_gr: Optional[float] = Field(None, description="营业总成本/营业总收入")
    op_of_gr: Optional[float] = Field(None, description="营业利润/营业总收入")
    ebit_of_gr: Optional[float] = Field(None, description="息税前利润/营业总收入")
    roe: Optional[float] = Field(None, description="净资产收益率")
    roe_waa: Optional[float] = Field(None, description="加权平均净资产收益率")
    roe_dt: Optional[float] = Field(None, description="净资产收益率(扣除非经常损益)")
    roa: Optional[float] = Field(None, description="总资产报酬率")
    npta: Optional[float] = Field(None, description="总资产净利润")
    roic: Optional[float] = Field(None, description="投入资本回报率")
    roe_yearly: Optional[float] = Field(None, description="年化净资产收益率")
    roa2_yearly: Optional[float] = Field(None, description="年化总资产报酬率")
    roe_avg: Optional[float] = Field(None, description="平均净资产收益率")
    opincome_of_ebt: Optional[float] = Field(None, description="经营活动净收益/利润总额")
    investincome_of_ebt: Optional[float] = Field(None, description="价值变动净收益/利润总额")
    n_op_profit_of_ebt: Optional[float] = Field(None, description="营业外收支净额/利润总额")
    tax_to_ebt: Optional[float] = Field(None, description="所得税/利润总额")
    dtprofit_to_profit: Optional[float] = Field(None, description="扣除非经常损益后的净利润/净利润")
    salescash_to_or: Optional[float] = Field(
        None, description="销售商品提供劳务收到的现金/营业收入"
    )
    ocf_to_or: Optional[float] = Field(None, description="经营活动产生的现金流量净额/营业收入")
    ocf_to_opincome: Optional[float] = Field(
        None, description="经营活动产生的现金流量净额/经营活动净收益"
    )
    capitalized_to_da: Optional[float] = Field(None, description="资本支出/折旧和摊销")
    debt_to_assets: Optional[float] = Field(None, description="资产负债率")
    assets_to_eqt: Optional[float] = Field(None, description="权益乘数")
    dp_assets_to_eqt: Optional[float] = Field(None, description="权益乘数(杜邦分析)")
    ca_to_assets: Optional[float] = Field(None, description="流动资产/总资产")
    nca_to_assets: Optional[float] = Field(None, description="非流动资产/总资产")
    tbassets_to_totalassets: Optional[float] = Field(None, description="有形资产/总资产")
    int_to_talcap: Optional[float] = Field(None, description="带息债务/全部投入资本")
    eqt_to_talcapital: Optional[float] = Field(
        None, description="归属于母公司的股东权益/全部投入资本"
    )
    currentdebt_to_debt: Optional[float] = Field(None, description="流动负债/负债合计")
    longdeb_to_debt: Optional[float] = Field(None, description="非流动负债/负债合计")
    ocf_to_shortdebt: Optional[float] = Field(
        None, description="经营活动产生的现金流量净额/流动负债"
    )
    debt_to_eqt: Optional[float] = Field(None, description="产权比率")

    source: str = Field("tushare", description="数据来源")

    model_config = ConfigDict(from_attributes=True)
