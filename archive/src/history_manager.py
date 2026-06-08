import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, storage_path="history/data.json"):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, 'w') as f:
                json.dump({}, f)

    def record_daily_stats(self, stats):
        """
        Record sector scores for the day.
        stats: { "SectorName": score, ... }
        """
        today = datetime.now().strftime("%Y-%m-%d")
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
        
        data[today] = stats
        
        with open(self.storage_path, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_acceleration(self, sector_name):
        """
        Calculate if a sector's score is increasing over the last 3 days.
        """
        with open(self.storage_path, 'r') as f:
            data = json.load(f)
        
        # Sort dates
        dates = sorted(data.keys(), reverse=True)
        if len(dates) < 2:
            return 0
        
        scores = []
        for d in dates[:3]:
            scores.append(data[d].get(sector_name, 0))
        
        if len(scores) < 2: return 0
        
        # Simple acceleration: current - average of previous
        return scores[0] - (sum(scores[1:]) / len(scores[1:]))
