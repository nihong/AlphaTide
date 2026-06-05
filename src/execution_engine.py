import json
import os
import datetime
from capital_flow_voter import CapitalFlowVoter

class ExecutionEngine:
    def __init__(self):
        self.state_file = "data/portfolio_state.json"
        self.total_equity = 1000000.0 # 1 million RMB starting capital
        self.risk_per_trade = 0.01    # 1% risk of total equity per trade
        self.price_fetcher = CapitalFlowVoter()
        
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.state_file):
            with open(self.state_file, "w") as f:
                json.dump({"cash": self.total_equity, "positions": {}}, f)
                
    def load_state(self):
        with open(self.state_file, "r") as f:
            return json.load(f)
            
    def save_state(self, state):
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=4)
            
    def calculate_atr(self, symbol):
        # Mock ATR. Real system would calculate 14-day ATR from daily data.
        if symbol.startswith("300"): return 5.0
        elif symbol.startswith("51") or symbol.startswith("15"): return 0.5
        else: return 1.5

    def manage_existing_positions(self, state):
        positions = state["positions"]
        cash = state["cash"]
        symbols_to_remove = []
        
        for sym, data in positions.items():
            df = self.price_fetcher.fetch_stock_data_with_retry(sym, retries=2)
            if df.empty:
                print(f"  -> ⚠️ Could not fetch current price for {sym}. Skipping stop-loss check.")
                continue
                
            current_price = df.iloc[-1]['收盘']
            
            # Trailing Stop Logic: If current price - ATR*2 is higher than old stop_loss, raise the stop_loss
            atr = self.calculate_atr(sym)
            potential_new_stop = current_price - (atr * 2.0)
            if potential_new_stop > data["stop_loss"]:
                data["stop_loss"] = potential_new_stop
                print(f"  -> 🛡️ {sym} Trailing Stop raised to {potential_new_stop:.2f} (Current Price: {current_price:.2f})")
                
            # Sell Logic: If price drops below stop loss
            if current_price <= data["stop_loss"]:
                print(f"  -> 🚨 SELL TRIGGERED: {sym} hit stop loss! Executing liquidation.")
                sell_value = current_price * data["shares"]
                cash += sell_value
                symbols_to_remove.append(sym)
                print(f"     Sold {data['shares']} shares at {current_price:.2f}. Returned {sell_value:.2f} to cash.")
                
        for sym in symbols_to_remove:
            del positions[sym]
            
        state["cash"] = cash
        state["positions"] = positions
        return state

    def execute_trades(self, targets):
        print(f"\\n[Execution Engine] ⚔️ Commencing tactical sniper execution...")
        state = self.load_state()
        
        # 1. Manage existing positions (Trailing Stop & Sells)
        state = self.manage_existing_positions(state)
        cash = state["cash"]
        positions = state["positions"]
        
        # 2. Open new positions
        for target in targets:
            sym = target['symbol']
            theme = target['theme']
            
            if sym in positions:
                print(f"  -> ⏭️ Already holding {sym}. Skipping.")
                continue
                
            df = self.price_fetcher.fetch_stock_data_with_retry(sym, retries=2)
            if df.empty:
                print(f"  -> 🛑 Could not fetch price to buy {sym}. Skipping.")
                continue
                
            current_price = df.iloc[-1]['收盘']
            atr = self.calculate_atr(sym)
            stop_distance = atr * 2.0
            
            capital_at_risk = (cash + sum([p["shares"]*p["entry_price"] for p in positions.values()])) * self.risk_per_trade
            shares_to_buy = int(capital_at_risk / stop_distance)
            
            # Ensure we buy in lots of 100
            shares_to_buy = max(100, (shares_to_buy // 100) * 100)
            total_cost = shares_to_buy * current_price
            
            if cash >= total_cost:
                cash -= total_cost
                positions[sym] = {
                    "shares": shares_to_buy,
                    "entry_price": current_price,
                    "stop_loss": current_price - stop_distance,
                    "theme": theme,
                    "date_entered": datetime.datetime.now().strftime("%Y-%m-%d")
                }
                print(f"  -> 🎯 BUY ORDER EXECUTED: {sym} (Logic: {theme})")
                print(f"     Shares: {shares_to_buy} | Price: {current_price:.2f} | Stop Loss Set at: {current_price - stop_distance:.2f}")
            else:
                print(f"  -> 🛑 INSUFFICIENT FUNDS to buy {sym}. Cash: {cash:.2f}, Needed: {total_cost:.2f}")
                
        if not targets and not positions:
            print("[Execution Engine] ⚠️ No active targets. Holding 100% Cash.")
            
        state["cash"] = cash
        state["positions"] = positions
        self.save_state(state)
        print(f"\\n[Execution Engine] 🏦 Portfolio Status: Cash = {cash:.2f}, Active Positions = {len(positions)}")
            
if __name__ == "__main__":
    engine = ExecutionEngine()
    engine.execute_trades([])
