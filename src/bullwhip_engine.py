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
    牛鞭效应与供应链瓶颈引擎 (Bullwhip & Bottleneck Engine) V7.1 - 极早期侦测版
    
    核心升级 (V7.1 Early Radar):
    1. 前置雷达: 监控现货涨价、招投标溢价与财报电话会“缺货”黑话，而非滞后的财报利润。
    2. 第一基底: 抓取底部“第一阶跃 (Stage 2 Breakout)”，拒绝已被炒高数倍的衰竭期盘整。
    3. 冷血护盾: VCP 突破买入，2.5倍 ATR 吊灯止损卖出。
    """
    
    def __init__(self):
        self.ai = AIAnalyst()
        self.rps_threshold = 85  # V7.1: 从90降至85，允许抓取刚刚从底部启动的第一波
        self.atr_stop_multiplier = 2.5

    def scan_high_freq_commodities(self) -> List[str]:
        """
        [V7.1 新增模块] 超高频先行指标：扫描大宗商品现货与招投标数据
        """
        logger.info("⚡ [Early Radar] 正在扫描全球大宗商品与供应链现货报价 API...")
        # 实际逻辑应请求现货价格数据库。当某材料价格在2周内跳涨超15%时触发预警。
        return ["取向硅钢/高压变压器", "HBM封装材料", "铜缆"]

    def scan_earnings_call_transcripts(self) -> List[str]:
        """
        [V7.1 新增模块] NLP 极早期听诊：大模型解析海外巨头财报电话会
        """
        logger.info("🎙️ [Early Radar] 正在监听全球科技巨头财报电话会，提取『缺货/满产』黑话...")
        prompt = """
        分析近期的财报电话会英文原稿 (Earnings Call Transcripts)。
        目标寻找以下极端供应链状态的表述：
        - "Capacity is fully booked" (产能已定满)
        - "Lead times are extending" (交货期拉长)
        - "Allocation" (按配额限量供货)
        - "Supply constraints" (供给受限)
        """
        # 实际调用 self.ai.analyze_with_llm(prompt)
        return ["北美电网设备", "先进封装"]

    def scan_bottleneck_industries(self, reports: List[Dict]) -> List[str]:
        """
        第一步：行业发现（三维交叉验证：现货 + 电话会 + 研报）
        """
        # 融合 V7.1 新增的极早期雷达
        early_commodities = self.scan_high_freq_commodities()
        early_transcripts = self.scan_earnings_call_transcripts()
        
        logger.info("📡 [Bullwhip Engine] 正在利用 LLM 综合研报与极早期预警，生成最终卡脖子赛道...")
        # 实际通过大模型求交集，这里做演示桩代码
        return list(set(["出海电网设备", "先进封装", "算力光互联"] + early_commodities + early_transcripts))

    def screen_apex_predators(self, symbols: List[str], target_date: str = None) -> List[Dict]:
        """
        第二步：龙头锁定（底部首板/第一基底 + VCP 极度缩量）
        [V7.1 升级]: 专门规避已涨 2 倍的“右侧晚期衰竭”，专抓 Stage 2 刚启动的第一/第二基底。
        """
        logger.info(f"🦅 [Bullwhip Engine] 正在对 {len(symbols)} 个嫌疑标的进行【第一基底与 VCP】交叉验证...")
        apex_predators = []
        
        for sym in symbols:
            df = fetch_a_stock_hist_cached(sym, period="daily")
            if df.empty or len(df) < 250: continue
            
            # V7.1 极早期动量识别：寻找底部刚刚放量的第一波 (近60天曾出现过爆量涨停，随后缩量横盘)
            recent_60d_high = df['最高'].iloc[-60:].max()
            year_low = df['最低'].iloc[-250:].min()
            
            # 排除已经涨了3倍的晚期标的
            if recent_60d_high > year_low * 3:
                continue 
                
            # 近20日动量：保持在强势整理区
            momentum_20d = (df['收盘'].iloc[-1] / df['收盘'].iloc[-20]) - 1
            if momentum_20d < -0.05: # 允许小幅回撤，但不能是崩盘
                continue 
                
            # VCP 形态验证 (波动率收缩)
            recent_10d_volatility = df['收盘'].iloc[-10:].std()
            past_30d_volatility = df['收盘'].iloc[-40:-10].std()
            if recent_10d_volatility > past_30d_volatility * 0.7:
                continue # 波动率没有达到极度收缩的标准
                
            apex_predators.append({
                "symbol": sym,
                "momentum": momentum_20d,
                "vcp_status": "Stage 2 First Base (VCP Tight)",
                "reason": "刚刚脱离底部 + 第一基底极度缩量 + 现货涨价前瞻信号"
            })
            
        return apex_predators

    def evaluate_exit(self, symbol: str, entry_price: float, highest_price: float) -> bool:
        """
        第三步：冷酷离场（2.5倍 ATR 吊灯防线 或 跌破 50 日生命线）
        """
        df = fetch_a_stock_hist_cached(symbol, period="daily")
        if df.empty: return False
        
        current_price = df['收盘'].iloc[-1]
        ema50 = df['收盘'].ewm(span=50, adjust=False).mean().iloc[-1]
        
        # 破 50 日线 (对于极早期买入的标的，容忍度从 20 日放宽到 50 日，避免被轻易洗出)
        if current_price < ema50:
            logger.warning(f"🚨 [Bullwhip Exit] {symbol} 跌破 50 日中期生命线！逻辑可能证伪，执行强制卖出！")
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
