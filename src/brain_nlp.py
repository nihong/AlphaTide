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
                
        # Load DeepSeek API Key from .env manually to avoid extra dependencies
        self.api_key = None
        if os.path.exists(".env"):
            with open(".env", "r") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY"):
                        self.api_key = line.strip().split("=")[1].strip(" '\"")

    def fetch_latest_news(self):
        """Fetch real financial news summary from Akshare (e.g. CCTV news or Sina)"""
        print("[Brain NLP] 📡 Fetching real macro and industry news via Akshare...")
        try:
            # CCTV Xinwen Lianbo text summary is a great macro indicator in China
            df = ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))
            if not df.empty:
                news_text = "\\n".join(df['content'].head(10).tolist())
                return news_text
        except Exception as e:
            print(f"Failed to fetch CCTV news: {e}")
            
        return "Macro environment remains stable. Tech sector (Semiconductors) and Export/Shipping show strong resilience. Gold prices are fluctuating."

    def call_llm(self, news_text):
        if not self.api_key:
            print("[Brain NLP] ⚠️ DEEPSEEK_API_KEY not found in .env. Falling back to rule-based logic.")
            return self.fallback_logic()

        print("[Brain NLP] 🧠 Connecting to DeepSeek API for NLP analysis...")
        
        # Memory retrieval
        memory_file = "data/brain_memory.json"
        historical_context = "No previous history."
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r") as f:
                    mem_data = json.load(f)
                    historical_context = f"Yesterday you extracted: {json.dumps(mem_data[-1]['themes'])}. Consider if these themes are fading or strengthening."
            except:
                pass

        prompt = f"""
        You are a top-tier Quantitative Financial Analyst. 
        Read the following macro news and extract 3 high-conviction investment themes.
        For each theme, provide ONE representative Chinese A-share or ETF ticker symbol (e.g. '513100' or '600519').
        Return ONLY valid JSON in this exact format:
        [
            {{"symbol": "513100", "theme": "Semiconductor", "logic_score": 90}},
            ...
        ]
        
        {historical_context}
        
        News Text:
        {news_text}
        """
        
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            data = json.dumps({
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }).encode('utf-8')
            
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                # Clean markdown JSON formatting if present
                content = content.replace("```json", "").replace("```", "").strip()
                parsed_json = json.loads(content)
                
                # Save memory
                try:
                    mem_list = []
                    if os.path.exists(memory_file):
                        with open(memory_file, "r") as f:
                            mem_list = json.load(f)
                    mem_list.append({"date": datetime.now().strftime("%Y-%m-%d"), "themes": [x['theme'] for x in parsed_json]})
                    with open(memory_file, "w") as f:
                        json.dump(mem_list[-5:], f) # Keep last 5 days
                except Exception as e:
                    print(f"Memory save error: {e}")
                    
                return parsed_json
        except Exception as e:
            print(f"[Brain NLP] ❌ LLM API Call Failed: {e}")
            return self.fallback_logic()

    def fallback_logic(self):
        """Fallback if API fails or no key. We read from manual watchlist populated by the Assistant."""
        print("[Brain NLP] 🧑‍💻 Using manual Assistant-populated watchlist...")
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, "r") as f:
                    data = json.load(f)
                    return data.get("stocks", [])
            except:
                return []
        return []
        
    def validate_symbols(self, ideas):
        """Cross-check LLM symbols against real A-share/ETF codes"""
        print("[Brain NLP] 🔍 Validating LLM symbols against real market database...")
        try:
            # We fetch real codes. Using a simple approach here.
            # In a full system, you might cache this to disk.
            valid_df = ak.stock_info_a_code_name()
            valid_codes = set(valid_df['code'].tolist())
            
            # ETFs also exist, typically starting with 51 or 15
            
            validated_ideas = []
            for idea in ideas:
                sym = idea['symbol']
                name = valid_df[valid_df['code'] == sym]['name'].values
                is_st = False
                if len(name) > 0 and 'ST' in name[0].upper():
                    is_st = True
                
                # Check if it's a valid stock or looks like a valid ETF
                if sym in valid_codes or sym.startswith("51") or sym.startswith("15"):
                    if not is_st:
                        validated_ideas.append(idea)
                    else:
                        print(f"  -> 🗑️ Dropped {sym}: ST/Delisting risk detected.")
                else:
                    print(f"  -> 🗑️ Dropped {sym}: Hallucinated or invalid symbol.")
            return validated_ideas
        except Exception as e:
            print(f"[Brain NLP] ⚠️ Validation API failed: {e}. Passing symbols blindly.")
            return ideas

    def update_watchlist(self):
        news = self.fetch_latest_news()
        raw_ideas = self.call_llm(news)
        
        # 1. New Feature: Symbol Validation
        ideas = self.validate_symbols(raw_ideas)
        
        data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stocks": ideas
        }
        with open(self.watchlist_file, "w") as f:
            json.dump(data, f, indent=4)
        print(f"[Brain NLP] ✅ Watchlist updated with {len(ideas)} validated LLM-extracted targets.")
        return ideas

if __name__ == "__main__":
    brain = NLPBrain()
    brain.update_watchlist()
