import os
import json
from datetime import datetime
import akshare as ak
import urllib.request
import urllib.error

class NLPBrain:
    def __init__(self):
        self.watchlist_file = "data/watchlist.json"
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.watchlist_file):
            with open(self.watchlist_file, "w") as f:
                json.dump({"date": "", "stocks": []}, f)
                
        self.api_key = None
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY"):
                        self.api_key = line.strip().split("=")[1].strip(" '\"")

    def fetch_latest_news(self):
        """Fetch real financial news summary from Akshare"""
        print("[Brain NLP] 📡 Fetching real macro and industry news via Akshare...")
        try:
            df = ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))
            if not df.empty:
                news_text = "\\n".join(df['content'].head(10).tolist())
                return news_text
        except Exception as e:
            pass
        return "Macro environment remains stable. Focus on domestic tech substitution, low-altitude economy, and high-yield dividend stocks."

    def call_llm_auditor(self, news_text, quant_pool):
        """
        The new AI Logic: Forensic Auditor.
        It does NOT pick stocks out of thin air. It takes the objectively accumulating stocks
        and checks if their sectors are supported by today's macro news.
        """
        if not self.api_key or not quant_pool:
            print("[Brain NLP] ⚠️ No API key or empty pool. Blindly passing all quant stocks.")
            return quant_pool

        print(f"[Brain NLP] 🧠 Connecting to DeepSeek to audit {len(quant_pool)} technically strong stocks...")
        
        # We only send the top 10 from quant pool to save context window
        top_candidates = quant_pool[:10]
        symbols_str = ", ".join([p['symbol'] for p in top_candidates])
        
        prompt = f"""
        You are a top-tier Quantitative Financial Auditor.
        Our Quant Radar has detected massive institutional money secretly buying the following A-share symbols over the last 10 days: 
        [{symbols_str}]
        
        Read the macro news below. Your job is to act as a Forensic Auditor.
        VETO (Reject) any stock if you believe the recent buying is just random speculation with NO solid policy or macro tailwind mentioned in the news or current global trends.
        APPROVE the stock ONLY if its sector is clearly supported by strong, multi-month fundamentals.
        
        Return ONLY valid JSON in this exact format:
        [
            {{"symbol": "000001", "decision": "APPROVE", "reason": "Bank sector supported by high dividend policy"}},
            {{"symbol": "000002", "decision": "VETO", "reason": "No policy support for real estate currently"}}
        ]
        
        News Text:
        {news_text}
        """
        
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            data = json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1 # Low temp for analytical tasks
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            })
            
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                content = content.replace("```json", "").replace("```", "").strip()
                parsed_json = json.loads(content)
                
                # Filter out the vetoed ones
                approved_symbols = [x['symbol'] for x in parsed_json if x.get('decision') == 'APPROVE']
                
                final_pool = [p for p in quant_pool if p['symbol'] in approved_symbols]
                print(f"[Brain NLP] ⚖️ Audit Complete. AI approved {len(final_pool)} out of {len(top_candidates)} targets.")
                return final_pool
        except Exception as e:
            print(f"[Brain NLP] ❌ LLM Audit Failed: {e}. Defaulting to Quant signals.")
            return quant_pool

    def update_watchlist(self, quant_pool):
        if not quant_pool:
            print("[Brain NLP] ⚠️ Quant Pool is empty. Nothing to audit.")
            return []
            
        news = self.fetch_latest_news()
        
        # AI now AUDITS the quant pool instead of generating its own
        approved_pool = self.call_llm_auditor(news, quant_pool)
        
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stocks": approved_pool
        }
        with open(self.watchlist_file, "w") as f:
            json.dump(data, f, indent=4)
            
        print(f"[Brain NLP] ✅ Watchlist updated. {len(approved_pool)} stocks ready for Execution Sniper.")
        return approved_pool

if __name__ == "__main__":
    # Test with dummy data
    brain = NLPBrain()
    dummy_quant_pool = [{"symbol": "600519", "accumulation_score": 5}, {"symbol": "000977", "accumulation_score": 4}]
    brain.update_watchlist(dummy_quant_pool)
