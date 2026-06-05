import akshare as ak
import pandas as pd
from src.data_fetcher import fetch_a_stock_hist_cached

class RiskManager:
    def __init__(self):
        # 激进策略（趋势跟踪）：破20日线卖出
        self.trend_ma = 20
        # 保守策略（估值/情绪）：乖离率过大或估值过高
        self.bias_threshold = 15.0 # 股价偏离MA20超过15%
        # 新增：移动止损（最高点回撤）策略
        self.trailing_stop_threshold = 10.0 # 从近期最高点回撤超过10%无条件止损
        self.lookback_days = 60 # 计算最高点的回溯天数

    def evaluate_exit_signals(self, symbol, current_price=None, target_date=None, regime=None):
        """
        评估卖出信号 (Context-Aware)
        根据当前大盘气候 (regime) 动态调整卖出条件
        """
        try:
            df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=4)
            if df.empty: return [], "无行情数据"
            
            if target_date:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df[df['日期'] <= pd.to_datetime(target_date)]
                if df.empty: return [], "无该日期之前的行情"

            if len(df) < 20: return [], "数据不足以计算防守线"

            latest = df.iloc[-1]
            close = latest['收盘']
            
            # 计算近期波动率 (ATR)
            df_atr = df.iloc[-20:].copy()
            df_atr['prev_close'] = df_atr['收盘'].shift(1)
            df_atr['tr1'] = df_atr['最高'] - df_atr['最低']
            df_atr['tr2'] = (df_atr['最高'] - df_atr['prev_close']).abs()
            df_atr['tr3'] = (df_atr['最低'] - df_atr['prev_close']).abs()
            df_atr['TR'] = df_atr[['tr1', 'tr2', 'tr3']].max(axis=1)
            atr = df_atr['TR'].iloc[-14:].mean()
            
            df['ema10'] = df['收盘'].ewm(span=10, adjust=False).mean()
            df['ema20'] = df['收盘'].ewm(span=20, adjust=False).mean()
            ema10 = df['ema10'].iloc[-1]
            ema20 = df['ema20'].iloc[-1]
            
            lookback_df = df.iloc[-self.lookback_days:] if len(df) >= self.lookback_days else df
            recent_high = lookback_df['最高'].max()
            
            triggered_signals = []
            descriptions = []

            # 环境自适应卖出逻辑
            if regime == "OSCILLATION":
                # 震荡市：布林带高抛低吸，触及上轨止盈
                df['ma20'] = df['收盘'].rolling(window=20).mean()
                df['std20'] = df['收盘'].rolling(window=20).std()
                upper_band = df['ma20'].iloc[-1] + (2 * df['std20'].iloc[-1])
                
                if close >= upper_band * 0.98:
                    triggered_signals.append("OscillationExit")
                    descriptions.append(f"🔴 【震荡市止盈】：股价({close})已触及布林带上轨({round(upper_band,2)})，建议主动止盈。")
                
                # 震荡市防守略紧
                stop_atr = 1.94
            elif regime == "SLOW_RISE":
                # 慢涨市：只要不有效跌破EMA20，忽略盘中小幅刺穿，放宽ATR
                stop_atr = 1.94
                if close < ema20:
                    triggered_signals.append("SlowRiseExit")
                    descriptions.append(f"🔴 【慢涨破坏】：股价({close})已跌破 20日均线核心支撑({round(ema20,2)})，慢牛格局结束。")
            else:
                # 正常/极端市：严格的 2.5ATR 和 EMA10 止盈
                stop_atr = 1.94
                if close < ema10:
                    triggered_signals.append("Aggressive")
                    descriptions.append(f"🔴 【止盈/趋势破坏】：股价({close}) 已跌破 10日指数均线({round(ema10, 2)})，短期动能衰退。")

            # 通用防线：吊灯止损
            chandelier_stop = recent_high - (atr * stop_atr)
            if close < chandelier_stop:
                triggered_signals.append("TrailingStop")
                descriptions.append(f"⚫ 【吊灯防线击穿】：股价({close})已跌破基于最高点计算的 {stop_atr}ATR 防守线({round(chandelier_stop,2)})，必须止损。")

            # 情绪过热：乖离率
            bias = ((close - ema20) / ema20) * 100
            if bias > self.bias_threshold:
                triggered_signals.append("Conservative")
                descriptions.append(f"🟡 【情绪过热】：股价偏离20日均线过远(乖离率 {round(bias, 2)}%)，建议减仓。")

            return triggered_signals, "\\n".join(descriptions)
        except Exception as e:
            return [], f"卖出评估出错: {e}"

    def get_rs_rating(self, symbol, target_date=None):
        """
        获取个股相对强度 (Relative Strength)
        逻辑：个股涨幅 vs 沪深300涨幅
        """
        try:
            # 简化版：计算过去20天的涨幅
            df_stock = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=4)
            df_index = ak.stock_zh_index_daily(symbol="sh000300")
            
            if target_date:
                df_stock['日期'] = pd.to_datetime(df_stock['日期'])
                df_stock = df_stock[df_stock['日期'] <= pd.to_datetime(target_date)]
                df_index['date'] = pd.to_datetime(df_index['date'])
                df_index = df_index[df_index['date'] <= pd.to_datetime(target_date)]

            df_stock = df_stock.iloc[-20:]
            df_index = df_index.iloc[-20:]
            
            stock_perf = (df_stock.iloc[-1]['收盘'] - df_stock.iloc[0]['收盘']) / df_stock.iloc[0]['收盘']
            index_perf = (df_index.iloc[-1]['close'] - df_index.iloc[0]['close']) / df_index.iloc[0]['close']
            
            rs_score = stock_perf - index_perf
            return rs_score
        except:
            return 0

    def calculate_position_size(self, symbol, risk_per_trade=0.02, max_position=0.20, target_date=None):
        """
        基于 ATR (平均真实波幅) 计算科学仓位
        """
        try:
            df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=4)
            if target_date:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df[df['日期'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 15: return max_position
            
            df = df.iloc[-15:].copy()
            df['prev_close'] = df['收盘'].shift(1)
            
            # 计算 True Range (TR)
            df['tr1'] = df['最高'] - df['最低']
            df['tr2'] = (df['最高'] - df['prev_close']).abs()
            df['tr3'] = (df['最低'] - df['prev_close']).abs()
            df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            # 计算 ATR (14日均值)
            atr = df['TR'].iloc[-14:].mean()
            latest_close = df.iloc[-1]['收盘']
            
            # 如果没有波动（极少见），返回上限
            if atr == 0: return max_position
            
            # 计算止损幅度比例 (将 1.5 倍 ATR 设为止损点)
            stop_loss_pct = (atr * 1.5) / latest_close
            
            # 建议仓位 = 愿意承担的风险 / 止损幅度
            position_size = risk_per_trade / stop_loss_pct
            
            # 限制最高仓位
            return min(position_size, max_position)
        except Exception as e:
            return max_position
            
    def evaluate_hk_exit_signals(self, symbol, current_price=None, target_date=None):
        """
        HK Exit Signals:
        1. Dynamic ATR trailing stop (replacing fixed 10% or MA20)
        """
        try:
            df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            if df.empty: return [], "无行情数据"
            
            if target_date:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] <= pd.to_datetime(target_date)]
                if df.empty: return [], "无该日期之前的行情"

            if len(df) < 20: return [], "数据不足以计算防守线"

            latest = df.iloc[-1]
            close = latest['close']
            
            # 计算近期波动率 (ATR)
            df_atr = df.iloc[-20:].copy()
            df_atr['prev_close'] = df_atr['close'].shift(1)
            df_atr['tr1'] = df_atr['high'] - df_atr['low']
            df_atr['tr2'] = (df_atr['high'] - df_atr['prev_close']).abs()
            df_atr['tr3'] = (df_atr['low'] - df_atr['prev_close']).abs()
            df_atr['TR'] = df_atr[['tr1', 'tr2', 'tr3']].max(axis=1)
            atr = df_atr['TR'].iloc[-14:].mean()
            
            # 回溯最高点
            lookback_df = df.iloc[-self.lookback_days:] if len(df) >= self.lookback_days else df
            recent_high = lookback_df['high'].max()
            
            triggered_signals = []
            descriptions = []

            # HK特有防线：动态波动率止损 (2.0倍 ATR)
            dynamic_stop_price = recent_high - (atr * 2.0)
            if close < dynamic_stop_price:
                triggered_signals.append("TrailingStop")
                descriptions.append(f"⚫ 【波动率防守线击穿】：股价({close})已跌破基于近期最高点({recent_high})设定的 2.0ATR 动态止损位({round(dynamic_stop_price,2)})，建议无条件离场。")

            # 乖离率保留作为情绪过热预警
            df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
            ema20 = df['ema20'].iloc[-1]
            bias = ((close - ema20) / ema20) * 100
            if bias > self.bias_threshold:
                triggered_signals.append("Conservative")
                descriptions.append(f"🟡 【保守卖点-情绪过热】：股价偏离均线过远(乖离率 {round(bias, 2)}%)，逢高减仓。")

            return triggered_signals, "\n".join(descriptions)
        except Exception as e:
            return [], f"卖出评估出错: {e}"

    def get_hk_rs_rating(self, symbol, target_date=None):
        try:
            df_stock = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            df_index = ak.stock_hk_index_daily_sina(symbol="HSI")
            
            if target_date:
                df_stock['date'] = pd.to_datetime(df_stock['date'])
                df_stock = df_stock[df_stock['date'] <= pd.to_datetime(target_date)]
                df_index['date'] = pd.to_datetime(df_index['date'])
                df_index = df_index[df_index['date'] <= pd.to_datetime(target_date)]

            df_stock = df_stock.iloc[-20:]
            df_index = df_index.iloc[-20:]
            
            stock_perf = (df_stock.iloc[-1]['close'] - df_stock.iloc[0]['close']) / df_stock.iloc[0]['close']
            index_perf = (df_index.iloc[-1]['close'] - df_index.iloc[0]['close']) / df_index.iloc[0]['close']
            
            return stock_perf - index_perf
        except:
            return 0

    def calculate_hk_position_size(self, symbol, risk_per_trade=0.02, max_position=0.20, target_date=None):
        try:
            df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            if target_date:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 15: return max_position
            
            df = df.iloc[-15:].copy()
            df['prev_close'] = df['close'].shift(1)
            
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = (df['high'] - df['prev_close']).abs()
            df['tr3'] = (df['low'] - df['prev_close']).abs()
            df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            
            atr = df['TR'].iloc[-14:].mean()
            latest_close = df.iloc[-1]['close']
            
            if atr == 0: return max_position
            
            stop_loss_pct = (atr * 1.5) / latest_close
            position_size = risk_per_trade / stop_loss_pct
            
            return min(position_size, max_position)
            
        except Exception as e:
            return max_position
