import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

# 彻底屏蔽代理，防止网络干扰
os.environ['NO_PROXY'] = '*'
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    os.environ.pop(proxy_var, None)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.data_fetcher import fetch_a_stock_hist

def calculate_120d_rps(symbol, target_date_str):
    """
    严格计算过去 120 个交易日的真实 RPS (相对沪深300指数的超额收益排名)
    """
    end_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    start_date = end_date - timedelta(days=200) # 多取几天以确保有足够的交易日
    
    # 1. 获取个股真实历史
    df_stock = fetch_a_stock_hist(symbol, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d"))
    if df_stock is None or df_stock.empty or len(df_stock) < 120:
        return None
        
    # 2. 获取沪深300历史作为大盘基准
    try:
        df_index = ak.stock_zh_index_daily(symbol="sh000300")
        df_index['date'] = pd.to_datetime(df_index['date'])
        df_index = df_index[(df_index['date'] >= start_date) & (df_index['date'] <= end_date)]
    except:
        return None

    if len(df_index) < 120:
        return None

    # 取最近 120 个交易日的涨跌幅
    stock_120d_return = (df_stock['收盘'].iloc[-1] / df_stock['收盘'].iloc[-120]) - 1
    index_120d_return = (df_index['close'].iloc[-1] / df_index['close'].iloc[-120]) - 1
    
    # 简单相对强度：跑赢大盘的幅度 (真实环境中应与全市场 5000 只股票排序，此处为简化版绝对超额收益要求)
    # 严格纪律：如果这 120 天连大盘都没跑赢 20% 以上，直接视为弱势股！
    relative_strength = stock_120d_return - index_120d_return
    return relative_strength

def main():
    print("[AlphaTide V8.0 绝对纪律执行器 - 启动]")
    print("此脚本拒绝任何主观脑补，没有通过 120 日量价测试的股票，一律视作垃圾。")
    
    targets = [
        {"symbol": "000048", "name": "京基智农", "logic": "大额回购"},
        {"symbol": "002428", "name": "云南锗业", "logic": "锗出口管制/光模块"},
        {"symbol": "688502", "name": "茂莱光学", "logic": "半导体光学卡脖子"}
    ]
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    passed_stocks = []
    
    for t in targets:
        print(f"\n正在审查: {t['name']} ({t['symbol']})")
        
        # 1. 执行 120 日相对强度审判 (替代单日涨跌幅伪 RPS)
        rs = calculate_120d_rps(t['symbol'], today_str)
        if rs is None:
            print("  ❌ 致命错误：无法获取完整的 120 日历史 K 线数据。依据铁律，强制熔断该标的。")
            continue
            
        print(f"  📊 过去 120 天跑赢沪深300的超额收益: {rs*100:.2f}%")
        
        # 严格纪律：120天内超额收益必须大于 20% 才能算作强势股 (模拟 RPS > 90)
        if rs < 0.20:
            print("  ❌ 判决：绝对弱势股！大资金根本没有形成长线护盘，全是短期炒作或左侧阴跌，淘汰！")
            continue
            
        print("  ✅ 判决：通过长线相对强度测试，属于真正的市场赢家。")
        passed_stocks.append(t['name'])

    print(f"\n==========================================")
    print(f"终极过审名单: {passed_stocks}")
    if not passed_stocks:
        print("结论：当前市场环境下，所有候选标的均为垃圾，系统强制空仓！")
    print(f"==========================================")

if __name__ == "__main__":
    main()
