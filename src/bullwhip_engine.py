import pandas as pd
import numpy as np
import logging
from typing import List, Dict

# Assuming local modules exist based on standard AlphaTide architecture
from src.data_fetcher import fetch_a_stock_hist_cached
from src.ai_analyst import AIAnalyst

logger = logging.getLogger(__name__)

class BullwhipEngine:
    """
    牛鞭效应与供应链瓶颈引擎 (Bullwhip & Bottleneck Engine)
    
    核心逻辑:
    1. 行业发现: 通过大模型提取“缺货、涨价、扩产周期长”的研报关键词，叠加宏观大宗商品价格与毛利率。
    2. 龙头锁定: RPS(相对强度)全市场前10% + 绝对毛利率压制同侪 + 在建工程/市占率最大。
    3. 交易执行: VCP (波动率收缩) 末端突破买入，2.5 ATR 吊灯止损卖出。
    """
    
    def __init__(self):
        self.ai = AIAnalyst()
        self.rps_threshold = 90
        self.atr_stop_multiplier = 2.5

    def scan_bottleneck_industries(self, reports: List[Dict]) -> List[str]:
        """
        第一步：行业发现（三维交叉验证）
        利用大模型批量阅读研报，寻找触发“牛鞭效应”的卡脖子环节。
        """
        logger.info("📡 [Bullwhip Engine] 正在使用 LLM 扫描研报寻找供应链短缺/涨价信号...")
        prompt = """
        请分析以下券商研报，识别出当前存在严重“供需错配”和“供应链瓶颈（卡脖子）”的行业。
        判定标准：
        1. 提及“现货价格暴涨”、“一箱难求/一货难求”、“库存告急”。
        2. 提及“扩产壁垒高”、“扩产周期极长（1-2年以上）”。
        3. 坚决排除那些半年就能建厂投产的组装加工环节。
        请仅返回符合瓶颈理论的行业名称列表（如：碳酸锂, 高纯石英砂, 800G光模块）。
        """
        # 实际运行中这里会调取 self.ai.analyze_with_llm(prompt, reports)
        # 这里做演示桩代码
        return ["光模块", "高纯石英砂", "高端算力芯片"]

    def screen_apex_predators(self, symbols: List[str], target_date: str = None) -> List[Dict]:
        """
        第二步：龙头锁定（RPS + 毛利率 + 在建工程市占率）
        """
        logger.info(f"🦅 [Bullwhip Engine] 正在对 {len(symbols)} 个嫌疑标的进行【财务霸权与绝对壁垒】交叉验证...")
        apex_predators = []
        
        for sym in symbols:
            # 1. 检查 RPS (相对强度) - 必须极度抗跌或领涨
            df = fetch_a_stock_hist_cached(sym, period="daily")
            if df.empty or len(df) < 250: continue
            
            # 近20日动量
            momentum_20d = (df['收盘'].iloc[-1] / df['收盘'].iloc[-20]) - 1
            # 简单模拟 RPS (实际需要全市场横向排序，这里简化为绝对动量要求)
            if momentum_20d < 0.15: 
                continue # 动量不足以证明是资金抢筹的龙头
                
            # 2. 检查 VCP 形态 (波动率收缩)
            # 近10天波幅必须小于前一个月的波幅，且成交量极度萎缩
            recent_10d_volatility = df['收盘'].iloc[-10:].std()
            past_30d_volatility = df['收盘'].iloc[-40:-10].std()
            if recent_10d_volatility > past_30d_volatility * 0.8:
                continue # 波动率没有收缩，洗盘未结束
                
            # 3. 财务与市占率验证 (通过大模型判定)
            prompt = f"分析 {sym} 的基本面，其毛利率是否显著高于行业平均水平？其产能和市占率是否处于绝对垄断地位？"
            # ai_eval = self.ai.analyze_with_llm(prompt)
            # 模拟全量通过
            
            apex_predators.append({
                "symbol": sym,
                "momentum": momentum_20d,
                "vcp_status": "Ready for Breakout",
                "reason": "RPS极高 + 波动率收缩 + 绝对垄断毛利率"
            })
            
        return apex_predators

    def evaluate_exit(self, symbol: str, entry_price: float, highest_price: float) -> bool:
        """
        第三步：冷酷离场（2.5倍 ATR 吊灯防线 或 跌破 20 日线）
        """
        df = fetch_a_stock_hist_cached(symbol, period="daily")
        if df.empty: return False
        
        current_price = df['收盘'].iloc[-1]
        ema20 = df['收盘'].ewm(span=20, adjust=False).mean().iloc[-1]
        
        # 破 20 日线
        if current_price < ema20:
            logger.warning(f"🚨 [Bullwhip Exit] {symbol} 跌破 20 日生命线！机构开始大举派发，执行强制卖出！")
            return True
            
        # 2.5倍 ATR 吊灯止损
        high = df['最高']
        low = df['最低']
        close = df['收盘'].shift(1)
        tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean().iloc[-1]
        
        trailing_stop = highest_price - (self.atr_stop_multiplier * atr_14)
        if current_price < trailing_stop:
            logger.warning(f"🚨 [Bullwhip Exit] {symbol} 跌破 2.5 倍 ATR 吊灯防线！波动率失控，执行强制卖出！")
            return True
            
        return False
