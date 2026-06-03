import os
import re
import json
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

# 1. 获取过去30个交易日
trade_dates = ak.tool_trade_date_hist_sina()
trade_dates['trade_date'] = pd.to_datetime(trade_dates['trade_date']).dt.date
today = datetime.now().date()
past_dates = trade_dates[trade_dates['trade_date'] < today]['trade_date'].tolist()[-30:]
past_dates_str = [d.strftime('%Y-%m-%d') for d in past_dates]

print(f"Backtesting {len(past_dates_str)} days: {past_dates_str[0]} to {past_dates_str[-1]}")

# 2. 依次生成 MD 报告
for d in past_dates_str:
    pass
    # print(f"Running scan for {d}...")
    # os.system(f"python3 main.py --auto --date {d}")

# 3. 解析所有的推荐股票
trades = [] # {'symbol':, 'name':, 'buy_date':, 'buy_price':, 'sell_date':, 'sell_price':, 'reason':, 'profit':}
for d in past_dates_str:
    report_file = f"reports/daily_decision_A_{d.replace('-', '')}.md"
    if not os.path.exists(report_file): continue
    
    with open(report_file, 'r') as f:
        content = f.read()
    
    # 提取精选标的: ### 浙能电力 (600023)
    matches = re.findall(r'### (.*?) \((\d{6})\)', content)
    for name, symbol in matches:
        # Check if already holding
        if not any(t['symbol'] == symbol and t['sell_date'] is None for t in trades):
            trades.append({
                'symbol': symbol,
                'name': name,
                'buy_date': d,
                'buy_price': None,
                'sell_date': None,
                'sell_price': None,
                'sell_reason': None
            })

# 4. 模拟买入和卖出 (根据三轨卖出信号)
from src.data_fetcher import fetch_a_stock_hist_cached
from src.risk_manager import RiskManager
risk = RiskManager()

for t in trades:
    # 获取完整的历史K线
    df = fetch_a_stock_hist_cached(t['symbol'], period="daily", adjust="qfq")
    if df is None or df.empty: continue
    
    df['日期'] = pd.to_datetime(df['日期'])
    
    # 找到买入点 (买入日的次日开盘价买入)
    future_df = df[df['日期'] > pd.to_datetime(t['buy_date'])]
    if future_df.empty: continue
    buy_idx = future_df.index.min()
    
    t['buy_price'] = df.loc[buy_idx, '开盘']
    
    # 遍历随后的每一天，检查是否触发卖出信号
    sell_idx = None
    for i in range(buy_idx, len(df)):
        current_date = df.loc[i, '日期'].strftime('%Y-%m-%d')
        # Check exit signals on this date
        signals, desc = risk.evaluate_exit_signals(t['symbol'], target_date=current_date)
        if signals:
            sell_idx = i
            t['sell_date'] = current_date
            t['sell_price'] = df.loc[i, '收盘']
            t['sell_reason'] = desc
            break
            
    if sell_idx is None: # 至今未卖出
        t['sell_date'] = "HOLDING"
        t['sell_price'] = df.iloc[-1]['收盘']
        t['sell_reason'] = "Holding"

# 5. 统计回测结果
completed_trades = [t for t in trades if t['buy_price'] is not None]
total_profit = 0
win_count = 0
for t in completed_trades:
    pct_profit = (t['sell_price'] - t['buy_price']) / t['buy_price']
    t['profit_pct'] = pct_profit
    total_profit += pct_profit
    if pct_profit > 0: win_count += 1

print("\n\n" + "="*50)
print("回测总结")
print("="*50)
print(f"总交易次数: {len(completed_trades)}")
if completed_trades:
    print(f"胜率: {win_count / len(completed_trades) * 100:.2f}%")
    print(f"平均单笔收益: {total_profit / len(completed_trades) * 100:.2f}%")
    print(f"累积绝对收益(单利): {total_profit * 100:.2f}%")
else:
    print("未产生任何交易。")

print("\n交易明细:")
for t in completed_trades:
    print(f"{t['buy_date']} 买入 {t['name']}({t['symbol']}) @ {t['buy_price']:.2f}")
    if t['sell_date'] == "HOLDING":
        print(f"   -> 至今持有, 现价 {t['sell_price']:.2f}, 浮动盈亏: {t['profit_pct']*100:.2f}%")
    else:
        print(f"   -> {t['sell_date']} 卖出 @ {t['sell_price']:.2f}, 收益: {t['profit_pct']*100:.2f}%, 理由: {t['sell_reason']}")

with open("backtest_result.json", "w") as f:
    json.dump(completed_trades, f, indent=2, ensure_ascii=False)
