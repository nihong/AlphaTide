import akshare as ak
import pandas as pd

class RiskManager:
    def __init__(self):
        # 激进策略（趋势跟踪）：破20日线卖出
        self.trend_ma = 20
        # 保守策略（估值/情绪）：乖离率过大或估值过高
        self.bias_threshold = 15.0 # 股价偏离MA20超过15%
        # 新增：移动止损（最高点回撤）策略
        self.trailing_stop_threshold = 10.0 # 从近期最高点回撤超过10%无条件止损
        self.lookback_days = 60 # 计算最高点的回溯天数

    def evaluate_exit_signals(self, symbol, current_price=None, target_date=None):
        """
        评估卖出信号
        Returns: (signals, description)
        signals: List of triggered signal types ["Aggressive", "Conservative", "TrailingStop"]
        """
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            if df.empty: return [], "无行情数据"
            
            if target_date:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df[df['日期'] <= pd.to_datetime(target_date)]
                if df.empty: return [], "无该日期之前的行情"

            latest = df.iloc[-1]
            close = latest['收盘']
            ma20 = df.iloc[-20:]['收盘'].mean()
            
            # 计算近期最高价与当前回撤
            lookback_df = df.iloc[-self.lookback_days:] if len(df) >= self.lookback_days else df
            recent_high = lookback_df['最高'].max()
            drawdown = ((recent_high - close) / recent_high) * 100
            
            triggered_signals = []
            descriptions = []

            # 0. 绝对止损点：高位回撤 (Trailing Stop)
            # 逻辑：无论均线状态如何，只要从近期高点回撤超过设定阈值，立即触发生存防线。
            if drawdown > self.trailing_stop_threshold:
                triggered_signals.append("TrailingStop")
                descriptions.append(f"⚫ 【绝对止损-高位回撤】：股价({close})已从近期高点({recent_high})回撤 {round(drawdown, 2)}%，超过设定的 {self.trailing_stop_threshold}% 红线，建议无条件止损/止盈。")

            # 1. 激进卖点：趋势破坏 (Aggressive - Trend Break)
            # 逻辑：只要价格跌破20日线，说明短期上升趋势终结，必须离场。
            if close < ma20:
                triggered_signals.append("Aggressive")
                descriptions.append(f"🔴 【激进卖点-趋势破坏】：股价({close}) 已跌破 20日均线({round(ma20, 2)})。")

            # 2. 保守卖点：情绪过热 (Conservative - Overheated)
            # 逻辑：股价短期涨幅过大，偏离均线太远（乖离率过高），存在回调压力，建议落袋为安。
            bias = ((close - ma20) / ma20) * 100
            if bias > self.bias_threshold:
                triggered_signals.append("Conservative")
                descriptions.append(f"🟡 【保守卖点-情绪过热】：股价偏离均线过远(乖离率 {round(bias, 2)}%)，建议分批减仓。")

            return triggered_signals, "\n".join(descriptions)
        except Exception as e:
            return [], f"卖出评估出错: {e}"

    def get_rs_rating(self, symbol, target_date=None):
        """
        获取个股相对强度 (Relative Strength)
        逻辑：个股涨幅 vs 沪深300涨幅
        """
        try:
            # 简化版：计算过去20天的涨幅
            df_stock = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
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
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
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
        try:
            df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
            if df.empty: return [], "无行情数据"
            
            if target_date:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] <= pd.to_datetime(target_date)]
                if df.empty: return [], "无该日期之前的行情"

            latest = df.iloc[-1]
            close = latest['close']
            ma20 = df.iloc[-20:]['close'].mean()
            
            lookback_df = df.iloc[-self.lookback_days:] if len(df) >= self.lookback_days else df
            recent_high = lookback_df['high'].max()
            drawdown = ((recent_high - close) / recent_high) * 100
            
            triggered_signals = []
            descriptions = []

            if drawdown > self.trailing_stop_threshold:
                triggered_signals.append("TrailingStop")
                descriptions.append(f"⚫ 【绝对止损-高位回撤】：股价({close})已从近期高点({recent_high})回撤 {round(drawdown, 2)}%，超过设定的 {self.trailing_stop_threshold}% 红线，建议无条件止损/止盈。")

            if close < ma20:
                triggered_signals.append("Aggressive")
                descriptions.append(f"🔴 【激进卖点-趋势破坏】：股价({close}) 已跌破 20日均线({round(ma20, 2)})。")

            bias = ((close - ma20) / ma20) * 100
            if bias > self.bias_threshold:
                triggered_signals.append("Conservative")
                descriptions.append(f"🟡 【保守卖点-情绪过热】：股价偏离均线过远(乖离率 {round(bias, 2)}%)，建议分批减仓。")

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
