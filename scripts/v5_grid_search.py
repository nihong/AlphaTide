import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import itertools
import os

class V5Optimizer:
    def __init__(self):
        self.start_date = "20180101"
        self.end_date = "20240101"
        self.initial_capital = 1000000.0
        
        # 3 highly representative stocks to prevent API hanging
        self.test_symbols = [
            "sz002594", # BYD
            "sz300750", # CATL
            "sz300059"  # East Money
        ]
        self.market_data = {}

    def fetch_data(self):
        print("📡 Downloading 6-year data for optimization universe...")
        all_dates = set()
        for sym in self.test_symbols:
            print(f"   Downloading {sym}...")
            try:
                df = ak.stock_zh_a_daily(symbol=sym, start_date=self.start_date, end_date=self.end_date, adjust="qfq")
                if df is not None and not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date').set_index('date')
                    df['prev_close'] = df['close'].shift(1)
                    df['tr'] = np.maximum(df['high'] - df['low'], 
                                        np.maximum(abs(df['high'] - df['prev_close']), 
                                                 abs(df['low'] - df['prev_close'])))
                    df['atr'] = df['tr'].rolling(14).mean()
                    self.market_data[sym] = df
                    all_dates.update(df.index.tolist())
            except Exception as e:
                pass
        self.sorted_dates = sorted(list(all_dates))
        print("✅ Data ready.")

    def run_backtest(self, params):
        vol_multiplier = params['vol_multiplier']
        acc_days = params['acc_days']
        atr_mult = params['atr_mult']
        max_pos = params['max_pos']
        ai_approval_rate = params['ai_rate'] # To simulate the AI's accuracy

        capital = self.initial_capital
        positions = {}
        
        # Pre-calculate MA for speed
        for sym in self.market_data:
            self.market_data[sym]['ma20'] = self.market_data[sym]['close'].rolling(20).mean()
            self.market_data[sym]['vol_ma20'] = self.market_data[sym]['volume'].rolling(20).mean()
            
        peak_capital = capital
        max_drawdown = 0
        
        # Deterministic random seed so results don't bounce around on same params
        np.random.seed(42)

        for i in range(20, len(self.sorted_dates)):
            current_date = self.sorted_dates[i]
            
            # SELL logic
            symbols_to_sell = []
            for sym, pos in positions.items():
                if sym not in self.market_data or current_date not in self.market_data[sym].index: continue
                row = self.market_data[sym].loc[current_date]
                current_price = row['close']
                
                if current_price > pos['highest_price']:
                    pos['highest_price'] = current_price
                    
                stop_price = pos['highest_price'] - (atr_mult * row['atr'])
                
                if current_price < stop_price or current_price < row['ma20']:
                    capital += pos['shares'] * current_price
                    symbols_to_sell.append(sym)
                    
            for sym in symbols_to_sell:
                del positions[sym]
                
            # BUY logic
            if len(positions) < max_pos:
                for sym, df in self.market_data.items():
                    if sym in positions: continue
                    if current_date not in df.index: continue
                    
                    past_10 = df.loc[:current_date].tail(10)
                    if len(past_10) < 10: continue
                    
                    high_vol_days = len(past_10[past_10['volume'] > past_10['vol_ma20'] * vol_multiplier])
                    current_price = past_10.iloc[-1]['close']
                    price_10d_ago = past_10.iloc[0]['close']
                    price_change = (current_price - price_10d_ago) / price_10d_ago
                    
                    if high_vol_days >= acc_days and 0 < price_change < 0.15 and current_price > past_10.iloc[-1]['ma20']:
                        # Mock AI Decision
                        if np.random.random() < ai_approval_rate:
                            if len(positions) >= max_pos: break
                            
                            alloc = capital * (1.0 / max_pos)
                            shares = int(alloc / current_price)
                            if shares > 0:
                                capital -= shares * current_price
                                positions[sym] = {
                                    "entry_price": current_price,
                                    "highest_price": current_price,
                                    "shares": shares
                                }

            # Track portfolio
            port_val = capital
            for sym, pos in positions.items():
                if sym in self.market_data and current_date in self.market_data[sym].index:
                    port_val += pos['shares'] * self.market_data[sym].loc[current_date]['close']
                else:
                    port_val += pos['shares'] * pos['entry_price']
                    
            if port_val > peak_capital:
                peak_capital = port_val
            dd = (port_val - peak_capital) / peak_capital
            if dd < max_drawdown:
                max_drawdown = dd
                
        total_return = (port_val - self.initial_capital) / self.initial_capital
        years = 6.0
        ann_return = (1 + total_return) ** (1 / years) - 1
        
        return ann_return, max_drawdown

    def optimize(self):
        self.fetch_data()
        
        # Grid definition
        grid = {
            'vol_multiplier': [1.2, 1.5, 2.0],
            'acc_days': [2, 3],
            'atr_mult': [1.5, 2.0, 2.5],
            'max_pos': [1, 2, 3], # Lower max_pos = higher concentration = higher returns (if right)
            'ai_rate': [0.5, 0.8] # Represents AI accuracy (higher means AI captures more of the quant signals)
        }
        
        keys, values = zip(*grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        print(f"⚙️ Running {len(combinations)} iterations in Grid Search...")
        best_return = -1
        best_params = None
        best_dd = 0
        
        for idx, params in enumerate(combinations):
            ann_ret, dd = self.run_backtest(params)
            
            # Constraint: Drawdown must be strictly < 15%
            if dd > -0.15 and ann_ret > best_return:
                best_return = ann_ret
                best_params = params
                best_dd = dd
                print(f"  [New Best] Iter {idx}: Ann Ret = {ann_ret*100:.2f}%, DD = {dd*100:.2f}% | Params: {params}")
                
        print("\\n🏆 Optimization Complete.")
        if best_params:
            print(f"Optimal Parameters: {best_params}")
            print(f"Max Annualized Return (DD < 15%): {best_return*100:.2f}%")
            print(f"Max Drawdown: {best_dd*100:.2f}%")
        else:
            print("Could not find any parameters that kept drawdown < 15% with positive returns.")

if __name__ == "__main__":
    opt = V5Optimizer()
    opt.optimize()
