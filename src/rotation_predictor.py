import pandas as pd
import akshare as ak
import os

import time

class RotationPredictor:
    def __init__(self):
        # 强制绕过代理，直接连接国内行情服务器
        os.environ["NO_PROXY"] = "*"
        os.environ["HTTP_PROXY"] = ""
        os.environ["HTTPS_PROXY"] = ""

    def _fetch_with_retry(self, func, **kwargs):
        for i in range(3):
            try:
                # 某些接口对并发和连接非常敏感
                return func(**kwargs)
            except Exception as e:
                print(f"请求失败 (尝试 {i+1}/3): {e}")
                time.sleep(5)
        return None

    def predict_accumulation_sectors(self):
        """
        核心逻辑：寻找“反转”与“潜伏”信号。
        1. 拐点信号：10日流出，但5日转为流入。
        2. 蓄势信号：5日大幅流入，但价格涨幅尚未被引爆（<6%）。
        """
        try:
            print("正在获取10日行业资金流数据...")
            df_10d = self._fetch_with_retry(ak.stock_sector_fund_flow_rank, indicator="10日")
            
            print("正在获取5日行业资金流数据...")
            df_5d = self._fetch_with_retry(ak.stock_sector_fund_flow_rank, indicator="5日")

            if df_10d is None or df_5d is None:
                print("⚠️ 无法获取深度资金流向数据，正在启动备选实时强度分析...")
                return self._fallback_analysis()

            # 合并分析
            df = pd.merge(
                df_5d[['名称', '5日涨跌幅', '5日主力净流入-净额']], 
                df_10d[['名称', '10日涨跌幅', '10日主力净流入-净额']], 
                on='名称'
            )

            def calc_score(row):
                f5 = row['5日主力净流入-净额']
                f10 = row['10日主力净流入-净额']
                p5 = row['5日涨跌幅']
                
                # 核心过滤：剔除已经大涨的（追高风险）
                if p5 > 7.0: return 0 
                
                score = 0
                # A. 趋势拐点（从流出转为流入）
                if f10 < 0 and f5 > 0: score += 100 
                # B. 资金密集潜伏（5日流入占10日比例极高）
                if f5 > (f10 * 0.8) and f10 > 0: score += 60
                
                # C. 资金效率（每一份涨幅背后有多少资金在撑）
                efficiency = f5 / (abs(p5) + 2)
                return score + (efficiency / 1e7) # 评分加权

            df['蓄势指数'] = df.apply(calc_score, axis=1)
            results = df[df['蓄势指数'] > 0].sort_values(by='蓄势指数', ascending=False)
            return results

        except Exception as e:
            print(f"预测引擎运行错误: {e}")
            return None

    def _fallback_analysis(self):
        """备选方案：使用 Sina 接口分析实时板块成交热度与个股强度"""
        try:
            df = ak.stock_sector_spot()
            # 逻辑：寻找涨幅温和 (0-3%) 但成交额巨大的板块
            df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce')
            df['总成交额'] = pd.to_numeric(df['总成交额'], errors='coerce')
            # 过滤掉涨幅过大的，寻找低位放量的
            return df[(df['涨跌幅'] >= 0) & (df['涨跌幅'] < 4)].sort_values(by='总成交额', ascending=False)
        except:
            return None

if __name__ == "__main__":
    predictor = RotationPredictor()
    results = predictor.predict_accumulation_sectors()
    if results is not None and not results.empty:
        print("\n🔥 检测到潜在蓄势/低位放量板块:")
        # 根据返回的列名决定显示哪些
        if '名称' in results.columns:
            # 资金流向分析结果
            print(results[['名称', '5日涨跌幅', '5日主力净流入-净额', '蓄势指数']].head(10))
        else:
            # 备选实时强度分析结果 (Sina)
            print(results[['板块', '涨跌幅', '总成交额', '股票名称']].head(10))
    else:
        print("未能检测到明显的蓄势信号。")
