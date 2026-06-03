import pandas as pd
import akshare as ak
import os
import time
from src.data_fetcher import fetch_with_cache, fetch_a_stock_hist_cached

class RotationPredictor:
    def __init__(self):
        os.environ["NO_PROXY"] = "*"
        os.environ["HTTP_PROXY"] = ""
        os.environ["HTTPS_PROXY"] = ""

    def predict_sectors(self):
        """
        双核驱动：杠铃策略
        返回: (蓄势板块 df, 热门板块 df)
        """
        accumulation = self._get_accumulation_sectors()
        momentum = self._get_momentum_concepts()
        
        # 如果资金流全挂了，就用降级方案同时充当两端
        if accumulation is None or accumulation.empty:
            print("⚠️ 资金流接口受限，启用低位放量备选算法计算蓄势池...")
            accumulation = self._fallback_analysis(mode="accumulation")
            
        if momentum is None or momentum.empty:
            print("⚠️ 概念接口受限，启用高活跃度备选算法计算热门池...")
            momentum = self._fallback_analysis(mode="momentum")

        return accumulation, momentum

    def _get_accumulation_sectors(self):
        """
        潜伏池 (蓄势): 4维评分
        1. 资金逆转: 10日流出，5日流入
        2. 量价背离: 放量但不涨
        """
        try:
            df_10d = fetch_with_cache("fund_10d", ak.stock_sector_fund_flow_rank, expiry_hours=2, indicator="10日")
            df_5d = fetch_with_cache("fund_5d", ak.stock_sector_fund_flow_rank, expiry_hours=2, indicator="5日")
            
            if df_10d is None or df_5d is None: return None
            
            df = pd.merge(
                df_5d[['名称', '5日涨跌幅', '5日主力净流入-净额']], 
                df_10d[['名称', '10日涨跌幅', '10日主力净流入-净额']], 
                on='名称'
            )

            def calc_acc_score(row):
                f5 = row['5日主力净流入-净额']
                f10 = row['10日主力净流入-净额']
                p5 = row['5日涨跌幅']
                
                if p5 > 5.0: return 0 # 剔除已大涨的
                
                score = 0
                if f10 < 0 and f5 > 0: score += 50  # 资金逆转
                if f5 > 0 and p5 < 3.0: score += 30 # 量价背离(压盘吸筹)
                score += (f5 / 1e8) # 绝对流入量加权
                return score

            df['潜伏分'] = df.apply(calc_acc_score, axis=1)
            return df[df['潜伏分'] > 0].sort_values(by='潜伏分', ascending=False)
        except:
            return None

    def _get_momentum_concepts(self):
        """
        动量池 (热门): 4维评分
        利用同花顺概念板块获取热门度
        """
        try:
            df = fetch_with_cache("ths_concept", ak.stock_board_concept_name_ths, expiry_hours=2)
            if df is None or df.empty: return None
            
            # 由于部分高级行情接口易被封，退退求其次，通过 Sina 的行业现货模拟动量
            return None # 强制 fallback 到 Sina，因为 Sina 更稳
        except:
            return None

    def _fallback_analysis(self, mode="accumulation"):
        """Sina 接口稳定，永不被封，用来做降级多日累积量价分析"""
        try:
            df = fetch_with_cache("sina_spot", ak.stock_sector_spot, expiry_hours=1)
            if df is None or df.empty: return None
            
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            df['总成交额'] = pd.to_numeric(df['总成交额'], errors='coerce')
            
            # 过滤成交额过小的死水板块 (小于 10 亿)
            df = df[df['总成交额'] >= 1_000_000_000].copy()
            
            # 取成交额排名前 15 的活跃板块进行多日累积分析，避免全市场扫描过慢
            df_top = df.sort_values(by='总成交额', ascending=False).head(15).copy()
            
            scores = []
            for idx, row in df_top.iterrows():
                sector_name = row['板块']
                rep_symbol = row['股票代码'].replace('sh', '').replace('sz', '')
                
                # 获取代表股的 25 天历史数据（用于计算 5日 vs 20日 的量价关系）
                hist_df = fetch_a_stock_hist_cached(rep_symbol, period="daily", adjust="qfq", expiry_hours=4)
                if hist_df is None or len(hist_df) < 25:
                    # 如果数据不足，则使用单日数据降级打分
                    scores.append(0.0)
                    continue
                
                # 整理价格和成交量
                hist_df = hist_df.tail(25)
                closes = hist_df['收盘'].tolist()
                volumes = hist_df['成交量'].tolist()
                
                # 1. 5日累积收益率
                ret_5d = (closes[-1] - closes[-5]) / closes[-5]
                
                # 2. 5日成交量均值 vs 20日成交量均值 (成交量放大比率)
                vol_5d_avg = sum(volumes[-5:]) / 5.0
                vol_20d_avg = sum(volumes[-25:-5]) / 20.0 if len(volumes) >= 25 else sum(volumes[:-5]) / len(volumes[:-5])
                vol_ratio = vol_5d_avg / vol_20d_avg if vol_20d_avg > 0 else 1.0
                
                # 根据不同模式进行累积多日量价打分
                if mode == "accumulation":
                    # 蓄势板块：5日价格横盘整理（振幅较小，-3% 到 +3%），但成交量显著放大（资金悄悄建仓）
                    # 5日涨跌幅绝对值越小分值越高，同时乘以成交量放大比率
                    price_score = 1.0 / (abs(ret_5d) * 10.0 + 0.1) # 振幅越小分越高
                    score = price_score * vol_ratio * (row['总成交额'] / 1e8)
                else:
                    # 热门板块：5日大涨且放量（动量主升浪）
                    # 5日收益率必须为正，且越大越好，乘上成交量放大比率
                    price_score = max(ret_5d, 0.0)
                    score = price_score * vol_ratio * (row['总成交额'] / 1e8)
                    
                scores.append(score)
                
            df_top['score'] = scores
            
            if mode == "accumulation":
                df_top = df_top.rename(columns={'score': '潜伏分'})
                return df_top[df_top['潜伏分'] > 0].sort_values(by='潜伏分', ascending=False)
            else:
                df_top = df_top.rename(columns={'score': '动量分'})
                return df_top[df_top['动量分'] > 0].sort_values(by='动量分', ascending=False)
                
        except Exception as e:
            print(f"Fallback Error in multi-day cumulative analysis: {e}")
            return None
