import pandas as pd

import akshare as ak

class Screener:
    def __init__(self):
        # Basic "10-bagger" criteria
        self.min_roe = 15.0
        self.min_growth = 20.0
        self.max_debt_ratio = 50.0
        self.min_cash_profit_ratio = 1.0

    def screen_technical(self, symbol):
        """
        Simple Technical Screen:
        1. Price > MA20 (Short-term trend)
        2. Volume is not drying up
        """
        try:
            # Note: For speed in a full-market scan, we might use spot data
            # But for a specific pick, we use historical
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            if df.empty or len(df) < 30: return False, "数据不足"
            
            latest_price = df.iloc[-1]['收盘']
            ma20 = df.iloc[-20:]['收盘'].mean()
            
            if latest_price > ma20:
                return True, f"股价处于MA20上方 ({round(latest_price,2)} > {round(ma20,2)})"
            return False, f"处于MA20下方 (趋势偏弱)"
        except:
            return False, "技术面分析失败"

    def get_stocks_in_sector(self, sector_name):
        """获取板块内的个股代码"""
        try:
            # 使用东财板块成分股接口
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            return df[['代码', '名称']]
        except:
            return None

    def screen_a_share(self, df):
        """
        Screen A-share based on abstract data.
        Indicators: ROE, Growth, Cash-to-Profit Ratio.
        """
        if df is None or df.empty:
            return False, "无数据"
        
        try:
            # Transpose for easier row access by indicator name
            # Indicators are in '指标' column
            reasons = []
            passed = True

            def get_val(name):
                # Use regex=False to avoid warnings when searching for fixed strings like '()'
                row = df[df['指标'].str.contains(name, na=False, regex=False)]
                if not row.empty:
                    val = row.iloc[0, 2] # Latest year
                    return float(val) if pd.notnull(val) else None
                return None

            # 1. ROE
            roe = get_val('净资产收益率(ROE)')
            if roe is None:
                roe = get_val('净资产收益率')
            
            if roe and roe > self.min_roe:
                reasons.append(f"ROE: {roe}%")
            else:
                passed = False
                reasons.append(f"ROE不达标: {roe}%")

            # 2. 净现比 (经营现金流 / 净利润)
            net_profit = get_val('归母净利润')
            cash_flow = get_val('经营现金流量净额')
            if net_profit and cash_flow and net_profit != 0:
                ratio = cash_flow / net_profit
                if ratio > self.min_cash_profit_ratio:
                    reasons.append(f"净现比: {round(ratio, 2)}")
                else:
                    passed = False
                    reasons.append(f"净现比低: {round(ratio, 2)}")

            # 3. 合同负债 (前瞻性)
            contract_liab = get_val('合同负债')
            if contract_liab:
                reasons.append(f"存在合同负债: {contract_liab}")

            return passed, ", ".join(reasons)
            
        except Exception as e:
            return False, f"筛选出错: {e}"

    def screen_hk_share(self, df):
        """Screen HK stock based on indicators."""
        if df is None or df.empty:
            return False, "无数据"
        
        try:
            latest = df.iloc[0]
            latest_roe = latest['ROE_AVG']
            latest_growth = latest['HOLDER_PROFIT_YOY']
            debt_ratio = latest['DEBT_ASSET_RATIO']
            
            reasons = []
            passed = True
            
            if latest_roe is not None and float(latest_roe) > self.min_roe:
                reasons.append(f"ROE: {latest_roe}%")
            else:
                passed = False
                reasons.append(f"ROE不达标: {latest_roe}%")
                
            if latest_growth is not None and float(latest_growth) > self.min_growth:
                reasons.append(f"增长: {latest_growth}%")
            else:
                passed = False
                reasons.append(f"成长性低: {latest_growth}%")

            if debt_ratio is not None and float(debt_ratio) < self.max_debt_ratio:
                reasons.append(f"负债率: {debt_ratio}%")
            else:
                passed = False
                reasons.append(f"负债过高: {debt_ratio}%")

            return passed, ", ".join(reasons)
        except Exception as e:
            return False, f"筛选出错: {e}"
