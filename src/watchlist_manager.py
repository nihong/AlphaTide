import json
import os
from datetime import datetime

class WatchlistManager:
    def __init__(self, filename="long_term_watchlist.json"):
        # 将文件存放在 data 目录下
        self.filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", filename)
        self._ensure_data_dir()
        self.watchlist = self.load_watchlist()

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)

    def load_watchlist(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 读取潜伏池失败: {e}")
                return []
        return []

    def save_watchlist(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.watchlist, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"⚠️ 保存潜伏池失败: {e}")

    def add_to_watchlist(self, symbol, name, industry, reasons):
        """
        添加通过基本面+宏观验证的标的进入潜伏池
        """
        # 检查是否已存在
        for item in self.watchlist:
            if item['symbol'] == symbol:
                # 更新理由和时间
                item['reasons'] = reasons
                item['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_watchlist()
                return False # 已存在，更新即可
                
        # 不存在，新增
        self.watchlist.append({
            'symbol': symbol,
            'name': name,
            'industry': industry,
            'reasons': reasons,
            'added_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        self.save_watchlist()
        return True # 新增成功
        
    def remove_from_watchlist(self, symbol):
        self.watchlist = [item for item in self.watchlist if item['symbol'] != symbol]
        self.save_watchlist()

    def get_watchlist(self):
        return self.watchlist
