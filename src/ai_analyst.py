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

## 1. 量化初筛状态
- 核心初筛：{status_str}
- 量化得分：{screening_result[1]}

## 2. 核心财务指标摘要
{financial_data.iloc[:15, :3].to_markdown() if hasattr(financial_data, 'to_markdown') else financial_data}

## 3. AI 深度研究任务 (首席分析师指令)
请扮演资深行业研究员，结合上述指标以及你的知识库，对该标的是否具备“10倍股”或“困境反转”潜力进行深度评估：

### A. 困境反转与利润爆发评估 (重点)
当前系统的硬性ROE标准已放宽至8%。请你判断：如果该公司的ROE较低，是否是因为它正处于“困境反转”的早期阶段？其营收或利润增速是否足够高，足以覆盖短期ROE的不足？

### B. 研发与资本开支 (R&D & CAPEX)
请分析该公司的技术护城河。其“研发投入占比”如何？同时观察其“在建工程”或“资本开支”。“合同负债”或“预收款”的高增长是否预示着未来订单的确定性爆发？

### C. 现金流与财务真实度
结合“经营现金流量净额”与“归母净利润”（净现比），判断其利润是否为实打实的真金白银。是否存在应收账款过高或财务粉饰风险？

### D. 最终投资建议
综合评估后，给出明确的“买入 / 观望 / 卖出”建议。
请列出 3 个核心驱动逻辑和 2 个致命风险点。
"""
        return prompt

    def summarize_findings(self, prompt):
        return prompt
