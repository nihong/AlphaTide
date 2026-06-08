import pandas as pd
import akshare as ak
import os
from src.data_fetcher import fetch_with_cache
from src.ai_analyst import AIAnalyst

class SentimentEngine:
    def __init__(self):
        self.analyst = AIAnalyst()

    def get_hot_sectors_with_news(self, top_n=10):
        """
        获取热门行业及其关联的核心新闻
        """
        print(f"🔍 正在抓取全市场热点舆情...")
        # 1. 获取实时热门行业 (Sina 接口最稳)
        try:
            df_sectors = fetch_with_cache("sina_spot_sentiment", ak.stock_sector_spot, expiry_hours=1)
            if df_sectors is None or df_sectors.empty: return []
            
            # 筛选涨幅 > 1% 且成交额大的前 Top N
            df_sectors['涨跌幅'] = pd.to_numeric(df_sectors['涨跌幅'], errors='coerce')
            df_sectors['总成交额'] = pd.to_numeric(df_sectors['总成交额'], errors='coerce')
            hot_sectors = df_sectors[df_sectors['涨跌幅'] > 1.0].sort_values(by='总成交额', ascending=False).head(top_n)
            
            results = []
            for _, sector in hot_sectors.iterrows():
                sector_name = sector['板块']
                # 获取该板块的领涨股或代表股新闻
                symbol = sector['股票代码'].replace('sh', '').replace('sz', '')
                stock_name = sector['股票名称']
                
                print(f"   - 正在提取 [{sector_name}] 的核心舆情...")
                news_df = fetch_with_cache(f"news_{symbol}", ak.stock_news_em, expiry_hours=1, symbol=symbol)
                
                headlines = []
                if news_df is not None and not news_df.empty:
                    headlines = news_df['新闻标题'].head(15).tolist()
                
                # 2. 调用 AI 进行舆情判读
                sentiment_score, ai_summary = self._analyze_sector_sentiment(sector_name, headlines)
                
                results.append({
                    'sector': sector_name,
                    'score': sentiment_score, # 0-100
                    'summary': ai_summary,
                    'representative_stock': stock_name
                })
            
            return results
        except Exception as e:
            print(f"舆情引擎运行错误: {e}")
            return []

    def _analyze_sector_sentiment(self, sector_name, headlines):
        """利用 DeepSeek 判读行业情绪"""
        if not headlines:
            return 50, "暂无近期核心新闻，维持中性评价。"
            
        news_str = "\n".join([f"- {h}" for h in headlines])
        prompt = f"""
你是一位资深的金融舆情分析师。请分析以下关于“{sector_name}”板块及相关个股的新闻标题，评估该板块当前的热度性质和参与价值。

新闻标题：
{news_str}

要求：
1. 给出一个 0-100 的情绪分（0: 极度利空/崩盘风险, 50: 中性, 100: 极度利好/主升浪爆发）。
2. 用一句话概括核心逻辑（为什么给这个分）。
3. 给出该板块的“参与建议”（如：短线博弈、持股待涨、观望避险）。

请严格按以下 JSON 格式输出：
{{"score": 85, "reason": "核心逻辑描述", "advice": "参与建议"}}
"""
        try:
            res_text = self.analyst.analyze_with_llm(prompt)
            # 简单解析 JSON (LLM 可能会带一些 Markdown 标记)
            import json
            import re
            json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('score', 50), f"{data.get('reason')} | 建议: {data.get('advice')}"
            return 50, "AI 解析失败"
        except:
            return 50, "AI 分析发生错误"

if __name__ == "__main__":
    engine = SentimentEngine()
    res = engine.get_hot_sectors_with_news(top_n=3)
    for r in res:
        print(f"\n板块: {r['sector']} (得分: {r['score']})")
        print(f"点评: {r['summary']}")
