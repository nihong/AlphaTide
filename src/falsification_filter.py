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
                latest_pmi = pmi_df.iloc[-1]['PMI']
                return latest_pmi
        except Exception as e:
            print(f"Error fetching PMI: {e}")
        return 50.0 # Neutral default

    def check_macro_data(self, theme):
        """
        Connects to Akshare to verify macro/industry data.
        Returns True if the physical data supports the theme.
        """
        print(f"[Truth Filter] 🕵️ Validating Alternative Data for theme: {theme}...")
        
        # General Macro Weather Check: PMI
        latest_pmi = self.get_latest_pmi()
        print(f"  -> 📊 Latest China Manufacturing PMI: {latest_pmi}")
        
        if latest_pmi < 50.0:
            print(f"  -> ⚠️ Systemic Macro Warning: PMI indicates economic contraction.")
            # If it's a growth/cyclical theme during contraction, veto it.
            if any(keyword in theme.lower() for keyword in ['growth', 'consumer', 'cyclical', 'ev', 'tech']):
                print(f"  -> ❌ FAKE LOGIC DETECTED! Macro environment does not support high-beta growth. VETO.")
                return False
                
        print(f"  -> ✅ Physical macro environment permits this narrative.")
        return True
        
    def filter_watchlist(self):
        if not os.path.exists(self.watchlist_file):
            print("[Truth Filter] Watchlist not found.")
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
