import akshare as ak
import pandas as pd
from datetime import datetime

class UniverseScreener:
    def __init__(self):
        # 铁血清洗参数
        self.min_market_cap = 50 * 100000000  # 最低总市值 50亿
        self.min_turnover = 3 * 100000000     # 最低单日成交额 3亿 (确保流动性)
        
    def filter_universe(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ 启动 AlphaTide 底池清洗程序...")
        
        # 1. 获取全市场 A 股实时基础数据 (东方财富接口，速度极快)
        try:
            df_spot = ak.stock_zh_a_spot_em()
        except Exception as e:
            print(f"获取全市场数据失败: {e}")
            return []
            
        initial_count = len(df_spot)
        print(f"📊 初始全市场标的池: {initial_count} 只股票")

        # 2. 清洗逻辑
        # 规则 A: 剔除 ST、*ST 和 退市股
        df_clean = df_spot[~df_spot['名称'].str.contains('ST|退')]
        
        # 规则 B: 市值过滤 (> 50亿)
        df_clean = df_clean[df_clean['总市值'] >= self.min_market_cap]
        
        # 规则 C: 流动性过滤 (成交额 > 3亿)
        # 次新股 (只要上市满一小段时间，成交额和市值达标，依然会被保留！)
        df_clean = df_clean[df_clean['成交额'] >= self.min_turnover]
        
        # 规则 D: 剔除长期停牌 (成交量为 0 的股票)
        df_clean = df_clean[df_clean['成交量'] > 0]
        
        final_count = len(df_clean)
        
        # 提取保留下来的股票代码列表
        clean_symbols = df_clean['代码'].tolist()
        
        print(f"✅ 清洗完毕！")
        print(f"🚫 剔除了 {initial_count - final_count} 只垃圾股/僵尸股/微盘股")
        print(f"💎 剩余核心高流动性标的: {final_count} 只")
        
        return clean_symbols

if __name__ == "__main__":
    screener = UniverseScreener()
    core_universe = screener.filter_universe()
    # 打印前 20 只过审的股票看看
    print("\\n[Sample Core Universe]:", core_universe[:20])
