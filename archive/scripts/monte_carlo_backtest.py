import akshare as ak
import pandas as pd
import numpy as np
import random
import time

class MonteCarloBacktest:
    def __init__(self):
        self.initial_capital = 1000000.0
        self.cash = self.initial_capital
        self.positions = {}
        self.equity_curve = []
        self.risk_per_trade = 0.01
        self.historical_data = {}
        self.trading_days = []
        
    def fetch_data(self, start_date="20230101", end_date="20240101"):
        print("[Engine] 📥 Generating Monkey Brain Universe...")
        # Get all stocks
        try:
            df_info = ak.stock_info_a_code_name()
            valid_codes = [c for c, n in zip(df_info['code'], df_info['name']) if 'ST' not in n and '退' not in n]
            
            # Pick 20 random stocks for speed
            universe = random.sample(valid_codes, 20)
            
            all_dates = set()
            print(f"[Engine] ⏳ Fetching history for 20 random stocks. Please wait...")
            
            for code in universe:
                # Add market prefix
                if code.startswith("6"): prefix = "sh" + code
                elif code.startswith("0") or code.startswith("3"): prefix = "sz" + code
                else: continue
                
                try:
                    df = ak.stock_zh_a_daily(symbol=prefix, start_date=start_date, end_date=end_date, adjust="qfq")
                    if not df.empty and len(df) > 50:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.set_index('date')
                        # Calculate indicators
                        df['ma20'] = df['close'].rolling(20).mean()
                        df['vol_ma20'] = df['volume'].rolling(20).mean()
                        # Simplified ATR
                        df['atr'] = (df['high'] - df['low']).rolling(14).mean()
                        df['atr'] = df['atr'].fillna(df['close'] * 0.02) # Fallback ATR
                        
                        self.historical_data[code] = df
                        all_dates.update(df.index.tolist())
                    time.sleep(0.5) # Avoid rate limit
                except Exception as e:
                    pass
                    
            self.trading_days = sorted(list(all_dates))
            print(f"[Engine] ✅ Fetched {len(self.historical_data)} valid stocks across {len(self.trading_days)} trading days.")
        except Exception as e:
            print(f"Data fetch failed: {e}")
            
    def run(self):
        if not self.trading_days:
            return
            
        print("[Engine] 🚀 Starting Monte Carlo Backtest (Monkey Brain vs V4 Filters)...")
        
        for current_day in self.trading_days:
            # 1. Manage Existing Positions
            symbols_to_remove = []
            for sym, pos in self.positions.items():
                df = self.historical_data[sym]
                if current_day not in df.index:
                    continue
                    
                today_data = df.loc[current_day]
                current_price = today_data['close']
                
                # Trailing Stop Update
                potential_new_stop = current_price - (pos['atr'] * 2.0)
                if potential_new_stop > pos['stop_loss']:
                    pos['stop_loss'] = potential_new_stop
                    
                # Sell Logic
                if current_price <= pos['stop_loss']:
                    # Limit-down check: close == low, and low < open
                    if current_price == today_data['low'] and today_data['low'] < today_data['open']:
                        pass # Trapped
                    else:
                        sell_val = current_price * pos['shares']
                        self.cash += sell_val
                        symbols_to_remove.append(sym)
                        
            for sym in symbols_to_remove:
                del self.positions[sym]
                
            # 2. Monkey Brain Random Generation
            available_symbols = list(self.historical_data.keys())
            if len(available_symbols) < 3: continue
            monkey_picks = random.sample(available_symbols, 3)
            
            # 3. V4 Filters (Smart Money & Trend)
            for sym in monkey_picks:
                if sym in self.positions: continue
                df = self.historical_data[sym]
                if current_day not in df.index: continue
                
                today_data = df.loc[current_day]
                
                # Filter Logic
                vol_breakout = today_data['volume'] > (today_data['vol_ma20'] * 1.5)
                price_uptrend = today_data['close'] > today_data['ma20']
                limit_up = (today_data['close'] == today_data['high']) and (today_data['high'] > today_data['open'])
                
                if vol_breakout and price_uptrend and not limit_up:
                    # Buy Logic
                    atr = today_data['atr']
                    if pd.isna(atr) or atr <= 0: atr = today_data['close'] * 0.02
                    stop_distance = atr * 2.0
                    
                    total_equity = self.cash + sum([p['shares'] * self.historical_data[s].loc[current_day]['close'] for s, p in self.positions.items() if current_day in self.historical_data[s].index])
                    
                    capital_at_risk = total_equity * self.risk_per_trade
                    shares_to_buy = int(capital_at_risk / stop_distance)
                    shares_to_buy = max(100, (shares_to_buy // 100) * 100)
                    
                    total_cost = shares_to_buy * today_data['close']
                    if self.cash >= total_cost:
                        self.cash -= total_cost
                        self.positions[sym] = {
                            "shares": shares_to_buy,
                            "entry_price": today_data['close'],
                            "stop_loss": today_data['close'] - stop_distance,
                            "atr": atr
                        }
                        
            # Record Equity
            daily_equity = self.cash
            for sym, pos in self.positions.items():
                if current_day in self.historical_data[sym].index:
                    daily_equity += pos['shares'] * self.historical_data[sym].loc[current_day]['close']
            self.equity_curve.append({"date": current_day, "equity": daily_equity})
            
        self.generate_report()
        
    def generate_report(self):
        if not self.equity_curve: return
        
        df_eq = pd.DataFrame(self.equity_curve)
        df_eq.set_index('date', inplace=True)
        
        df_eq['peak'] = df_eq['equity'].cummax()
        df_eq['drawdown'] = (df_eq['peak'] - df_eq['equity']) / df_eq['peak']
        
        max_dd = df_eq['drawdown'].max()
        final_equity = df_eq['equity'].iloc[-1]
        total_return = (final_equity - self.initial_capital) / self.initial_capital
        
        print("\\n" + "="*50)
        print("📊 MONTE CARLO STRESS TEST REPORT")
        print("="*50)
        print(f"Total Trading Days: {len(self.trading_days)}")
        print(f"Initial Capital: {self.initial_capital:,.2f}")
        print(f"Final Equity: {final_equity:,.2f}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Max Drawdown: {max_dd:.2%} 🛡️")
        print("="*50)
        if max_dd < 0.15:
            print("✅ TEST PASSED: System armor held strong. Max Drawdown < 15%.")
        else:
            print("❌ TEST FAILED: Drawdown exceeded limits.")

if __name__ == "__main__":
    tester = MonteCarloBacktest()
    tester.fetch_data(start_date="20230101", end_date="20240101")
    tester.run()
