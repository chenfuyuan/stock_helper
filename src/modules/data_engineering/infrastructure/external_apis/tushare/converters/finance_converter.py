from typing import List, Optional

import pandas as pd
from loguru import logger

from src.modules.data_engineering.domain.model.financial_report import (
    StockFinance,
)


class StockFinanceAssembler:
    """
    股票财务指标数据装配器
    """

    @staticmethod
    def to_domain_list(df: pd.DataFrame) -> List[StockFinance]:
        finances = []
        if df is None or df.empty:
            return finances

        df = df.where(pd.notnull(df), None)

        for _, row in df.iterrows():
            try:
                finance = StockFinanceAssembler._row_to_entity(row)
                if finance:
                    finances.append(finance)
            except Exception as e:
                logger.warning(f"财务指标转换失败: {row.get('ts_code', 'unknown')} - {str(e)}")
                continue

        return finances

    @staticmethod
    def _row_to_entity(row: pd.Series) -> Optional[StockFinance]:
        def parse_date(date_str):
            if not date_str:
                return None
            try:
                return pd.to_datetime(date_str).date()
            except ValueError:
                return None

        # Tushare ts_code -> third_code
        third_code = row.get("ts_code")
        ann_date = parse_date(row.get("ann_date"))
        end_date = parse_date(row.get("end_date"))

        if not third_code or not ann_date or not end_date:
            return None

        return StockFinance(
            third_code=third_code,
            ann_date=ann_date,
            end_date=end_date,
            eps=row.get("eps"),
            dt_eps=row.get("dt_eps"),
            total_revenue_ps=row.get("total_revenue_ps"),
            revenue_ps=row.get("revenue_ps"),
            capital_rese_ps=row.get("capital_rese_ps"),
            surplus_rese_ps=row.get("surplus_rese_ps"),
            undist_profit_ps=row.get("undist_profit_ps"),
            extra_item=row.get("extra_item"),
            profit_dedt=row.get("profit_dedt"),
            gross_margin=row.get("gross_margin"),
            current_ratio=row.get("current_ratio"),
            quick_ratio=row.get("quick_ratio"),
            cash_ratio=row.get("cash_ratio"),
            inv_turn=row.get("inv_turn"),
            ar_turn=row.get("ar_turn"),
            ca_turn=row.get("ca_turn"),
            fa_turn=row.get("fa_turn"),
            assets_turn=row.get("assets_turn"),
            invturn_days=row.get("invturn_days"),
            arturn_days=row.get("arturn_days"),
            op_income=row.get("op_income"),
            valuechange_income=row.get("valuechange_income"),
            interst_income=row.get("interst_income"),
            daa=row.get("daa"),
            ebit=row.get("ebit"),
            ebitda=row.get("ebitda"),
            fcff=row.get("fcff"),
            fcfe=row.get("fcfe"),
            current_exint=row.get("current_exint"),
            noncurrent_exint=row.get("noncurrent_exint"),
            interestdebt=row.get("interestdebt"),
            netdebt=row.get("netdebt"),
            tangible_asset=row.get("tangible_asset"),
            working_capital=row.get("working_capital"),
            networking_capital=row.get("networking_capital"),
            invest_capital=row.get("invest_capital"),
            retained_earnings=row.get("retained_earnings"),
            diluted2_eps=row.get("diluted2_eps"),
            bps=row.get("bps"),
            ocfps=row.get("ocfps"),
            retainedps=row.get("retainedps"),
            cfps=row.get("cfps"),
            ebit_ps=row.get("ebit_ps"),
            fcff_ps=row.get("fcff_ps"),
            fcfe_ps=row.get("fcfe_ps"),
            netprofit_margin=row.get("netprofit_margin"),
            grossprofit_margin=row.get("grossprofit_margin"),
            cogs_of_sales=row.get("cogs_of_sales"),
            expense_of_sales=row.get("expense_of_sales"),
            profit_to_gr=row.get("profit_to_gr"),
            saleexp_to_gr=row.get("saleexp_to_gr"),
            adminexp_of_gr=row.get("adminexp_of_gr"),
            finaexp_of_gr=row.get("finaexp_of_gr"),
            impai_ttm=row.get("impai_ttm"),
            gc_of_gr=row.get("gc_of_gr"),
            op_of_gr=row.get("op_of_gr"),
            ebit_of_gr=row.get("ebit_of_gr"),
            roe=row.get("roe"),
            roe_waa=row.get("roe_waa"),
            roe_dt=row.get("roe_dt"),
            roa=row.get("roa"),
            npta=row.get("npta"),
            roic=row.get("roic"),
            roe_yearly=row.get("roe_yearly"),
            roa2_yearly=row.get("roa2_yearly"),
            roe_avg=row.get("roe_avg"),
            opincome_of_ebt=row.get("opincome_of_ebt"),
            investincome_of_ebt=row.get("investincome_of_ebt"),
            n_op_profit_of_ebt=row.get("n_op_profit_of_ebt"),
            tax_to_ebt=row.get("tax_to_ebt"),
            dtprofit_to_profit=row.get("dtprofit_to_profit"),
            salescash_to_or=row.get("salescash_to_or"),
            ocf_to_or=row.get("ocf_to_or"),
            ocf_to_opincome=row.get("ocf_to_opincome"),
            capitalized_to_da=row.get("capitalized_to_da"),
            debt_to_assets=row.get("debt_to_assets"),
            assets_to_eqt=row.get("assets_to_eqt"),
            dp_assets_to_eqt=row.get("dp_assets_to_eqt"),
            ca_to_assets=row.get("ca_to_assets"),
            nca_to_assets=row.get("nca_to_assets"),
            tbassets_to_totalassets=row.get("tbassets_to_totalassets"),
            int_to_talcap=row.get("int_to_talcap"),
            eqt_to_talcapital=row.get("eqt_to_talcapital"),
            currentdebt_to_debt=row.get("currentdebt_to_debt"),
            longdeb_to_debt=row.get("longdeb_to_debt"),
            ocf_to_shortdebt=row.get("ocf_to_shortdebt"),
            debt_to_eqt=row.get("debt_to_eqt"),
            source="tushare",
        )
