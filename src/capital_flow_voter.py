import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time

class CapitalFlowVoter:
    def __init__(self):
        pass
        
    def get_market_prefix(self, symbol):
        if symbol.startswith("60") or symbol.startswith("51") or symbol.startswith("68"):
            return "sh" + symbol
        else:
            return "sz" + symbol

    def fetch_stock_data_with_retry(self, symbol, retries=3):
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        
        for attempt in range(retries):
            # Attempt 1: EastMoney (Primary)
            try:
                if symbol.startswith("51") or symbol.startswith("15"):
                    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                else:
                    df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                if not df.empty and '收盘' in df.columns:
                    return df
            except Exception as e:
                print(f"    [Flow Voter] EastMoney fetch failed for {symbol}: {e}. Trying Sina fallback...")
                
            # Attempt 2: Sina (Fallback 1)
            try:
                sina_symbol = self.get_market_prefix(symbol)
                df_sina = ak.stock_zh_a_daily(symbol=sina_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
                if not df_sina.empty:
                    # Rename columns to match EastMoney format so downstream logic works
                    df_sina = df_sina.rename(columns={"close": "收盘", "volume": "成交量"})
                    if '收盘' in df_sina.columns:
                        return df_sina
            except Exception as e:
                print(f"    [Flow Voter] Sina fetch failed for {symbol}: {e}. Trying Tencent fallback...")
                
            # Attempt 3: Tencent (Fallback 2)
            try:
                tx_symbol = self.get_market_prefix(symbol)
                # Tencent endpoint uses format like sh600519
                df_tx = ak.stock_zh_a_hist_tx(symbol=tx_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
                if not df_tx.empty:
                    # Tencent usually has 'close' and 'amount' or 'volume'
                    df_tx = df_tx.rename(columns={"close": "收盘", "amount": "成交量", "volume": "成交量"})
                    if '收盘' in df_tx.columns:
                        return df_tx
            except Exception as e:
                print(f"    [Flow Voter] Tencent fetch failed for {symbol}: {e}")
                
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
            return False, 0.0
            
        df['vol_ma20'] = df['成交量'].rolling(20).mean()
        df['price_ma20'] = df['收盘'].rolling(20).mean()
        
        latest = df.iloc[-1]
        
        # 1. Limit-Up Check (涨停板物理拦截)
        if '最高' in latest and latest['收盘'] == latest['最高'] and latest['最高'] > latest['开盘']:
            print(f"  -> 🛑 [Flow Voter] Symbol {symbol}: Limit-Up detected (close == high). Cannot buy. Rejected.")
            return False, 0.0
            
        vol_breakout = latest['成交量'] > (latest['vol_ma20'] * 1.5)
        price_uptrend = latest['收盘'] > latest['price_ma20']
        
        # Calculate Momentum (ROC)
        momentum_score = (latest['收盘'] - latest['price_ma20']) / latest['price_ma20']
        
        if vol_breakout and price_uptrend:
            print(f"  -> 💸 [Flow Voter] Symbol {symbol}: Smart Money accumulation! Vol={latest['成交量']}, Momentum={momentum_score:.2%}")
            return True, momentum_score
        else:
            reason = "No Volume Breakout" if not vol_breakout else "Price Below MA20"
            print(f"  -> 🐢 [Flow Voter] Symbol {symbol}: Rejected. Reason: {reason}")
            return False, 0.0
        
    def vote(self, candidates):
        print(f"[Flow Voter] 🗳️ Initiating Capital Flow Voting & Cross-Sectional Ranking for {len(candidates)} candidates...")
        
        # Sector Resonance Check
        resonance = self.check_sector_resonance()
        
        scored_candidates = []
        for stock in candidates:
            # If sector resonance is bad, we demand even stricter volume (or we just reject)
            if not resonance and stock['symbol'].startswith("300"):
                print(f"  -> 🛑 [Flow Voter] Symbol {stock['symbol']} rejected due to poor Sector Resonance.")
                continue
                
            passed, score = self.check_smart_money(stock['symbol'])
            if passed:
                stock['momentum'] = score
                scored_candidates.append(stock)
                
        # 2. Winner Takes All Ranking (赢者通吃)
        # Sort descending by momentum score and take top 3
        scored_candidates.sort(key=lambda x: x.get('momentum', 0), reverse=True)
        approved = scored_candidates[:3]
                
        print(f"[Flow Voter] 🏆 {len(approved)} stocks passed and ranked as Top Tier targets.")
        return approved

if __name__ == "__main__":
    voter = CapitalFlowVoter()
    voter.vote([{"symbol": "513100"}, {"symbol": "600519"}])
