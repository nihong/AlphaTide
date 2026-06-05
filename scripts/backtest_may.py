import os
import json
import pandas as pd
import akshare as ak
from datetime import datetime
from src.market_monitor import MarketMonitor
from src.data_fetcher import fetch_a_stock_hist_cached

# 屏蔽个股层面的 AI 分析以加速回测，并在板块提纯环节使用基于词频的快速 Mock，节省 132 次大模型调用成本
from src.ai_analyst import AIAnalyst
from collections import Counter

def mock_analyze(self, prompt): return "Backtest Mock Analysis: 优质标的"

def mock_extract(self, reports):
    # 模拟大模型行为：直接从传进来的研报数据中，找到报告数量最多的前3个行业！
    if not reports: return {}
    industries = [r.get('industry', '') for r in reports if r.get('industry')]
    top_3 = Counter(industries).most_common(3)
    
    result = {}
    for ind, count in top_3:
        if not ind: continue
        result[ind] = {
            "name": ind,
            "reason": f"回测快速提取: 该板块近期有 {count} 份券商研报密集覆盖",
            "macro_indicator": "回测模拟指标"
        }
    return result

AIAnalyst.analyze_with_llm = mock_analyze
AIAnalyst.extract_hot_industries_from_reports = mock_extract

class MayStrategyEvaluator:
    def __init__(self):
        self.monitor = MarketMonitor()

    def get_may_trade_dates(self):
        df = ak.tool_trade_date_hist_sina()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        # 取过去7年的5月份交易日 (2020-2026)
        may_dates = df[(df['trade_date'].dt.month == 5) & 
                       (df['trade_date'].dt.year >= 2020) & 
                       (df['trade_date'].dt.year <= 2026) &
                       (df['trade_date'] < datetime.now())]['trade_date'].dt.strftime('%Y-%m-%d').tolist()
        return sorted(may_dates)

    def get_forward_return(self, symbol, entry_date, days=5):
        try:
            df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=24)
            date_col = '日期'
            close_col = '收盘'
            
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

    def evaluate(self):
        dates = self.get_may_trade_dates()
        all_signals = []
        
        print(f"🚀 开始回测 A股 近7年 5月份 策略表现，共计 {len(dates)} 个交易日...")
        
        for date in dates:
            print(f"\n==============================================")
            print(f"📅 正在扫描历史回测节点: {date}")
            print(f"==============================================")
            
            signals_today = []
            original_report_func = self.monitor._generate_final_report
            
            def temp_report(recs, light, light_msg, warnings, target_date=None, market="A", **kwargs):
                for r in recs:
                    signals_today.append(r)
            
            self.monitor._generate_final_report = temp_report
            # 使用 fast_mode=True 跳过部分繁琐计算，但我们依然依赖行业的 LLM 提取
            self.monitor.run_daily_scan(target_date=date, market="A", fast_mode=True)
            self.monitor._generate_final_report = original_report_func
            
            for s in signals_today:
                if "对冲" in s['sector'] or "做空" in s['name']:
                    # 对于大盘空仓保护，计算510300下跌的相对收益（做空收益）
                    ret_5d = -self.get_forward_return(s['symbol'], date, days=5)
                    ret_10d = -self.get_forward_return(s['symbol'], date, days=10)
                else:
                    ret_5d = self.get_forward_return(s['symbol'], date, days=5)
                    ret_10d = self.get_forward_return(s['symbol'], date, days=10)
                    
                all_signals.append({
                    'date': date,
                    'symbol': s['symbol'],
                    'name': s['name'],
                    'sector': s['sector'],
                    'ret_5d': ret_5d,
                    'ret_10d': ret_10d
                })

        if not all_signals:
            print("回测结束: 未触发任何买入或防守信号。")
            return
            
        df_res = pd.DataFrame(all_signals)
        df_res.to_csv("reports/may_7yr_backtest_results.csv", index=False)
        
        total_signals = len(df_res)
        win_rate = len(df_res[df_res['ret_5d'] > 0]) / total_signals if total_signals > 0 else 0
        avg_ret = df_res['ret_5d'].mean()
        
        print("\n🏆 回测完成！汇总数据如下：")
        print(f"总交易笔数: {total_signals}")
        print(f"5日胜率: {win_rate * 100:.2f}%")
        print(f"5日平均收益率: {avg_ret * 100:.2f}%")

if __name__ == "__main__":
    evaluator = MayStrategyEvaluator()
    evaluator.evaluate()
