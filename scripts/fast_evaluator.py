import os
import glob
import re
import pandas as pd
from scripts.evaluate_strategy import StrategyEvaluator

def parse_reports_and_evaluate():
    evaluator = StrategyEvaluator()
    results = {"A": [], "HK": []}
    
    # 查找所有的 daily_decision 报告
    report_files = glob.glob("reports/daily_decision_*.md")
    
    for filepath in report_files:
        filename = os.path.basename(filepath)
        # 忽略非回测生成的旧报告，例如每天自动生成的当前日期报告，只匹配我们有指定日期的
        match = re.search(r'daily_decision_(A|HK)_(\d{8})\.md', filename)
        if not match:
            continue
            
        market = match.group(1)
        date_str = match.group(2)
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取推荐标的: ### 股票名称 (Symbol)
        # 例如: ### 腾讯控股 (00700) 或 ### 贵州茅台 (600519)
        symbols = re.findall(r'###\s+.*?\s+\((\d+)\)', content)
        
        for symbol in symbols:
            # 获取5日和10日收益率
            ret_5d = evaluator.get_forward_return(symbol, date_formatted, days=5, market=market)
            results[market].append({
                'date': date_formatted,
                'symbol': symbol,
                'ret_5d': ret_5d
            })

    for market in ["A", "HK"]:
        signals = results[market]
        if not signals:
            print(f"\n{market} 市场目前无推荐信号。")
            continue
            
        df = pd.DataFrame(signals)
        win_rate = len(df[df['ret_5d'] > 0]) / len(df)
        avg_ret = df['ret_5d'].mean()
        max_ret = df['ret_5d'].max()
        min_ret = df['ret_5d'].min()
        
        print(f"\n" + "="*30)
        print(f"📊 {market} 股市场近期策略表现 (基于已生成的报告)")
        print("="*30)
        print(f"触发信号总数: {len(df)}")
        print(f"5日胜率: {round(win_rate*100, 2)}%")
        print(f"5日平均收益: {round(avg_ret*100, 2)}%")
        print(f"单笔最大收益: {round(max_ret*100, 2)}%")
        print(f"最差表现(回撤): {round(min_ret*100, 2)}%")

if __name__ == "__main__":
    parse_reports_and_evaluate()
