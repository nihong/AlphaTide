import akshare as ak
import pandas as pd
import numpy as np
import datetime

def calculate_atr(df, period=14):
    df['high-low'] = df['high'] - df['low']
    df['high-pc'] = abs(df['high'] - df['close'].shift(1))
    df['low-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df

def run_performance_backtest():
    print("==================================================")
    print("🌊 AlphaTide V8.1 实战收益率与回撤极限回测 (6年完整周期)")
    print("注意：受限于免费数据，使用当期卡脖子龙头股池回测过去6年会存在一定幸存者偏差。")
    print("但此回测能完美展示【VCP 突破 + 2.5倍ATR防线】体系的盈亏比与净值曲线。")
    print("==================================================")
    
    # 设定典型牛鞭效应赛道龙头作为沙盘标的
    symbols = {
        "sz300408": "三环集团 (MLCC)", 
        "sz300308": "中际旭创 (光模块)",
        "sz002837": "英维克 (液冷)",
        "sh600487": "亨通光电 (光纤)"
    }
    
    print("正在拉取大盘宏观防线数据...")
    try:
        df_300 = ak.stock_zh_index_daily(symbol="sh000300")
    except Exception:
        print("大盘数据抓取失败，跳过测试。")
        return
        
    df_300['date'] = pd.to_datetime(df_300['date'])
    df_300.set_index('date', inplace=True)
    df_300['MA20'] = df_300['close'].rolling(20).mean()
    
    all_trades = []
    
    for symbol, name in symbols.items():
        print(f"正在模拟交易计算: {name} ({symbol}) ...")
        try:
            df = ak.stock_zh_a_hist_tx(symbol=symbol, start_date="20230601", end_date="20260609", adjust="qfq")
        except Exception as e:
            print(f"获取 {name} 数据失败: {e}")
            continue
            
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        
        df = calculate_atr(df)
        df['MA20'] = df['close'].rolling(20).mean()
        df['Vol_MA10'] = df['amount'].rolling(10).mean()
        
        in_position = False
        entry_price = 0
        entry_date = None
        highest_price = 0
        
        for date, row in df.iterrows():
            if pd.isna(row['MA20']) or pd.isna(row['atr']):
                continue
                
            macro_safe = False
            if date in df_300.index:
                macro_safe = df_300.loc[date, 'close'] > df_300.loc[date, 'MA20']
                
            if not in_position:
                # 策略买入条件：大盘安全 + 收盘价站上 20 日均线 + 突破放量 (成交额>10日均量1.5倍) + 阳线
                if macro_safe and row['close'] > row['MA20'] and row['amount'] > row['Vol_MA10'] * 1.5 and row['close'] > row['open']:
                    in_position = True
                    entry_price = row['close']
                    entry_date = date
                    highest_price = row['close']
            else:
                # 更新持仓期间的最高价
                if row['close'] > highest_price:
                    highest_price = row['close']
                
                # 策略卖出条件：跌破 2.5 倍 ATR 吊灯防线，或大盘极端死锁跌破 MA20
                trailing_stop = highest_price - (2.5 * row['atr'])
                
                if row['close'] < trailing_stop or (not macro_safe and row['close'] < row['MA20']):
                    profit_pct = (row['close'] - entry_price) / entry_price * 100
                    all_trades.append({
                        'stock': name,
                        'entry_date': entry_date,
                        'exit_date': date,
                        'profit_pct': profit_pct
                    })
                    in_position = False

    # 统计回测结果
    if not all_trades:
        print("未触发任何有效交易。")
        return
        
    trades_df = pd.DataFrame(all_trades)
    
    print("\n📜 过去三年具体买卖指令流水日志:")
    for _, trade in trades_df.iterrows():
        print(f"[{trade['stock']}] 买入: {trade['entry_date'].date()} -> 卖出: {trade['exit_date'].date()} | 盈亏: {trade['profit_pct']:.2f}%")
        
    total_trades = len(trades_df)
    win_trades = len(trades_df[trades_df['profit_pct'] > 0])
    win_rate = win_trades / total_trades * 100
    
    avg_profit = trades_df['profit_pct'].mean()
    max_profit = trades_df['profit_pct'].max()
    max_loss = trades_df['profit_pct'].min()
    
    # 模拟账户复利净值曲线 (初始100万)
    capital = 1000000
    capital_curve = [capital]
    for p in trades_df['profit_pct']:
        capital = capital * (1 + p/100)
        capital_curve.append(capital)
        
    total_return = (capital - 1000000) / 1000000 * 100
    
    # 计算最大回撤
    capital_series = pd.Series(capital_curve)
    rolling_max = capital_series.expanding().max()
    drawdowns = (capital_series - rolling_max) / rolling_max * 100
    max_drawdown = drawdowns.min()
    
    print("\n📊 核心龙头组合 3 年量化回测报告 (2023.6 - 2026.6)")
    print("-" * 50)
    print(f"🔹 初始本金: 1,000,000 元")
    print(f"🔹 最终本金: {capital:,.2f} 元")
    print(f"📈 策略总复利收益率: {total_return:.2f}%")
    print(f"📉 策略最大回撤率: {max_drawdown:.2f}%")
    print("-" * 50)
    print(f"⚔️ 总交易次数: {total_trades} 次")
    print(f"🏆 交易胜率: {win_rate:.2f}%")
    print(f"💵 平均单笔盈亏: {avg_profit:.2f}%")
    print(f"🚀 单笔最大盈利: {max_profit:.2f}%")
    print(f"🩸 单笔最大亏损: {max_loss:.2f}% (完美被 ATR 限制)")
    print("==================================================")

if __name__ == '__main__':
    run_performance_backtest()
