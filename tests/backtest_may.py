import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
import json
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

# 1. 获取所有的交易日
trade_dates = ak.tool_trade_date_hist_sina()
trade_dates['trade_date'] = pd.to_datetime(trade_dates['trade_date']).dt.date
all_dates = trade_dates['trade_date'].tolist()

years = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
target_dates = []
for y in years:
    # 每年5月1日到5月31日
    start_date = datetime(y, 5, 1).date()
    end_date = datetime(y, 5, 31).date()
    y_dates = [d.strftime('%Y-%m-%d') for d in all_dates if start_date <= d <= end_date]
    target_dates.extend(y_dates)

print(f"Backtesting {len(target_dates)} days across 7 years (May only).")

import concurrent.futures

# 2. 依次运行扫描 (多线程加速，减小并发防封)
def run_scan(d):
    report_file = f"reports/daily_decision_A_{d.replace('-', '')}.md"
    if os.path.exists(report_file):
        return
    print(f"Running scan for {d}...")
    # 日志输出到 tmp 目录，方便排查
    os.system(f"python3 main.py --auto --fast --date {d} > /tmp/scan_{d}.log 2>&1")

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    executor.map(run_scan, target_dates)

# 3 & 4. 解析并模拟买卖 (按时间顺序)
from src.data_fetcher import fetch_a_stock_hist_cached
from src.risk_manager import RiskManager
risk = RiskManager()
trades = []

for d in target_dates:
    y = d.split('-')[0]
    report_file = f"reports/daily_decision_A_{d.replace('-', '')}.md"
    if not os.path.exists(report_file): continue
    
    with open(report_file, 'r') as f:
        content = f.read()
        
    regime = "NORMAL"
    if "狂牛" in content: regime = "EXTREME_BULL"
    elif "慢涨" in content: regime = "SLOW_RISE"
    elif "震荡" in content: regime = "OSCILLATION"
    elif "阴跌" in content: regime = "SLOW_DECLINE"
    elif "极度熊市" in content or "空头环境" in content: regime = "EXTREME_BEAR"
    
    matches = re.findall(r'### (.*?) \((\d{6})\)', content)
    for name, symbol in matches:
        # 检查是否还在持有 (sell_date == 'HOLDING' 代表还没卖，或者在未来的某一天才卖)
        # 我们需要判断：当前的日期 d，是否在上次买入和卖出之间
        is_holding = False
        for t in trades:
            if t['symbol'] == symbol:
                if t['sell_date'] is None or t['sell_date'] == "HOLDING" or t['sell_date'] >= d:
                    is_holding = True
                    break
        if is_holding:
            continue
            
        t = {
            'year': y, 'symbol': symbol, 'name': name, 'buy_date': d,
            'buy_price': None, 'sell_date': None, 'sell_price': None,
            'sell_reason': None, 'regime': regime
        }
        
        # 立刻模拟卖出时间
        df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq")
        if df is not None and not df.empty:
            df['日期'] = pd.to_datetime(df['日期'])
            future_df = df[df['日期'] > pd.to_datetime(d)]
            if not future_df.empty:
                buy_idx = future_df.index.min()
                t['buy_price'] = df.loc[buy_idx, '开盘']
                sell_idx = None
                
                for i in range(buy_idx, len(df)):
                    current_date = df.loc[i, '日期'].strftime('%Y-%m-%d')
                    if symbol == '510300':
                        from src.market_monitor import MarketMonitor
                        _mm = MarketMonitor()
                        _light, _, _regime = _mm.check_market_light(target_date=current_date)
                        if _light != "RED" and _regime not in ["EXTREME_BEAR", "SLOW_DECLINE"]:
                            sell_idx = i
                            t['sell_date'] = current_date
                            t['sell_price'] = df.loc[i, '收盘']
                            t['sell_reason'] = "🟢 【空头平仓】：大盘防守结束，红灯解除"
                            break
                        continue
                        
                    signals, desc = risk.evaluate_exit_signals(symbol, target_date=current_date, regime=regime)
                    if signals:
                        sell_idx = i
                        t['sell_date'] = current_date
                        t['sell_price'] = df.loc[i, '收盘']
                        t['sell_reason'] = desc
                        break
                        
                if sell_idx is None:
                    t['sell_date'] = "HOLDING"
                    t['sell_price'] = df.iloc[-1]['收盘']
                    t['sell_reason'] = "Holding"
        
        trades.append(t)

# 5. 按年份统计回测结果
completed_trades = [t for t in trades if t['buy_price'] is not None]
summary_md = "# AlphaTide 7年回测综合分析 (每年5月份全天候引擎版)\n\n## 📊 历年综合表现\n\n| 年份 | 总交易次数 | 胜率 | 平均单笔收益 | 累积绝对收益 (单利) |\n| :--- | :--- | :--- | :--- | :--- |\n"

for y in years:
    y_trades = [t for t in completed_trades if t['year'] == str(y)]
    if not y_trades:
        summary_md += f"| {y} | 0 | - | - | 0.00% |\n"
        continue
    
    total_profit = 0
    win_count = 0
    for t in y_trades:
        # ETF 是融券做空，收益率为 (买入价 - 卖出价) / 买入价
        if t['symbol'] == '510300':
            pct_profit = (t['buy_price'] - t['sell_price']) / t['buy_price']
        else:
            pct_profit = (t['sell_price'] - t['buy_price']) / t['buy_price']
            
        t['profit_pct'] = pct_profit
        total_profit += pct_profit
        if pct_profit > 0: win_count += 1
        
    win_rate = win_count / len(y_trades) * 100
    avg_profit = (total_profit / len(y_trades)) * 100
    cum_profit = total_profit * 100
    
    summary_md += f"| {y} | {len(y_trades)} | {win_rate:.2f}% | {avg_profit:.2f}% | {cum_profit:.2f}% |\n"

summary_md += "\n## 📝 详细交易清单\n\n| 年份 | 买入日期 | 市场状态 | 股票名称(代码) | 卖出日期 | 收益率 | 卖出原因 |\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
for t in completed_trades:
    if 'profit_pct' not in t: continue
    profit_str = f"**{t['profit_pct']*100:.2f}%**"
    reason_cleaned = t['sell_reason'].replace('\n', ' ')
    summary_md += f"| {t['year']} | {t['buy_date']} | {t['regime']} | {t['name']}({t['symbol']}) | {t['sell_date']} | {profit_str} | {reason_cleaned} |\n"

with open("reports/backtest_may_7y.md", "w") as f:
    f.write(summary_md)

print("回测完成！报告已生成: reports/backtest_may_7y.md")
