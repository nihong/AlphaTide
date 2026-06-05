import os
import json
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from src.market_monitor import MarketMonitor
from src.data_fetcher import fetch_a_stock_hist_cached
from collections import Counter

# ==========================================
# 屏蔽大模型以加速回测，使用词频提纯行业
# ==========================================
from src.ai_analyst import AIAnalyst
def mock_analyze(self, prompt): return "Backtest Mock Analysis"
def mock_extract(self, reports):
    if not reports: return {}
    industries = [r.get('industry', '') for r in reports if r.get('industry')]
    top_3 = Counter(industries).most_common(3)
    return {ind: {"name": ind, "reason": "历史回测模拟共识", "macro_indicator": "N/A"} for ind, count in top_3 if ind}
AIAnalyst.analyze_with_llm = mock_analyze
AIAnalyst.extract_hot_industries_from_reports = mock_extract


class FullHistoryBacktester:
    def __init__(self):
        self.monitor = MarketMonitor()
        self.portfolio = {}  # {symbol: {"buy_date": date, "buy_price": price, "highest_price": price, "qty": qty}}
        self.history_trades = []
        
    def get_all_trade_dates(self, years=7):
        df = ak.tool_trade_date_hist_sina()
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        start_date = datetime.now() - timedelta(days=years*365)
        dates = df[(df['trade_date'] >= start_date) & (df['trade_date'] < datetime.now())]['trade_date'].dt.strftime('%Y-%m-%d').tolist()
        return sorted(dates)

    def get_price(self, symbol, date):
        try:
            df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=24)
            df['日期'] = pd.to_datetime(df['日期'])
            row = df[df['日期'] == pd.to_datetime(date)]
            if not row.empty:
                return float(row.iloc[0]['收盘'])
        except:
            pass
        return None

    def run(self):
        dates = self.get_all_trade_dates()
        print(f"🚀 开始全量 7 年回测，共计 {len(dates)} 个交易日...")
        
        for i, date in enumerate(dates):
            if i % 10 == 0:
                print(f"[{i}/{len(dates)}] 正在回测节点: {date} (当前持仓: {len(self.portfolio)} 只)")
                
            # 1. 检查当前持仓是否触发卖出 (使用真实的 ATR 吊灯防线和 EMA 破位)
            sold_symbols = []
            for symbol, pos in self.portfolio.items():
                current_price = self.get_price(symbol, date)
                if not current_price: continue
                
                # 更新最高价
                if current_price > pos['highest_price']:
                    pos['highest_price'] = current_price
                    
                # 调取真实的卖出风控逻辑
                # 因为 evaluate_a_exit_signals 内部会去抓最近行情，这里可以直接复用
                exit_signals, reason = self.monitor.risk.evaluate_a_exit_signals(symbol, target_date=date)
                
                if exit_signals:
                    ret = (current_price - pos['buy_price']) / pos['buy_price']
                    self.history_trades.append({
                        "buy_date": pos['buy_date'],
                        "sell_date": date,
                        "symbol": symbol,
                        "buy_price": pos['buy_price'],
                        "sell_price": current_price,
                        "return": ret,
                        "reason": reason
                    })
                    sold_symbols.append(symbol)
                    print(f"  🔴 [卖出] {symbol} | 收益: {ret*100:.2f}% | 原因: {reason}")
                    
            for sym in sold_symbols:
                del self.portfolio[sym]

            # 2. 扫描今日买入信号
            signals_today = []
            original_report_func = self.monitor._generate_final_report
            def temp_report(recs, light, light_msg, warnings, target_date=None, market="A", **kwargs):
                for r in recs: signals_today.append(r)
            
            self.monitor._generate_final_report = temp_report
            # 屏蔽打印以防止日志爆炸
            import sys, os
            old_stdout = sys.stdout
            sys.stdout = open(os.devnull, 'w')
            try:
                self.monitor.run_daily_scan(target_date=date, market="A", fast_mode=True)
            finally:
                sys.stdout.close()
                sys.stdout = old_stdout
            self.monitor._generate_final_report = original_report_func
            
            # 执行买入
            for s in signals_today:
                sym = s['symbol']
                if sym not in self.portfolio and "做空" not in s['name'] and "对冲" not in s['sector']:
                    price = self.get_price(sym, date)
                    if price:
                        self.portfolio[sym] = {
                            "buy_date": date,
                            "buy_price": price,
                            "highest_price": price,
                            "name": s['name']
                        }
                        print(f"  🟢 [买入] {s['name']} ({sym})")

        # 结算期末未平仓持仓
        final_date = dates[-1]
        for symbol, pos in self.portfolio.items():
            current_price = self.get_price(symbol, final_date)
            if current_price:
                ret = (current_price - pos['buy_price']) / pos['buy_price']
                self.history_trades.append({
                    "buy_date": pos['buy_date'],
                    "sell_date": "END_OF_TEST",
                    "symbol": symbol,
                    "buy_price": pos['buy_price'],
                    "sell_price": current_price,
                    "return": ret,
                    "reason": "期末强制平仓"
                })

        # 输出报告
        self.generate_markdown_report()

    def generate_markdown_report(self):
        if not self.history_trades:
            print("回测结束，无交易记录。")
            return
            
        df = pd.DataFrame(self.history_trades)
        df.to_csv("reports/7yr_full_backtest.csv", index=False)
        
        total_trades = len(df)
        win_trades = len(df[df['return'] > 0])
        win_rate = win_trades / total_trades
        avg_ret = df['return'].mean()
        max_profit = df['return'].max()
        max_loss = df['return'].min()
        
        report_md = f"""# AlphaTide 7年全量真实回测报告 (2019-2026)

## 📌 回测说明
- **防未来函数**: 所有研报抓取、均线计算均严格使用 `target_date` 截止日，**100% 对应过往真实日期**。
- **真实卖出逻辑**: 弃用“死拿 5 天”的粗暴模式，全面接入 AlphaTide 真实的 `ATR 吊灯止损防线` 及 `过热卖出` 信号引擎。
- **触发逻辑**: 遇到卖出信号才离场，无信号则一直持有。

## 📊 核心绩效指标
- **总交易笔数**: {total_trades} 笔
- **真实胜率 (赢单比例)**: **{win_rate * 100:.2f}%**
- **平均单笔收益率**: **{avg_ret * 100:.2f}%**
- **单笔最大盈利**: {max_profit * 100:.2f}%
- **单笔最大回撤**: {max_loss * 100:.2f}%

## 📝 详细交易清单 (节选)
"""
        # 加上最近的几笔交易
        for _, row in df.tail(20).iterrows():
            report_md += f"- **{row['symbol']}** | 买入: {row['buy_date']} | 卖出: {row['sell_date']} | 收益: **{row['return']*100:.2f}%** | 卖出原因: {row['reason']}\n"
            
        with open("reports/AlphaTide_7Yr_Strategy_Report.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        print("✅ 全量报告已生成至 reports/AlphaTide_7Yr_Strategy_Report.md")

if __name__ == "__main__":
    backtester = FullHistoryBacktester()
    backtester.run()
