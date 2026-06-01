import pandas as pd

import akshare as ak

from src.data_fetcher import fetch_with_cache

class Screener:
    def __init__(self):
        # 基础筛选条件 (放宽ROE要求，交由AI深度判断困境反转)
        self.min_roe = 10.0
        self.min_growth = 20.0
        self.max_debt_ratio = 50.0
        self.min_cash_profit_ratio = 0.8

    def screen_technical(self, symbol, target_date=None, mode='value'):
        """
        Technical Screen with Dual Engines:
        mode 'value': Fundamental Pullback (缩量回踩 MA20/30) - For white horses.
        mode 'momentum': Breakout/Surge (近5日异动大阳线) - For hot sectors.
        """
        try:
            df = fetch_with_cache(f"hist_a_{symbol}", ak.stock_zh_a_hist, expiry_hours=24, symbol=symbol, period="daily", adjust="qfq")
            
            if target_date:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df[df['日期'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 60: return False, "数据不足60天"
            
            # 流动性基础过滤：近5日平均成交额大于 5000 万
            avg_turnover_5d = df.iloc[-5:]['成交额'].mean()
            if avg_turnover_5d < 50_000_000:
                return False, f"流动性不足 (日均成交<5000万)"

            latest_price = df.iloc[-1]['收盘']
            latest_vol = df.iloc[-1]['成交量']
            ma20 = df.iloc[-20:]['收盘'].mean()
            ma60 = df.iloc[-60:]['收盘'].mean()
            vol_ma5 = df.iloc[-5:]['成交量'].mean()
            
            if mode == 'value':
                # 白马回踩引擎：大趋势向上(MA60向上或价格>MA60)，近期回调到 MA20 附近(乖离率极小) 且 显著缩量(洗盘结束)
                ma60_10d_ago = df.iloc[-70:-10]['收盘'].mean()
                is_uptrend = ma60 > ma60_10d_ago or latest_price > ma60
                
                bias_ma20 = abs(latest_price - ma20) / ma20
                is_pullback = bias_ma20 < 0.03  # 距离MA20不到3%
                is_shrinking = latest_vol < vol_ma5 * 0.8 # 明显缩量
                
                if is_uptrend and is_pullback and is_shrinking:
                    return True, f"价值引擎: 缩量回踩企稳 (偏离MA20仅 {round(bias_ma20*100, 1)}%)"
                else:
                    return False, "未满足缩量回踩形态"
                    
            elif mode == 'momentum':
                # 游资异动引擎：近期(5日内)有标志性放量大阳线(涨幅>5%且放量2倍)，且当前未破坏大阳线形态
                recent_5d = df.iloc[-5:]
                recent_30d_vol_avg = df.iloc[-30:]['成交量'].mean()
                
                has_surge = False
                for _, row in recent_5d.iterrows():
                    pct_change = (row['收盘'] - row['开盘']) / row['开盘']
                    vol_ratio = row['成交量'] / recent_30d_vol_avg
                    if pct_change > 0.05 and vol_ratio > 1.5:
                        has_surge = True
                        break
                        
                if has_surge and latest_price > ma20:
                    return True, f"游资引擎: 近期有放量大阳线异动，趋势保持良好"
                else:
                    return False, "缺乏明显的资金抢筹异动"
                    
            return False, "未知模式"
        except Exception as e:
            return False, f"技术面分析失败: {str(e)}"

    def get_stocks_in_sector(self, sector_name, sector_label=None):
        """获取板块内的个股代码"""
        try:
            # 优先尝试 Sina 接口 (无反爬限制，解决东财被封锁导致选票池为空的问题)
            if sector_label:
                df = ak.stock_sector_detail(sector=sector_label)
                if df is not None and not df.empty:
                    df = df.rename(columns={'code': '代码', 'name': '名称'})
                    return df[['代码', '名称']]
                    
            # 备选：使用东财板块成分股接口
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            return df[['代码', '名称']]
        except:
            return None

    def screen_a_share(self, df, min_roe=None):
        """
        Screen A-share based on abstract data.
        Indicators: ROE, Growth, Cash-to-Profit Ratio.
        """
        if df is None or df.empty:
            return False, "无数据"
        
        target_roe = min_roe if min_roe is not None else self.min_roe
        
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
            
            if roe and roe >= target_roe:
                reasons.append(f"ROE: {roe}%")
            else:
                passed = False
                reasons.append(f"ROE不达标: {roe}% (要求>={target_roe}%)")

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

    def screen_hk_technical(self, symbol, target_date=None):
        """
        HK Technical Screen (Mean Reversion & Value Investing):
        1. Liquidity: 20-day avg turnover > 100M HKD
        2. Trend: Price < MA60 (Mean Reversion) & RSI(14) < 40 (Oversold) OR Price near MA250 (Support)
        """
        try:
            # 使用新浪接口防止被封
            df = fetch_with_cache(f"hist_hk_{symbol}", ak.stock_hk_daily, expiry_hours=24, symbol=symbol, adjust="qfq")
            
            if target_date:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 60: return False, "数据不足60天"
            
            # 流动性过滤：近20日平均成交额大于1亿
            avg_turnover_20d = df.iloc[-20:]['amount'].mean()
            if avg_turnover_20d < 100_000_000:
                return False, f"流动性不足 (日均成交<1亿港币)"

            latest_price = df.iloc[-1]['close']
            ma60 = df.iloc[-60:]['close'].mean()
            
            # 简单 RSI 计算
            delta = df['close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            rsi_14 = 100 - (100 / (1 + rs))
            latest_rsi = rsi_14.iloc[-1]
            
            # 左侧均值回归逻辑：在半年线(60日)下方，且出现超卖信号(RSI<40)
            if latest_price < ma60 and latest_rsi < 40:
                return True, f"左侧潜伏点 (流动性>1亿, 在MA60下方且RSI={round(latest_rsi,1)} 超卖)"
            else:
                return False, f"未见严重超卖或价格过高 (RSI={round(latest_rsi,1)})"
        except Exception as e:
            return False, f"技术面分析失败: {str(e)}"

    def screen_hk_share(self, df, min_roe=None):
        """
        Screen HK stock based on Value indicators (Dividend Yield & PB).
        """
        if df is None or df.empty:
            return False, "无数据"
        
        try:
            latest = df.iloc[0]
            
            # 获取港股红利与估值指标 (根据 akshare 字段调整，部分可能需容错)
            # 注意: ak.stock_hk_spot_em() 或 ak.stock_hk_indicator_em() 提供的字段可能有差异
            # 这里尝试获取常见字段
            div_yield = latest.get('股息率(%)', latest.get('股息率', 0))
            pb = latest.get('市净率', latest.get('PB', 1.0))
            
            div_yield = float(div_yield) if pd.notna(div_yield) and str(div_yield).replace('.','',1).isdigit() else 0
            pb = float(pb) if pd.notna(pb) and str(pb).replace('.','',1).isdigit() else 1.0
            
            reasons = []
            passed = True
            
            # 核心1：股息率防守
            if div_yield >= 4.0:
                reasons.append(f"高股息: {div_yield}%")
            else:
                passed = False
                reasons.append(f"股息率过低: {div_yield}% (要求>=4%)")
                
            # 核心2：估值保护 (防老千股，也防泡沫股)
            if 0.3 <= pb <= 1.5:
                reasons.append(f"估值合理: PB={pb}")
            else:
                passed = False
                reasons.append(f"估值不符合要求: PB={pb} (要求 0.3-1.5)")

            return passed, ", ".join(reasons)
        except Exception as e:
            return False, f"筛选出错: {e}"
