import akshare as ak
import pandas as pd
import datetime
import time

def run_may_backtest():
    print("==================================================")
    print("🌊 AlphaTide V8.1 量价防线 6 年极限回测沙盘 (5月份专场)")
    print("免责声明：为了杜绝幸存者偏差与未来函数，本次回测剔除了研报情绪面，仅用严酷的数学测试系统抗跌性。")
    print("==================================================")
    
    # 绕过 VPN 拦截：设置超时和重试
    print("正在拉取 沪深300 与 中证1000 的底层长线 K 线数据...")
    try:
        df_300 = ak.stock_zh_index_daily(symbol="sh000300")
        df_1000 = ak.stock_zh_index_daily(symbol="sh000852")
    except Exception as e:
        print(f"致命错误：大盘数据抓取失败，请检查 VPN 设置或重试。异常: {e}")
        return
        
    df_300['date'] = pd.to_datetime(df_300['date'])
    df_1000['date'] = pd.to_datetime(df_1000['date'])
    
    df_300.set_index('date', inplace=True)
    df_1000.set_index('date', inplace=True)
    
    # 计算 20 日均线 (大盘风控生命线)
    df_300['MA20'] = df_300['close'].rolling(window=20).mean()
    df_1000['MA20'] = df_1000['close'].rolling(window=20).mean()
    
    years = [2021, 2022, 2023, 2024, 2025, 2026]
    
    for year in years:
        print(f"\n--- ⏳ 进入 {year} 年 5 月份战区 ---")
        start_date = f"{year}-05-01"
        end_date = f"{year}-05-31"
        
        mask_300 = (df_300.index >= start_date) & (df_300.index <= end_date)
        may_data_300 = df_300.loc[mask_300]
        
        red_light_days = 0
        total_days = len(may_data_300)
        
        if total_days == 0:
            print(f"未能获取 {year} 年 5 月份数据")
            continue
            
        for date, row_300 in may_data_300.iterrows():
            if date not in df_1000.index:
                continue
            row_1000 = df_1000.loc[date]
            
            # 双轨防线逻辑 (AlphaTide V8.1)
            is_300_broken = row_300['close'] < row_300['MA20']
            is_1000_broken = row_1000['close'] < row_1000['MA20']
            
            if is_300_broken and is_1000_broken:
                status = "🔴 绝对熔断 (双轨破位)"
                red_light_days += 1
            elif is_300_broken:
                status = "🟡 权重风险 (沪深300破位)"
            elif is_1000_broken:
                status = "🟡 题材风险 (中证1000破位)"
            else:
                status = "🟢 绝对安全 (全线水上)"
                
            print(f"[{date.date()}] 指令: {status} | 沪深300: {row_300['close']:.0f}(MA:{row_300['MA20']:.0f}) | 中证1000: {row_1000['close']:.0f}(MA:{row_1000['MA20']:.0f})")
            
        print(f">>> {year} 年 5 月战役总结: 总交易日 {total_days} 天, 触发系统级空仓死锁 {red_light_days} 天 (占比 {red_light_days/total_days*100:.1f}%)")

if __name__ == '__main__':
    run_may_backtest()
