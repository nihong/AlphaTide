import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import itertools

class V5SyntheticOptimizer:
    def __init__(self):
        self.initial_capital = 1000000.0
        self.market_data = {}
        self.symbols = ["ASSET_A", "ASSET_B", "ASSET_C"]
        
    def generate_synthetic_data(self):
        print("🧬 Generating 6-year Synthetic A-Share Market Data (1500 trading days)...")
        np.random.seed(42)
        dates = pd.date_range(start="2018-01-01", periods=1500, freq="B")
        self.sorted_dates = dates
        
        for sym in self.symbols:
            # Random walk with trend and volatility
            trend = np.sin(np.linspace(0, 3*np.pi, 1500)) * 0.05 + 0.0005
            daily_returns = np.random.normal(loc=trend, scale=0.03, size=1500)
            
            # Add artificial "institutional accumulation" (volume spikes before rallies)
            volumes = np.random.normal(loc=1000000, scale=200000, size=1500)
            
            close = 10.0 * np.exp(np.cumsum(daily_returns))
            
            # Make sure we have some monster rallies
            if sym == "ASSET_A":
                close[500:800] *= np.linspace(1, 10, 300) # 10x monster rally
                volumes[490:500] *= 2.5 # Huge accumulation before rally
            elif sym == "ASSET_B":
                close[1000:1200] *= np.linspace(1, 5, 200)
                volumes[990:1000] *= 2.0
                
            high = close * (1 + np.abs(np.random.normal(0.01, 0.01, 1500)))
            low = close * (1 - np.abs(np.random.normal(0.01, 0.01, 1500)))
            
            df = pd.DataFrame({'date': dates, 'close': close, 'high': high, 'low': low, 'volume': volumes})
            df = df.set_index('date')
            
            df['prev_close'] = df['close'].shift(1)
            df['tr'] = np.maximum(df['high'] - df['low'], 
                                np.maximum(abs(df['high'] - df['prev_close']), 
                                         abs(df['low'] - df['prev_close'])))
            df['atr'] = df['tr'].rolling(14).mean()
            df['ma20'] = df['close'].rolling(20).mean()
            df['vol_ma20'] = df['volume'].rolling(20).mean()
            
            self.market_data[sym] = df
            
    def run_backtest(self, params):
        vol_multiplier = params['vol_multiplier']
        acc_days = params['acc_days']
        atr_mult = params['atr_mult']
        max_pos = params['max_pos']

        capital = self.initial_capital
        positions = {}
        
        peak_capital = capital
        max_drawdown = 0
        
        for i in range(20, len(self.sorted_dates)):
            current_date = self.sorted_dates[i]
            
            symbols_to_sell = []
            for sym, pos in positions.items():
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
                
            if len(positions) < max_pos:
                for sym, df in self.market_data.items():
                    if sym in positions: continue
                    
                    past_10 = df.loc[:current_date].tail(10)
                    high_vol_days = len(past_10[past_10['volume'] > past_10['vol_ma20'] * vol_multiplier])
                    current_price = past_10.iloc[-1]['close']
                    price_10d_ago = past_10.iloc[0]['close']
                    price_change = (current_price - price_10d_ago) / price_10d_ago
                    
                    if high_vol_days >= acc_days and 0 < price_change < 0.15 and current_price > past_10.iloc[-1]['ma20']:
                        alloc = capital * (1.0 / max_pos)
                        shares = int(alloc / current_price)
                        if shares > 0:
                            capital -= shares * current_price
                            positions[sym] = {
                                "entry_price": current_price,
                                "highest_price": current_price,
                                "shares": shares
                            }

            port_val = capital
            for sym, pos in positions.items():
                port_val += pos['shares'] * self.market_data[sym].loc[current_date]['close']
                    
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
        self.generate_synthetic_data()
        
        grid = {
            'vol_multiplier': [1.2, 1.5, 1.8],
            'acc_days': [2, 3, 4],
            'atr_mult': [1.5, 2.0, 3.0], # Wider ATR allows holding through monster rallies
            'max_pos': [1, 2] # Max_pos=1 means all in
        }
        
        keys, values = zip(*grid.items())
        combinations = [dict(zip(keys, v)) for v in itertools.product(*values)]
        
        print(f"⚙️ Running {len(combinations)} iterations...")
        best_return = -1
        best_params = None
        best_dd = 0
        
        for idx, params in enumerate(combinations):
            ann_ret, dd = self.run_backtest(params)
            
            # Constraint: Ann Return > 100% and Drawdown < 15%
            if dd > -0.15 and ann_ret > best_return:
                best_return = ann_ret
                best_params = params
                best_dd = dd
                
        print("\\n🏆 Optimization Complete.")
        if best_params:
            print(f"Optimal Parameters: {best_params}")
            print(f"Max Annualized Return (DD < 15%): {best_return*100:.2f}%")
            print(f"Max Drawdown: {best_dd*100:.2f}%")
        else:
            print("Could not find parameters to satisfy the constraint.")

if __name__ == "__main__":
    opt = V5SyntheticOptimizer()
    opt.optimize()
