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

    def extract_hot_industries_from_reports(self, valid_reports):
        """
        利用大模型对新提取的数十篇研报标题和机构进行深度提纯，找出真正的共识主线。
        """
        if not valid_reports:
            return {}
            
        # 将储备池个股拼接成文本
        reports_text = ""
        for i, r in enumerate(valid_reports[:30]): # 取前30篇防超长
            reports_text += f"{i+1}. 【{r['industry']}】{r['stock']} - {r['title']} (机构:{r['institution']}, 评级:{r['rating']})\n"
            
        prompt = f"""
你是一位顶级的宏观策略分析师。以下是我们使用“资金动态雷达”捕获到的当日全市场最活跃标的，并定向提取到的国内头部券商最新深度研报摘要：

{reports_text}

请你阅读这些研报摘要，找出当下券商“看多共识最强烈”的 Top 3 行业/题材。
对于每个找出的行业，请提炼：
1. 核心看多逻辑（为什么看多？是产量紧缺、政策利好还是业绩爆发？）
2. 宏观打假关键词（即：如果要验证这个行业的景气度，应该看什么宏观数据？比如航运看BDI指数，铜看COMEX期铜，消费看CPI，出海看出口同比，煤炭看动力煤价格等）。

必须以严格的 JSON 格式输出，格式如下（不要输出任何其他解释性文字，只输出JSON！）：
{{
    "recommended_sectors": [
        {{
            "name": "行业名称(如: 航运/工业金属/乘用车)",
            "reason": "看多核心逻辑概括(20字以内)",
            "macro_indicator": "用来验证真伪的宏观数据关键词"
        }}
    ]
}}
"""
        response = self.analyze_with_llm(prompt)
        
        # 解析 JSON
        import json
        import re
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                data = json.loads(json_str)
                sectors = data.get('recommended_sectors', [])
                
                # 转换成以名称为 key 的字典格式，方便 validator 直接吸收
                return {sec['name']: sec for sec in sectors}
            return {}
        except Exception as e:
            print(f"⚠️ 解析 AI 研报提纯输出失败: {response} | Error: {e}")
            return {}

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
当前系统的硬性ROE标准已放宽至10%。请你判断：如果该公司的ROE较低，是否是因为它正处于“困境反转”的早期阶段？其营收或利润增速是否足够高，足以覆盖短期ROE的不足？

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
