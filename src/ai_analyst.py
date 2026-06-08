import os
import requests
import json
import re

class AIAnalyst:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"

    def analyze_with_llm(self, prompt):
        """调用 DeepSeek API 进行深度分析"""
        if not self.api_key:
            return "⚠️ 未配置 DEEPSEEK_API_KEY，请在环境变量中设置。报告将仅包含原始 Prompt。"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system", 
                    "content": "你是一位专业的量化投资分析师，专门针对'牛鞭效应'和'供应链瓶颈'生成战报。\n"
                               "【最高指令：反作弊机制 (ANTI-HALLUCINATION PROTOCOL)】\n"
                               "1. 绝对禁止捏造、凭空生成任何具体的现货价格、毛利率数据、或是大厂电话会的原句。\n"
                               "2. 如果上下文没有提供真实数据，必须输出 'DATA_UNAVAILABLE' 或 '无公开数据支撑'，绝不允许编造数字。\n"
                               "3. 绝对禁止生成虚拟的 URL 链接（如 mock-url）。所有引用的链接必须来源于系统传入的真实 Grounding 库。\n"
                               "4. 所有的结论必须具有可追溯的逻辑源头。"
                },
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }

        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"❌ API 调用失败: {response.text}"
        except Exception as e:
            return f"❌ AI 分析发生错误: {e}"

    def generate_v7_report_prompt(self, symbol, sector, raw_macro_data, raw_financial_data):
        """
        V7.1: 生成极早期牛鞭效应报告的 Prompt。
        严格限制 AI 只能根据传入的 raw_macro_data 和 raw_financial_data 写作，不得胡编乱造。
        """
        prompt = f"""
# AlphaTide V7.1 分析指令：{sector} - {symbol}

## 1. 系统传入的真实事实数据 (Hard Facts)
【宏观/现货数据】：
{raw_macro_data if raw_macro_data else "DATA_UNAVAILABLE (注意：缺乏真实宏观数据，禁止大模型自行编造)"}

【财务/动量数据】：
{raw_financial_data if raw_financial_data else "DATA_UNAVAILABLE (注意：缺乏真实财务数据，禁止大模型自行编造)"}

## 2. 撰写任务
请严格遵循上述提供的真实数据，为 {symbol} 撰写一份 V7.1 格式的《极早期前哨战报》。
报告必须包含以下板块：
一、 极早期前哨信号 (Early Radar Alerts) - 必须引用提供的真实事实数据，若无数据必须标明“缺乏数据印证”。
二、 第一基底解剖 (Stage 2 Base Anatomy) - 简述其爆发与洗盘逻辑。
三、 战略图谱 (SWOT 深度解析) - 梳理其在当前赛道的定价权与宏观威胁。
四、 狙击手交易卡片 (Execution Setup) - 写明右侧突破买入规则和 50 日线+ATR 止损纪律。

警告：再次强调，不要编造任何百分比、价格或链接！如果没有传入相应的真实链接，不要在报告末尾写“溯源链接”！
"""
        return prompt
