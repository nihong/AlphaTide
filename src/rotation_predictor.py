import pandas as pd
import os
import time
from src.data_fetcher import fetch_a_stock_hist_cached

CORE_SECTORS = {
    "酿酒行业": "600519", # 贵州茅台
    "半导体": "600584", # 长电科技
    "通信设备": "000063", # 中兴通讯
    "汽车零部件": "601689", # 拓普集团
    "电力行业": "600900", # 长江电力
    "煤炭行业": "601088", # 中国神华
    "医疗器械": "300760", # 迈瑞医疗
    "光伏设备": "601012", # 隆基绿能
    "风电设备": "601615", # 明阳智能
    "电池": "300750", # 宁德时代
    "消费电子": "002475", # 立讯精密
    "软件开发": "002230", # 科大讯飞
    "家电行业": "000333", # 美的集团
    "房地产开发": "000002", # 万科A
    "银行": "601398", # 工商银行
    "证券": "600030", # 中信证券
    "化学制药": "600276", # 恒瑞医药
    "中药": "000538", # 云南白药
    "农林牧渔": "002714", # 牧原股份
    "工程机械": "600031"  # 三一重工
}

class RotationPredictor:
    def __init__(self):
        os.environ["NO_PROXY"] = "*"
        os.environ["HTTP_PROXY"] = ""
        os.environ["HTTPS_PROXY"] = ""

    def predict_sectors(self, target_date=None):
        """
        双核驱动：杠铃策略
        返回: (蓄势板块 df, 热门板块 df)
        """
        print("🎯 [双重锁妖塔] 启动第一层：资金动量雷达扫描 (固定20大核心赛道)...")
        momentum, accumulation = self._scan_sectors_momentum(target_date)
        
        print("🔍 [双重锁妖塔] 启动第二层：行业基本面照妖镜...")
        accumulation = self._filter_by_fundamentals(accumulation, target_date)
        momentum = self._filter_by_fundamentals(momentum, target_date)
        
        return accumulation, momentum

    def _scan_sectors_momentum(self, target_date):
        """基于代表股票的历史K线计算板块动量，完美支持回测，且彻底绕过东财封锁"""
        scores = []
        for sector, rep_symbol in CORE_SECTORS.items():
            try:
                df = fetch_a_stock_hist_cached(rep_symbol, period="daily", adjust="qfq", expiry_hours=240)
                if df is None or df.empty: continue
                
                if target_date:
                    df['日期'] = pd.to_datetime(df['日期'])
                    df = df[df['日期'] <= pd.to_datetime(target_date)]
                    
                if len(df) < 25: continue
                
                df = df.tail(25)
                closes = df['收盘'].tolist()
                volumes = df['成交量'].tolist()
                
                ret_5d = (closes[-1] - closes[-5]) / closes[-5]
                vol_5d_avg = sum(volumes[-5:]) / 5.0
                vol_20d_avg = sum(volumes[-25:-5]) / 20.0 if len(volumes) >= 25 else sum(volumes[:-5]) / len(volumes[:-5])
                vol_ratio = vol_5d_avg / vol_20d_avg if vol_20d_avg > 0 else 1.0
                
                # 动量打分：5日大涨且放量
                mom_score = max(ret_5d, 0.0) * vol_ratio
                
                # 蓄势打分：5日横盘（振幅极小）且放量
                acc_score = (1.0 / (abs(ret_5d) * 10.0 + 0.1)) * vol_ratio
                
                scores.append({
                    '名称': sector,
                    '动量分': mom_score,
                    '潜伏分': acc_score
                })
            except Exception as e:
                pass
                
        if not scores: return pd.DataFrame(), pd.DataFrame()
        
        res_df = pd.DataFrame(scores)
        mom_df = res_df[res_df['动量分'] > 0].sort_values(by='动量分', ascending=False).head(5)
        acc_df = res_df[res_df['潜伏分'] > 0].sort_values(by='潜伏分', ascending=False).head(5)
        return mom_df, acc_df

    def _filter_by_fundamentals(self, df, target_date):
        if df is None or df.empty: return df
        from src.screener import Screener
        screener = Screener()
        valid_indices = []
        
        for idx, row in df.iterrows():
            sector_name = row.get('名称', row.get('板块', ''))
            label = row.get('label', None)
            
            f_data = screener.get_sector_fundamentals(sector_name, label, target_date)
            if f_data:
                # 核心过滤规则：利润正增长(>10%) 或 高价值(ROE>5%)
                if f_data['median_growth'] >= 10.0 or f_data['median_roe'] >= 5.0:
                    valid_indices.append(idx)
                    print(f"✅ 【放行】[{sector_name}]: 利润增速中位数 {f_data['median_growth']:.1f}%, ROE中位数 {f_data['median_roe']:.1f}%")
                else:
                    print(f"🚫 【拦截游资概念】[{sector_name}]: 利润中位数为 {f_data['median_growth']:.1f}% (<10%) 且 ROE极差。已踢出！")
            else:
                # 无基本面数据的板块(如部分特殊概念)暂且放行
                valid_indices.append(idx)
                
        return df.loc[valid_indices]
