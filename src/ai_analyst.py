import os
import json
import re
import asyncio

try:
    from google.antigravity import Agent, LocalAgentConfig
except ImportError:
    pass

import pydantic

class TargetStock(pydantic.BaseModel):
    symbol: str
    name: str
    reason: str

class TargetList(pydantic.BaseModel):
    targets: list[TargetStock]

class AIAnalyst:
    def __init__(self):
        pass

    def analyze_with_llm(self, prompt):
        """调用 AI 模型进行深度分析 (Antigravity SDK)"""
        return asyncio.run(self._async_analyze_with_llm(prompt))

    def map_sectors_to_symbols(self, sectors):
        """利用大模型将瓶颈行业直接映射到具体的 A 股核心标的"""
        return asyncio.run(self._async_map_sectors_to_symbols(sectors))

    async def _async_analyze_with_llm(self, prompt):
        system_instruction = (
            "你是一位专业的量化投资分析师，专门针对'牛鞭效应'和'供应链瓶颈'生成战报。\n"
            "【最高指令：反作弊机制 (ANTI-HALLUCINATION PROTOCOL)】\n"
            "1. 绝对禁止捏造、凭空生成任何具体的现货价格、毛利率数据、或是大厂电话会的原句。\n"
            "2. 如果上下文没有提供真实数据，必须输出 'DATA_UNAVAILABLE' 或 '无公开数据支撑'，绝不允许编造数字。\n"
            "3. 绝对禁止生成虚拟的 URL 链接（如 mock-url）。所有引用的链接必须来源于系统传入的真实 Grounding 库。\n"
            "4. 所有的结论必须具有可追溯的逻辑源头。"
        )
        
        config = LocalAgentConfig(
            system_instruction=system_instruction
        )
        try:
            async with Agent(config) as agent:
                response = await agent.chat(prompt)
                return await response.text()
        except Exception as e:
            return f"❌ AI 分析发生错误: {e}"

    async def _async_map_sectors_to_symbols(self, sectors):
        system_instruction = (
            "你是一位资深的A股行业研究员。你需要根据给定的目标赛道（如缺货涨价的细分行业），"
            "直接列出这些赛道在A股市场中最正宗、最核心的龙头上市公司的股票代码与名称。"
        )
        
        config = LocalAgentConfig(
            system_instruction=system_instruction,
            response_schema=TargetList
        )
        
        prompt = (
            f"目标赛道（牛鞭效应/供应链瓶颈）：{sectors}\n\n"
            f"请直接列出属于这些目标赛道的 A股核心上市公司代码（必须带有 sh/sz 前缀，如 sz300408 或 sh600519）。\n"
            f"不要遗漏处于早期的核心标的。每个赛道请列出大约 5-10 只最正宗的核心龙头股。\n"
            f"请简述选择该公司的核心理由（必须包含它的具体主营业务，以证明它与该赛道完全契合）。"
        )
        
        try:
            async with Agent(config) as agent:
                response = await agent.chat(prompt)
                data = await response.structured_output()
                if data:
                    return [item['symbol'] for item in data['targets']]
                return []
        except Exception as e:
            print(f"❌ AI 赛道映射发生错误: {e}")
            return []

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
