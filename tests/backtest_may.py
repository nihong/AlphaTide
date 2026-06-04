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

years = [2021, 2022, 2023, 2024, 2025, 2026]
target_dates = []
for y in years:
    # 每年5月1日到5月31日
    start_date = datetime(y, 5, 1).date()
    end_date = datetime(y, 5, 31).date()
    y_dates = [d.strftime('%Y-%m-%d') for d in all_dates if start_date <= d <= end_date]
    target_dates.extend(y_dates)

print(f"Backtesting {len(target_dates)} days across 6 years (May only).")

# 2. 依次运行扫描
for d in target_dates:
    report_file = f"reports/daily_decision_A_{d.replace('-', '')}.md"
    if os.path.exists(report_file):
        continue
    print(f"Running scan for {d}...")
    os.system(f"python3 main.py --auto --fast --date {d}")

# 3. 解析所有的推荐股票与市场状态
trades = [] # {'year':, 'symbol':, 'name':, 'buy_date':, 'buy_price':, 'sell_date':, 'sell_price':, 'sell_reason':, 'regime':}
for d in target_dates:
    y = d.split('-')[0]
    report_file = f"reports/daily_decision_A_{d.replace('-', '')}.md"
    if not os.path.exists(report_file): continue
    
    with open(report_file, 'r') as f:
        content = f.read()
        
    # Extract regime from description
    regime = "NORMAL"
    if "狂牛" in content: regime = "EXTREME_BULL"
    elif "慢涨" in content: regime = "SLOW_RISE"
    elif "震荡" in content: regime = "OSCILLATION"
    elif "阴跌" in content: regime = "SLOW_DECLINE"
    elif "极度熊市" in content or "空头环境" in content: regime = "EXTREME_BEAR"
    
    # 提取精选标的: ### 浙能电力 (600023)
    matches = re.findall(r'### (.*?) \((\d{6})\)', content)
    for name, symbol in matches:
        # Check if already holding
        if not any(t['symbol'] == symbol and t['sell_date'] is None for t in trades):
            trades.append({
                'year': y,
                'symbol': symbol,
                'name': name,
                'buy_date': d,
                'buy_price': None,
                'sell_date': None,
                'sell_price': None,
                'sell_reason': None,
                'regime': regime
            })

# 4. 模拟买入和卖出
from src.data_fetcher import fetch_a_stock_hist_cached
from src.risk_manager import RiskManager
risk = RiskManager()

for t in trades:
    df = fetch_a_stock_hist_cached(t['symbol'], period="daily", adjust="qfq")
    if df is None or df.empty: continue
    
    df['日期'] = pd.to_datetime(df['日期'])
    
    future_df = df[df['日期'] > pd.to_datetime(t['buy_date'])]
    if future_df.empty: continue
    buy_idx = future_df.index.min()
    
    t['buy_price'] = df.loc[buy_idx, '开盘']
    
    sell_idx = None
    for i in range(buy_idx, len(df)):
        current_date = df.loc[i, '日期'].strftime('%Y-%m-%d')
        # Here we pass the regime to context-aware exit evaluations
        signals, desc = risk.evaluate_exit_signals(t['symbol'], target_date=current_date, regime=t['regime'])
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

# 5. 按年份统计回测结果
completed_trades = [t for t in trades if t['buy_price'] is not None]
summary_md = "# AlphaTide 6年回测综合分析 (每年5月份全天候引擎版)\\n\\n## 📊 历年综合表现\\n\\n| 年份 | 总交易次数 | 胜率 | 平均单笔收益 | 累积绝对收益 (单利) |\\n| :--- | :--- | :--- | :--- | :--- |\\n"

for y in years:
    y_trades = [t for t in completed_trades if t['year'] == str(y)]
    if not y_trades:
        summary_md += f"| {y} | 0 | - | - | 0.00% |\\n"
        continue
    
    total_profit = 0
    win_count = 0
    for t in y_trades:
        pct_profit = (t['sell_price'] - t['buy_price']) / t['buy_price']
        t['profit_pct'] = pct_profit
        total_profit += pct_profit
        if pct_profit > 0: win_count += 1
        
    win_rate = win_count / len(y_trades) * 100
    avg_profit = (total_profit / len(y_trades)) * 100
    cum_profit = total_profit * 100
    
    summary_md += f"| {y} | {len(y_trades)} | {win_rate:.2f}% | {avg_profit:.2f}% | {cum_profit:.2f}% |\\n"

summary_md += "\\n## 📝 详细交易清单\\n\\n| 年份 | 买入日期 | 市场状态 | 股票名称(代码) | 卖出日期 | 收益率 | 卖出原因 |\\n| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\\n"
for t in completed_trades:
    if 'profit_pct' not in t: continue
    profit_str = f"**{t['profit_pct']*100:.2f}%**"
    reason_cleaned = t['sell_reason'].replace('\\n', ' ')
    summary_md += f"| {t['year']} | {t['buy_date']} | {t['regime']} | {t['name']}({t['symbol']}) | {t['sell_date']} | {profit_str} | {reason_cleaned} |\\n"

with open("reports/backtest_may_6y.md", "w") as f:
    f.write(summary_md)

print("回测完成！报告已生成: reports/backtest_may_6y.md")
