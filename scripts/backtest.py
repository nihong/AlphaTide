import os
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from src.market_monitor import MarketMonitor
from src.data_fetcher import fetch_market_index

class BacktestEngine:
    def __init__(self):
        self.monitor = MarketMonitor()
        # Mock LLM to save time and money during backtest
        self.monitor.analyst.analyze_with_llm = lambda prompt: "AI Analysis skipped in backtest mode."

    def get_last_30_trading_days(self, end_date, market="A"):
        if market == "A":
            df = ak.stock_zh_index_daily(symbol="sh000300")
        else:
            df = ak.stock_hk_index_daily_sina(symbol="HSI")
            
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'] <= pd.to_datetime(end_date)]
        return df.tail(30)['date'].dt.strftime('%Y-%m-%d').tolist()

    def run(self, end_date="2026-05-29", market="A"):
        dates = self.get_last_30_trading_days(end_date, market)
        print(f"Running [{market}] backtest for {len(dates)} days: {dates[0]} to {dates[-1]}")
        
        all_recommendations = []
        
        for d in dates:
            print(f"\n--- Backtesting Date: {d} ---")
            recs_today = []
            def mock_report(recommendations, light, light_msg, sell_warnings, target_date=None, market_type="A", **kwargs):
                nonlocal recs_today
                recs_today = recommendations

            original_report = self.monitor._generate_final_report
            self.monitor._generate_final_report = mock_report
            
            self.monitor.run_daily_scan(target_date=d, market=market)
            
            self.monitor._generate_final_report = original_report
            
            for r in recs_today:
                r['date'] = d
                all_recommendations.append(r)

        if not all_recommendations:
            print(f"\n❌ No [{market}] recommendations found in the last 30 trading days with current settings.")
            return

        print(f"\n✅ Found {len(all_recommendations)} recommendations. Calculating performance...")
        self.calculate_performance(all_recommendations, end_date, market)

    def calculate_performance(self, recs, end_date, market):
        results = []
        for r in recs:
            symbol = r['symbol']
            buy_date = r['date']
            name = r['name']
            
            try:
                if market == "A":
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=buy_date.replace("-", ""), end_date=end_date.replace("-", ""), adjust="qfq")
                    close_col = '收盘'
                else:
                    df = ak.stock_hk_daily(symbol=symbol, adjust="qfq")
                    df['date'] = pd.to_datetime(df['date'])
                    df = df[(df['date'] >= pd.to_datetime(buy_date)) & (df['date'] <= pd.to_datetime(end_date))]
                    close_col = 'close'
                    
                if df.empty: continue
                
                buy_price = df.iloc[0][close_col]
                current_price = df.iloc[-1][close_col]
                ret = (current_price - buy_price) / buy_price
                
                results.append({
                    "Date": buy_date,
                    "Symbol": symbol,
                    "Name": name,
                    "Buy Price": buy_price,
                    "End Price": current_price,
                    "Return (%)": round(ret * 100, 2)
                })
            except:
                continue
        
        if not results:
            print(f"Could not calculate performance for any [{market}] recommendations.")
            return

        df_results = pd.DataFrame(results)
        print(f"\n### [{market}] Backtest Results ###")
        print(df_results.to_string())
        
        avg_ret = df_results['Return (%)'].mean()
        win_rate = (df_results['Return (%)'] > 0).sum() / len(df_results)
        
        print(f"\n[{market}] Summary:")
        print(f"Total Recommendations: {len(df_results)}")
        print(f"Average Return: {round(avg_ret, 2)}%")
        print(f"Win Rate: {round(win_rate * 100, 2)}%")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=str, default="A")
    args = parser.parse_args()
    
    engine = BacktestEngine()
    engine.run(market=args.market)
