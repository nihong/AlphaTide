import akshare as ak
import pandas as pd

class RiskManager:
    def __init__(self):
        # 激进策略（趋势跟踪）：破20日线卖出
        self.trend_ma = 20
        # 保守策略（估值/情绪）：乖离率过大或估值过高
        self.bias_threshold = 15.0 # 股价偏离MA20超过15%

    def evaluate_exit_signals(self, symbol, current_price=None):
        """
        评估卖出信号
        Returns: (signals, description)
        signals: List of triggered signal types ["Aggressive", "Conservative"]
        """
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            if df.empty: return [], "无行情数据"
            
            latest = df.iloc[-1]
            close = latest['收盘']
            ma20 = df.iloc[-20:]['收盘'].mean()
            
            triggered_signals = []
            descriptions = []

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

    def get_rs_rating(self, symbol):
        """
        获取个股相对强度 (Relative Strength)
        逻辑：个股涨幅 vs 沪深300涨幅
        """
        try:
            # 简化版：计算过去20天的涨幅
            df_stock = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq").iloc[-20:]
            df_index = ak.stock_zh_index_daily(symbol="sh000300").iloc[-20:]
            
            stock_perf = (df_stock.iloc[-1]['收盘'] - df_stock.iloc[0]['收盘']) / df_stock.iloc[0]['收盘']
            index_perf = (df_index.iloc[-1]['close'] - df_index.iloc[0]['close']) / df_index.iloc[0]['close']
            
            rs_score = stock_perf - index_perf
            return rs_score
        except:
            return 0
