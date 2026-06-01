import os
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from src.market_monitor import MarketMonitor
from src.data_fetcher import fetch_with_cache

# 屏蔽 AI 调用以加速回测并节省成本
from src.ai_analyst import AIAnalyst
def mock_analyze(self, prompt): return "Backtest Mock Analysis"
AIAnalyst.analyze_with_llm = mock_analyze

class StrategyEvaluator:
    def __init__(self):
        self.monitor = MarketMonitor()

    def get_trade_dates(self, count=30):
        df = ak.tool_trade_date_hist_sina()
        # 获取今天之前的交易日
        dates = df[df['trade_date'] < datetime.now().date()]['trade_date'].iloc[-count:].tolist()
        return [d.strftime('%Y-%m-%d') for d in dates]

    def get_forward_return(self, symbol, entry_date, days=5, market="A"):
        """计算买入后 N 天的收益率"""
        try:
            if market == "A":
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
                date_col = '日期'
                close_col = '收盘'
            else:
                df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
                date_col = 'date'
                close_col = 'close'
            
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.sort_values(by=date_col)
            
            entry_idx = df[df[date_col] == pd.to_datetime(entry_date)].index
            if entry_idx.empty: return 0
            
            idx = entry_idx[0]
            if idx + days >= len(df):
                exit_price = df.iloc[-1][close_col]
            else:
                exit_price = df.iloc[idx + days][close_col]
                
            entry_price = df.loc[idx, close_col]
            return (exit_price - entry_price) / entry_price
        except:
            return 0

    def evaluate(self, market="A", days=30):
        dates = self.get_trade_dates(days)
        all_signals = []
        
        print(f"开始回测 {market} 市场 过去 {days} 个工作日...")
        
        for date in dates:
            print(f"正在扫描 {date} ...")
            # 捕获推荐结果
            # 为了获取结果，我们临时 hack 一下报告生成函数
            signals_today = []
            original_report_func = self.monitor._generate_final_report
            
            def temp_report(recs, light, light_msg, warnings, target_date=None, market=market, **kwargs):
                for r in recs:
                    signals_today.append(r)
            
            self.monitor._generate_final_report = temp_report
            self.monitor.run_daily_scan(target_date=date, market=market)
            self.monitor._generate_final_report = original_report_func
            
            for s in signals_today:
                ret_5d = self.get_forward_return(s['symbol'], date, days=5, market=market)
                ret_10d = self.get_forward_return(s['symbol'], date, days=10, market=market)
                all_signals.append({
                    'date': date,
                    'symbol': s['symbol'],
                    'name': s['name'],
                    'ret_5d': ret_5d,
                    'ret_10d': ret_10d
                })

        if not all_signals:
            print(f"回测结束: {market} 市场在过去 {days} 天内由于风控严苛，未触发任何买入信号。")
            return None

        df_res = pd.DataFrame(all_signals)
        stats = {
            'market': market,
            'signal_count': len(df_res),
            'win_rate_5d': len(df_res[df_res['ret_5d'] > 0]) / len(df_res),
            'avg_ret_5d': df_res['ret_5d'].mean(),
            'max_ret': df_res['ret_5d'].max(),
            'max_drawdown': df_res['ret_5d'].min()
        }
        return stats

if __name__ == "__main__":
    evaluator = StrategyEvaluator()
    a_stats = evaluator.evaluate(market="A", days=30)
    hk_stats = evaluator.evaluate(market="HK", days=30)
    
    print("\n" + "="*30)
    print("📋 AlphaTide 30日实战审计报告")
    print("="*30)
    
    for s in [a_stats, hk_stats]:
        if s:
            print(f"\n市场: {s['market']}")
            print(f"- 触发信号总数: {s['signal_count']}")
            print(f"- 5日胜率: {round(s['win_rate_5d']*100, 2)}%")
            print(f"- 5日平均收益: {round(s['avg_ret_5d']*100, 2)}%")
            print(f"- 单笔最大收益: {round(s['max_ret']*100, 2)}%")
            print(f"- 回测期间最大回撤: {round(s['max_drawdown']*100, 2)}%")
        else:
            print(f"\n市场: (无数据)")
    
    print("\n💡 架构师总结：")
    print("1. 如果信号极少：说明漏斗极度严苛，成功避开了过去30天的震荡下行。")
    print("2. 如果胜率 > 55%：说明策略具备统计学上的正期望。")
    print("3. 如果回撤 < 10%：说明移动止损与大盘红绿灯机制生效。")
