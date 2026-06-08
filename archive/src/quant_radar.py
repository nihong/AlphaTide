import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from .universe_screener import UniverseScreener

class QuantRadar:
    def __init__(self):
        self.screener = UniverseScreener()
        self.lookback_days = 10
        self.accumulation_days_threshold = 4 # Optimized: At least 4 days of high volume in the last 10 days
        self.max_price_spike = 0.15          # Do not buy if it already spiked > 15% in 10 days
        self.vol_multiplier = 1.2            # Optimized: Volume = 1.2x of 20-day average volume
        
    def scan_accumulation(self, symbols=None):
        if not symbols:
            print("[Quant Radar] 📡 Fetching RPS Top 10% Core Universe...")
            symbols = self.screener.filter_universe()
            
        print(f"\\n[Quant Radar] 🕵️ Scanning {len(symbols)} stocks for Volatility Contraction (VCP) & Breakout...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60) # Need 60 days to calc MA20 properly
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        vcp_pool = []
        
        # In a real production system, this would be heavily concurrent/async.
        scan_list = symbols[:150] if len(symbols) > 150 else symbols
        
        for idx, code in enumerate(scan_list):
            if idx % 20 == 0:
                print(f"  -> Scanning progress: {idx}/{len(scan_list)}...")
                
            if code.startswith("6") or code.startswith("5") or code.startswith("1"): prefix = "sh" + code
            elif code.startswith("0") or code.startswith("3"): prefix = "sz" + code
            else: continue
            
            try:
                # Fetch daily data
                df = ak.stock_zh_a_daily(symbol=prefix, start_date=start_str, end_date=end_str, adjust="qfq")
                if df.empty or len(df) < 30: continue
                
                # Calculate indicators
                df['ma20'] = df['close'].rolling(20).mean()
                df['ma60'] = df['close'].rolling(60).mean()
                df['vol_ma20'] = df['volume'].rolling(20).mean()
                
                # We need the last 15 days to check VCP
                last_15 = df.tail(15)
                if len(last_15) < 15: continue
                
                # 1. 趋势过滤 (Trend Filter): 必须在 20 日均线之上
                current_close = last_15.iloc[-1]['close']
                if current_close < last_15.iloc[-1]['ma20']: continue
                
                # 2. 价格波动率收缩 (Price Contraction)
                # 计算倒数第 15 天到倒数第 2 天的收盘价标准差，越小代表洗盘越彻底
                consolidation_period = last_15.iloc[0:-1]
                price_std = consolidation_period['close'].std()
                price_mean = consolidation_period['close'].mean()
                volatility_ratio = price_std / price_mean
                
                # 3. 缩量洗盘 (Volume Dry-up)
                # 盘整期的平均成交量必须低于 20 日均量
                avg_consolidation_vol = consolidation_period['volume'].mean()
                is_volume_dry = avg_consolidation_vol < consolidation_period.iloc[-1]['vol_ma20']
                
                # 4. 突破确认 (Breakout)
                # 最后一根 K 线必须是阳线 (收盘 > 开盘)，且温和放量 (大于 20 日均量 1.5 倍)
                latest_candle = last_15.iloc[-1]
                is_green_candle = latest_candle['close'] > latest_candle['open']
                is_breakout_vol = latest_candle['volume'] > (latest_candle['vol_ma20'] * 1.5)
                
                # 综合判断 VCP
                # volatility_ratio < 0.05 意味着过去两周上下振幅极小 (死寂)
                if volatility_ratio < 0.05 and is_volume_dry and is_green_candle and is_breakout_vol:
                    vcp_pool.append({
                        "symbol": code,
                        "vcp_score": round((0.05 - volatility_ratio) * 1000, 2), # 波动率越小，得分越高
                        "breakout_price": current_close
                    })
            except Exception as e:
                pass
                
        # Sort by VCP tightness score
        vcp_pool.sort(key=lambda x: x['vcp_score'], reverse=True)
        
        print(f"\\n✅ [Quant Radar] Scan complete! Found {len(vcp_pool)} stocks triggering VCP Breakout.")
        for p in vcp_pool[:5]:
            print(f"  🎯 Symbol {p['symbol']} | Tightness Score: {p['vcp_score']} | Breakout Price: {p['breakout_price']}")
            
        return vcp_pool

if __name__ == "__main__":
    radar = QuantRadar()
    radar.scan_accumulation()
