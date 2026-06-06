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
        self.accumulation_days_threshold = 3 # At least 3 days of high volume in the last 10 days
        self.max_price_spike = 0.15          # Do not buy if it already spiked > 15% in 10 days
        self.vol_multiplier = 1.5            # High volume = 1.5x of 20-day average volume
        
    def scan_accumulation(self, symbols=None):
        if not symbols:
            print("[Quant Radar] 📡 Fetching Core Universe...")
            symbols = self.screener.filter_universe()
            
        print(f"\\n[Quant Radar] 🕵️ Scanning {len(symbols)} stocks for 10-day Institutional Accumulation...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60) # Need 60 days to calc MA20 properly
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        accumulation_pool = []
        
        # In a real production system, this would be heavily concurrent/async.
        # For demonstration, we will scan the first 100 to save API time if the list is huge.
        scan_list = symbols[:150] if len(symbols) > 150 else symbols
        
        for idx, code in enumerate(scan_list):
            if idx % 20 == 0:
                print(f"  -> Scanning progress: {idx}/{len(scan_list)}...")
                
            if code.startswith("6") or code.startswith("5"): prefix = "sh" + code
            elif code.startswith("0") or code.startswith("3") or code.startswith("1"): prefix = "sz" + code
            else: continue
            
            try:
                # Fetch daily data
                df = ak.stock_zh_a_daily(symbol=prefix, start_date=start_str, end_date=end_str, adjust="qfq")
                if df.empty or len(df) < 30: continue
                
                # Calculate indicators
                df['ma20'] = df['close'].rolling(20).mean()
                df['vol_ma20'] = df['volume'].rolling(20).mean()
                
                # Get the last 10 days
                last_10 = df.tail(self.lookback_days)
                if len(last_10) < self.lookback_days: continue
                
                # 1. Volume Accumulation Check
                # How many days had volume > 1.5 * vol_ma20?
                high_vol_days = len(last_10[last_10['volume'] > last_10['vol_ma20'] * self.vol_multiplier])
                
                if high_vol_days >= self.accumulation_days_threshold:
                    # 2. Price Constraint Check (Avoid buying the top)
                    price_start = last_10.iloc[0]['close']
                    price_end = last_10.iloc[-1]['close']
                    price_change = (price_end - price_start) / price_start
                    
                    # Ensure it's in a general uptrend (> MA20) but hasn't exploded yet (< 15%)
                    if 0 < price_change < self.max_price_spike and price_end > last_10.iloc[-1]['ma20']:
                        
                        # Sector Resonance Placeholder: In real life, we'd map code to sector here
                        accumulation_pool.append({
                            "symbol": code,
                            "accumulation_score": high_vol_days,
                            "10d_price_change": round(price_change, 3)
                        })
            except Exception as e:
                # Silently skip API errors for individual stocks
                pass
                
        # Sort by accumulation score (number of high volume days)
        accumulation_pool.sort(key=lambda x: x['accumulation_score'], reverse=True)
        
        print(f"\\n✅ [Quant Radar] Scan complete! Found {len(accumulation_pool)} stocks under stealth accumulation.")
        for p in accumulation_pool[:5]:
            print(f"  🎯 Symbol {p['symbol']} | High Vol Days: {p['accumulation_score']} | 10d Change: {p['10d_price_change']*100:.1f}%")
            
        return accumulation_pool

if __name__ == "__main__":
    radar = QuantRadar()
    radar.scan_accumulation()
