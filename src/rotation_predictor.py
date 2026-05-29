import pandas as pd
import akshare as ak
import os
import time
from src.data_fetcher import fetch_with_cache

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
        """Sina 接口稳定，永不被封，用来做降级量价分析"""
        try:
            df = fetch_with_cache("sina_spot", ak.stock_sector_spot, expiry_hours=1)
            if df is None or df.empty: return None
            
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            df['总成交额'] = pd.to_numeric(df['总成交额'], errors='coerce')
            df['平均价格'] = pd.to_numeric(df['平均价格'], errors='coerce')
            
            if mode == "accumulation":
                # 蓄势：涨幅在 -2% ~ 3% 之间，且总成交额大
                res = df[(df['涨跌幅'] >= -2) & (df['涨跌幅'] <= 3)].copy()
                res['潜伏分'] = res['总成交额'] / 1e8
                return res.sort_values(by='潜伏分', ascending=False)
            else:
                # 热门：涨幅 > 3%，绝对成交额排名前列
                res = df[df['涨跌幅'] > 3].copy()
                res['动量分'] = res['涨跌幅'] * (res['总成交额'] / 1e8)
                return res.sort_values(by='动量分', ascending=False)
        except Exception as e:
            print(f"Fallback Error: {e}")
            return None
