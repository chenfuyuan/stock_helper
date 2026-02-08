from sqlalchemy import Column, String, Date, Float
from app.infrastructure.db.base import Base

class StockFinanceModel(Base):
    """
    股票财务指标数据库模型
    Stock Financial Indicator Database Model
    """
    __tablename__ = "stock_finance"

    third_code = Column(String(20), primary_key=True, nullable=False, index=True, comment="第三方代码")
    ann_date = Column(Date, primary_key=True, nullable=False, index=True, comment="公告日期")
    end_date = Column(Date, primary_key=True, nullable=False, index=True, comment="报告期")
    
    # 每股指标
    eps = Column(Float, nullable=True, comment="基本每股收益")
    dt_eps = Column(Float, nullable=True, comment="稀释每股收益")
    total_revenue_ps = Column(Float, nullable=True, comment="每股营业总收入")
    revenue_ps = Column(Float, nullable=True, comment="每股营业收入")
    capital_rese_ps = Column(Float, nullable=True, comment="每股资本公积")
    surplus_rese_ps = Column(Float, nullable=True, comment="每股盈余公积")
    undist_profit_ps = Column(Float, nullable=True, comment="每股未分配利润")
    extra_item = Column(Float, nullable=True, comment="非经常性损益")
    profit_dedt = Column(Float, nullable=True, comment="扣除非经常性损益后的净利润")
    
    # 盈利能力
    gross_margin = Column(Float, nullable=True, comment="毛利率")
    current_ratio = Column(Float, nullable=True, comment="流动比率")
    quick_ratio = Column(Float, nullable=True, comment="速动比率")
    cash_ratio = Column(Float, nullable=True, comment="保守速动比率")
    
    # 营运能力
    inv_turn = Column(Float, nullable=True, comment="存货周转率")
    ar_turn = Column(Float, nullable=True, comment="应收账款周转率")
    ca_turn = Column(Float, nullable=True, comment="流动资产周转率")
    fa_turn = Column(Float, nullable=True, comment="固定资产周转率")
    assets_turn = Column(Float, nullable=True, comment="总资产周转率")
    invturn_days = Column(Float, nullable=True, comment="存货周转天数")
    arturn_days = Column(Float, nullable=True, comment="应收账款周转天数")
    
    # 偿债能力
    op_income = Column(Float, nullable=True, comment="经营活动净收益")
    valuechange_income = Column(Float, nullable=True, comment="价值变动净收益")
    interst_income = Column(Float, nullable=True, comment="利息费用")
    daa = Column(Float, nullable=True, comment="折旧与摊销")
    ebit = Column(Float, nullable=True, comment="息税前利润")
    ebitda = Column(Float, nullable=True, comment="息税折旧摊销前利润")
    
    # 现金流
    fcff = Column(Float, nullable=True, comment="企业自由现金流量")
    fcfe = Column(Float, nullable=True, comment="股权自由现金流量")
    current_exint = Column(Float, nullable=True, comment="无息流动负债")
    noncurrent_exint = Column(Float, nullable=True, comment="无息非流动负债")
    interestdebt = Column(Float, nullable=True, comment="带息债务")
    netdebt = Column(Float, nullable=True, comment="净债务")
    tangible_asset = Column(Float, nullable=True, comment="有形资产")
    working_capital = Column(Float, nullable=True, comment="营运资金")
    networking_capital = Column(Float, nullable=True, comment="营运流动资本")
    invest_capital = Column(Float, nullable=True, comment="全部投入资本")
    retained_earnings = Column(Float, nullable=True, comment="留存收益")
    diluted2_eps = Column(Float, nullable=True, comment="期末摊薄每股收益")
    bps = Column(Float, nullable=True, comment="每股净资产")
    ocfps = Column(Float, nullable=True, comment="每股经营活动产生的现金流量净额")
    retainedps = Column(Float, nullable=True, comment="每股留存收益")
    cfps = Column(Float, nullable=True, comment="每股现金流量净额")
    ebit_ps = Column(Float, nullable=True, comment="每股息税前利润")
    fcff_ps = Column(Float, nullable=True, comment="每股企业自由现金流量")
    fcfe_ps = Column(Float, nullable=True, comment="每股股权自由现金流量")

    # 财务比率
    netprofit_margin = Column(Float, nullable=True, comment="销售净利率")
    grossprofit_margin = Column(Float, nullable=True, comment="销售毛利率")
    cogs_of_sales = Column(Float, nullable=True, comment="销售成本率")
    expense_of_sales = Column(Float, nullable=True, comment="销售期间费用率")
    profit_to_gr = Column(Float, nullable=True, comment="净利润/营业总收入")
    saleexp_to_gr = Column(Float, nullable=True, comment="销售费用/营业总收入")
    adminexp_of_gr = Column(Float, nullable=True, comment="管理费用/营业总收入")
    finaexp_of_gr = Column(Float, nullable=True, comment="财务费用/营业总收入")
    impai_ttm = Column(Float, nullable=True, comment="资产减值损失/营业总收入")
    gc_of_gr = Column(Float, nullable=True, comment="营业总成本/营业总收入")
    op_of_gr = Column(Float, nullable=True, comment="营业利润/营业总收入")
    ebit_of_gr = Column(Float, nullable=True, comment="息税前利润/营业总收入")
    roe = Column(Float, nullable=True, comment="净资产收益率")
    roe_waa = Column(Float, nullable=True, comment="加权平均净资产收益率")
    roe_dt = Column(Float, nullable=True, comment="净资产收益率(扣除非经常损益)")
    roa = Column(Float, nullable=True, comment="总资产报酬率")
    npta = Column(Float, nullable=True, comment="总资产净利润")
    roic = Column(Float, nullable=True, comment="投入资本回报率")
    roe_yearly = Column(Float, nullable=True, comment="年化净资产收益率")
    roa2_yearly = Column(Float, nullable=True, comment="年化总资产报酬率")
    roe_avg = Column(Float, nullable=True, comment="平均净资产收益率")
    opincome_of_ebt = Column(Float, nullable=True, comment="经营活动净收益/利润总额")
    investincome_of_ebt = Column(Float, nullable=True, comment="价值变动净收益/利润总额")
    n_op_profit_of_ebt = Column(Float, nullable=True, comment="营业外收支净额/利润总额")
    tax_to_ebt = Column(Float, nullable=True, comment="所得税/利润总额")
    dtprofit_to_profit = Column(Float, nullable=True, comment="扣除非经常损益后的净利润/净利润")
    salescash_to_or = Column(Float, nullable=True, comment="销售商品提供劳务收到的现金/营业收入")
    ocf_to_or = Column(Float, nullable=True, comment="经营活动产生的现金流量净额/营业收入")
    ocf_to_opincome = Column(Float, nullable=True, comment="经营活动产生的现金流量净额/经营活动净收益")
    capitalized_to_da = Column(Float, nullable=True, comment="资本支出/折旧和摊销")
    debt_to_assets = Column(Float, nullable=True, comment="资产负债率")
    assets_to_eqt = Column(Float, nullable=True, comment="权益乘数")
    dp_assets_to_eqt = Column(Float, nullable=True, comment="权益乘数(杜邦分析)")
    ca_to_assets = Column(Float, nullable=True, comment="流动资产/总资产")
    nca_to_assets = Column(Float, nullable=True, comment="非流动资产/总资产")
    tbassets_to_totalassets = Column(Float, nullable=True, comment="有形资产/总资产")
    int_to_talcap = Column(Float, nullable=True, comment="带息债务/全部投入资本")
    eqt_to_talcapital = Column(Float, nullable=True, comment="归属于母公司的股东权益/全部投入资本")
    currentdebt_to_debt = Column(Float, nullable=True, comment="流动负债/负债合计")
    longdeb_to_debt = Column(Float, nullable=True, comment="非流动负债/负债合计")
    ocf_to_shortdebt = Column(Float, nullable=True, comment="经营活动产生的现金流量净额/流动负债")
    debt_to_eqt = Column(Float, nullable=True, comment="产权比率")
    
    source = Column(String(20), nullable=True, default="tushare", comment="数据来源")
