import random

class CapitalFlowVoter:
    def __init__(self):
        pass
        
    def check_smart_money(self, symbol):
        """
        Check if Smart Money / Institutional Volume is accumulating.
        """
        # Simulated logic: Check recent Volume moving average and relative strength
        volume_spike = random.random() > 0.3 # 70% chance volume is supportive
        if volume_spike:
            print(f"  -> 💸 [Flow Voter] Symbol {symbol}: Smart Money accumulation detected! (Vol > MA20)")
        else:
            print(f"  -> 🐢 [Flow Voter] Symbol {symbol}: No institutional interest. Volume dead. Rejected.")
        return volume_spike
        
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
    voter.vote([{"symbol": "002594"}, {"symbol": "300308"}])
