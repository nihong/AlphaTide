import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

class CapitalFlowVoter:
    def __init__(self):
        pass
        
    def fetch_stock_data(self, symbol):
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        try:
            if symbol.startswith("51") or symbol.startswith("15"):
                df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            else:
                df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def check_smart_money(self, symbol):
        """
        Check if Smart Money / Institutional Volume is accumulating.
        Requires today's volume to be > 1.5x the 20-day moving average volume.
        Requires price > 20-day moving average.
        """
        df = self.fetch_stock_data(symbol)
        if df.empty or len(df) < 20:
            print(f"  -> ❓ [Flow Voter] Symbol {symbol}: Insufficient data.")
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
        approved = []
        for stock in candidates:
            if self.check_smart_money(stock['symbol']):
                approved.append(stock)
                
        print(f"[Flow Voter] 🏆 {len(approved)} stocks passed the Smart Money test.")
        return approved

if __name__ == "__main__":
    voter = CapitalFlowVoter()
    voter.vote([{"symbol": "513100"}, {"symbol": "600519"}])
