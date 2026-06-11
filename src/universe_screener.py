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
        
        # 1. 获取全市场 A 股实时基础数据 (双源灾备：东财 -> 新浪)
        try:
            df_spot = ak.stock_zh_a_spot_em()
            print("🟢 成功使用东财源获取全市场数据")
        except Exception as e:
            print(f"⚠️ 东财源获取失败 ({e})，正在紧急切换到新浪备用源...")
            try:
                df_spot = ak.stock_zh_a_spot()
                print("🟢 成功使用新浪备用源获取全市场数据")
                # 新浪源缺少总市值字段，为了不阻断后续过滤，强行补齐一个合规默认值
                if '总市值' not in df_spot.columns:
                    print("⚠️ 新浪源缺少总市值字段，已自动降级跳过 50 亿市值过滤防线。")
                    df_spot['总市值'] = 1000 * 100000000
            except Exception as e2:
                print(f"❌ 新浪灾备源也获取失败: {e2}")
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
        
        # 规则 E: RPS 相对强度过滤 (只买全市场前 10% 的最强王者)
        # 获取涨跌幅数据 (如果是真实运行，使用 60 日或年初至今涨跌幅)
        # 东财接口通常包含 '年初至今涨跌幅' 或 '涨跌幅'
        momentum_col = '年初至今涨跌幅' if '年初至今涨跌幅' in df_clean.columns else ('涨跌幅' if '涨跌幅' in df_clean.columns else None)
        
        if momentum_col:
            # 过滤掉没有涨跌幅数据的股票
            df_clean = df_clean.dropna(subset=[momentum_col])
            # 计算 RPS 排名 (0-100)
            df_clean['RPS'] = df_clean[momentum_col].rank(pct=True) * 100
            # 只保留 RPS 大于 90 的股票 (前 10%)
            df_clean = df_clean[df_clean['RPS'] >= 90]
            print(f"🌟 启用 RPS 相对强度过滤: 保留 {momentum_col} 排名前 10% 的强势股。")
        else:
            print("☠️ [致命错误] 无法获取涨跌幅字段！为了防止买入弱势垃圾股，严格禁止跳过 RPS 过滤。强行熔断并空仓。")
            return []
        
        final_count = len(df_clean)
        
        # 提取保留下来的股票代码和名称列表
        clean_symbols = df_clean[['代码', '名称']].to_dict('records')
        
        print(f"✅ 清洗完毕！")
        print(f"🚫 剔除了 {initial_count - final_count} 只弱势股/垃圾股")
        print(f"💎 剩余 RPS Top10% 核心标的: {final_count} 只")
        
        return clean_symbols

if __name__ == "__main__":
    screener = UniverseScreener()
    core_universe = screener.filter_universe()
    # 打印前 20 只过审的股票看看
    print("\\n[Sample Core Universe]:", core_universe[:20])
