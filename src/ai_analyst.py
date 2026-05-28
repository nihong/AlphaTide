import os
import requests

class AIAnalyst:
    def __init__(self):
        # 从环境变量获取 API KEY
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
                {"role": "system", "content": "你是一位专业的量化投资分析师，擅长结合财务与技术面给出实战建议。"},
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

    def generate_report_prompt(self, symbol, market, financial_data, screening_result):
        """
        创建一个让大模型进行深度分析的 Prompt。
        """
        status_str = "【通过】" if screening_result[0] else "【未通过】"
        prompt = f"""
# 投资价值深度分析报告：{symbol} ({market})

## 1. 量化筛选状态
- 核心初筛：{status_str}
- 详细详情：{screening_result[1]}

## 2. 核心财务指标摘要
{financial_data.iloc[:15, :3].to_markdown()}

## 3. AI 深度研究任务 (分析师指令)
请扮演资深行业研究员，基于上述数据对该标的是否具备“10倍股”潜力进行深度评估：

### A. 研发与创新能力 (R&D)
请搜索并分析该公司近三年的**研发投入占比**。其技术是否具有护城河？是否处于行业领先地位？

### B. 产能与扩张 (CAPEX)
分析其**资本开支**情况。公司是否在扩建产能？“合同负债”或“预收款”的变动是否预示着未来订单的爆发？

### C. 现金流质量
结合“净现比”，判断其利润是否为实打实的真金白银，是否存在财务粉饰风险。

### D. 最终建议
给出“买入/持有/卖出”建议，并列出 3 个核心理由和 2 个关键风险点。
"""
        return prompt

    def summarize_findings(self, prompt):
        return prompt
