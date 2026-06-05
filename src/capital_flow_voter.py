import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

class CapitalFlowVoter:
    def __init__(self):
        pass
        
    def fetch_stock_data_with_retry(self, symbol, retries=3):
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        for attempt in range(retries):
            try:
                if symbol.startswith("51") or symbol.startswith("15"):
                    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                if not df.empty:
                    return df
            except Exception as e:
                print(f"    [Flow Voter] Fetch attempt {attempt+1} failed for {symbol}: {e}")
                time.sleep(2)
        return pd.DataFrame()

    def check_sector_resonance(self):
        """Check if broad growth/tech index (ChiNext 159915) is in uptrend."""
        df = self.fetch_stock_data_with_retry("159915", retries=2)
        if df.empty or len(df) < 20:
            return True # Default to true if api fails
        df['price_ma20'] = df['收盘'].rolling(20).mean()
        latest = df.iloc[-1]
        if latest['收盘'] > latest['price_ma20']:
            print("  -> 🌊 Sector Resonance: Broad Growth Index is SURGING.")
            return True
        else:
            print("  -> 🛑 Sector Resonance: Broad Growth Index is WEAK.")
            return False

    def check_smart_money(self, symbol):
        df = self.fetch_stock_data_with_retry(symbol)
        if df.empty or len(df) < 20:
            print(f"  -> ❓ [Flow Voter] Symbol {symbol}: Insufficient data after retries.")
            return False
            
        df['vol_ma20'] = df['成交量'].rolling(20).mean()
        df['price_ma20'] = df['收盘'].rolling(20).mean()
        
        latest = df.iloc[-1]
        
        vol_breakout = latest['成交量'] > (latest['vol_ma20'] * 1.5)
        price_uptrend = latest['收盘'] > latest['price_ma20']
        
        if vol_breakout and price_uptrend:
            print(f"  -> 💸 [Flow Voter] Symbol {symbol}: Smart Money accumulation detected! Vol={latest['成交量']}, MA20={latest['vol_ma20']:.0f}")
            return True
        else:
            reason = "No Volume Breakout" if not vol_breakout else "Price Below MA20"
            print(f"  -> 🐢 [Flow Voter] Symbol {symbol}: Rejected. Reason: {reason}")
            return False
        
    def vote(self, candidates):
        print(f"[Flow Voter] 🗳️ Initiating Capital Flow Voting for {len(candidates)} candidates...")
        
        # Sector Resonance Check
        resonance = self.check_sector_resonance()
        
        approved = []
        for stock in candidates:
            # If sector resonance is bad, we demand even stricter volume (or we just reject)
            # For simplicity, if resonance is bad, we reject high-beta names
            if not resonance and stock['symbol'].startswith("300"):
                print(f"  -> 🛑 [Flow Voter] Symbol {stock['symbol']} rejected due to poor Sector Resonance.")
                continue
                
            if self.check_smart_money(stock['symbol']):
                approved.append(stock)
                
        print(f"[Flow Voter] 🏆 {len(approved)} stocks passed the Smart Money test.")
        return approved

if __name__ == "__main__":
    voter = CapitalFlowVoter()
    voter.vote([{"symbol": "513100"}, {"symbol": "600519"}])
