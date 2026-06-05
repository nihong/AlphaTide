import json
import os
import akshare as ak
import pandas as pd
from datetime import datetime

class FalsificationFilter:
    def __init__(self):
        self.watchlist_file = "data/watchlist.json"
        
    def get_latest_pmi(self):
        try:
            pmi_df = ak.macro_china_pmi()
            if '月份' in pmi_df.columns:
                pmi_df['日期'] = pd.to_datetime(pmi_df['月份'], format='%Y年%m月份')
                pmi_df['PMI'] = pd.to_numeric(pmi_df['制造业-指数'], errors='coerce')
                pmi_df = pmi_df.sort_values('日期')
                return pmi_df.iloc[-1]['PMI']
        except Exception as e:
            print(f"Error fetching PMI: {e}")
        return 50.0 
        
    def get_specific_macro(self, theme):
        """Map themes to specific Sector ETFs as alternative data proxies"""
        theme = theme.lower()
        proxy_symbol = None
        
        if 'ship' in theme or 'export' in theme or 'freight' in theme:
            print("    -> [Mapping] Found Shipping Theme. Using Shipping ETF (159765) as proxy...")
            proxy_symbol = "159765"
            
        elif 'pork' in theme or 'agri' in theme:
            print("    -> [Mapping] Found Agriculture Theme. Using Agri ETF (159825) as proxy...")
            proxy_symbol = "159825"
            
        elif 'semi' in theme or 'tech' in theme or 'ai' in theme:
            print("    -> [Mapping] Found Tech Theme. Using Semiconductor ETF (512480) as proxy...")
            proxy_symbol = "512480"
            
        elif 'gold' in theme or 'hedge' in theme:
            print("    -> [Mapping] Found Safe Haven Theme. Using Gold ETF (518880) as proxy...")
            proxy_symbol = "518880"
            
        if proxy_symbol:
            # We import CapitalFlowVoter to use its robust fetcher
            from capital_flow_voter import CapitalFlowVoter
            fetcher = CapitalFlowVoter()
            df = fetcher.fetch_stock_data_with_retry(proxy_symbol, retries=2)
            if not df.empty and len(df) >= 20:
                df['ma20'] = df['收盘'].rolling(20).mean()
                latest = df.iloc[-1]
                if latest['收盘'] >= latest['ma20']:
                    print(f"      -> 📈 Sector Proxy ({proxy_symbol}) is in uptrend. Validated.")
                    return True
                else:
                    print(f"      -> 📉 Sector Proxy ({proxy_symbol}) is in downtrend. Failed Validation.")
                    return False
            else:
                print(f"      -> ⚠️ Could not fetch proxy {proxy_symbol}. Assuming true for safety.")
                return True
                
        return True # Default pass if no specific mapping

    def check_macro_data(self, theme):
        print(f"[Truth Filter] 🕵️ Validating Alternative Data for theme: {theme}...")
        
        # 1. Global Macro Weather Check
        latest_pmi = self.get_latest_pmi()
        print(f"  -> 📊 Latest China Manufacturing PMI: {latest_pmi}")
        
        if latest_pmi < 50.0:
            if any(keyword in theme.lower() for keyword in ['growth', 'consumer', 'cyclical', 'ev', 'tech', 'semi']):
                print(f"  -> ❌ FAKE LOGIC DETECTED! Macro environment does not support high-beta growth. VETO.")
                return False
                
        # 2. Industry-Specific Alternative Data Check
        if not self.get_specific_macro(theme):
            print(f"  -> ❌ FAKE LOGIC DETECTED! Industry-specific alternative data contradicts narrative. VETO.")
            return False
                
        print(f"  -> ✅ Physical macro environment permits this narrative.")
        return True
        
    def filter_watchlist(self):
        if not os.path.exists(self.watchlist_file):
            return []
            
        with open(self.watchlist_file, "r") as f:
            data = json.load(f)
            
        survivors = []
        for stock in data.get("stocks", []):
            if self.check_macro_data(stock["theme"]):
                survivors.append(stock)
                
        print(f"[Truth Filter] 🛡️ Filter complete. {len(survivors)}/{len(data.get('stocks', []))} stocks survived falsification.")
        return survivors

if __name__ == "__main__":
    ff = FalsificationFilter()
    ff.filter_watchlist()
