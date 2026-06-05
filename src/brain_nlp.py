import os
import json
import random
from datetime import datetime

class NLPBrain:
    def __init__(self):
        self.watchlist_file = "data/watchlist.json"
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.watchlist_file):
            with open(self.watchlist_file, "w") as f:
                json.dump({"date": "", "stocks": []}, f)
                
    def read_reports(self):
        """
        Simulate scraping EastMoney / Sina Finance for brokerage reports.
        In a real scenario, this calls DeepSeek API to extract tickers and narratives.
        """
        print("[Brain NLP] 🧠 Scraping daily brokerage reports and policy news...")
        # Simulated LLM output
        ideas = [
            {"symbol": "600519", "theme": "Consumer Recovery", "logic_score": 85},
            {"symbol": "002594", "theme": "EV Export Boom", "logic_score": 92},
            {"symbol": "300308", "theme": "AI Optoelectronics", "logic_score": 95},
            {"symbol": "518880", "theme": "Geopolitical Hedge", "logic_score": 88},
            {"symbol": "513100", "theme": "US Tech Earnings", "logic_score": 90}
        ]
        
        # Add some random noise to simulate dynamic daily generation
        selected = random.sample(ideas, k=random.randint(3, 5))
        print(f"[Brain NLP] 🎯 LLM Extracted {len(selected)} Core Logic Targets.")
        return selected
        
    def update_watchlist(self):
        ideas = self.read_reports()
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stocks": ideas
        }
        with open(self.watchlist_file, "w") as f:
            json.dump(data, f, indent=4)
        print("[Brain NLP] ✅ Watchlist updated successfully.")
        return ideas

if __name__ == "__main__":
    brain = NLPBrain()
    brain.update_watchlist()
