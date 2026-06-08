import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import re
import json
import pandas as pd
from datetime import datetime, timedelta
import akshare as ak

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# 定义我们想要测试的极端市场切片
slices = [
    # 1. 极端牛市切片（测试攻击力）
    {"name": "2021年1月极端牛市", "start": "2021-01-04", "end": "2021-01-15"},
    # 2. 极端熊市切片（测试防御力与对冲）
    {"name": "2022年10月极端熊市", "start": "2022-10-10", "end": "2022-10-21"},
    # 3. 结构性震荡切片（测试杠铃纠错）
    {"name": "2023年4月结构性震荡", "start": "2023-04-10", "end": "2023-04-21"}
]

# 1. 获取所有的交易日
trade_dates = ak.tool_trade_date_hist_sina()
trade_dates['trade_date'] = pd.to_datetime(trade_dates['trade_date']).dt.date
all_dates = trade_dates['trade_date'].tolist()

target_dates = []
for s in slices:
    start_date = datetime.strptime(s["start"], "%Y-%m-%d").date()
    end_date = datetime.strptime(s["end"], "%Y-%m-%d").date()
    y_dates = [d.strftime('%Y-%m-%d') for d in all_dates if start_date <= d <= end_date]
    target_dates.extend(y_dates)

print(f"开始执行【极端环境切片测试】，共选取 {len(target_dates)} 个交易日。")
print("注意：当前东方财富接口在黑名单期，系统会自动降级至新浪接口，速度可能稍慢，请耐心等待。")

# 2. 依次运行扫描
for d in target_dates:
    report_file = os.path.join(REPORTS_DIR, f"daily_decision_A_{d.replace('-', '')}.md")
    if os.path.exists(report_file):
        print(f"跳过 {d}，报告已存在。")
        continue
    print(f"正在扫描 {d} 的数据...")
    os.system(f"cd {PROJECT_ROOT} && python3 main.py --auto --fast --date {d}")

# 3. 解析所有的推荐股票
trades = []
for d in target_dates:
    report_file = os.path.join(REPORTS_DIR, f"daily_decision_A_{d.replace('-', '')}.md")
    if not os.path.exists(report_file): continue
    
    with open(report_file, 'r') as f:
        content = f.read()
    
    # 提取大盘红绿灯
    light = "未知"
    m_light = re.search(r"当前红绿灯.*?:\s*\*\*(.*?)\*\*", content)
    if not m_light: m_light = re.search(r"当前红绿灯.*?:\s*(.*?)\n", content)
    if m_light: light = m_light.group(1).strip()
    
    # 提取对冲提示
    hedge = "无对冲提示"
    if "熊市融券对冲建议" in content or "熊市反向对冲建议" in content:
        hedge = "⚠️已触发红灯对冲防守"

    # 提取推荐股票
    blocks = content.split("### ")
    for block in blocks[1:]:
        if "个股推荐" not in block: continue
        lines = block.split('\n')
        for line in lines:
            if line.startswith("- **"):
                m = re.search(r"\*\*(.*?)\s*\((\d+)\)\*\*", line)
                if m:
                    name = m.group(1)
                    symbol = m.group(2)
                    trades.append({
                        'date': d,
                        'light': light,
                        'hedge': hedge,
                        'symbol': symbol,
                        'name': name
                    })

# 4. 生成Markdown报告
summary_md = "# 🛡️ AlphaTide 极端环境切片测试报告 (Slice Testing)\n\n"
summary_md += "本报告针对过去 5 年最具代表性的 3 个极端市场环境进行切片测试，验证系统的攻击、防守与对冲逻辑是否按预期触发。\n\n"

for s in slices:
    summary_md += f"## {s['name']} ({s['start']} 到 {s['end']})\n"
    summary_md += "| 交易日期 | 大盘红绿灯 | 对冲状态 | 选股名单 (空仓为空) |\n"
    summary_md += "| :--- | :--- | :--- | :--- |\n"
    
    # 找到该切片内的所有日期
    start_date = datetime.strptime(s["start"], "%Y-%m-%d").date()
    end_date = datetime.strptime(s["end"], "%Y-%m-%d").date()
    slice_dates = [d.strftime('%Y-%m-%d') for d in all_dates if start_date <= d <= end_date]
    
    for d in slice_dates:
        # 找当天的记录
        day_trades = [t for t in trades if t['date'] == d]
        if not day_trades:
            # 去文件里找红绿灯
            report_file = os.path.join(REPORTS_DIR, f"daily_decision_A_{d.replace('-', '')}.md")
            light = "空仓"
            hedge = "无记录"
            if os.path.exists(report_file):
                with open(report_file, 'r') as f: c = f.read()
                m_light = re.search(r"当前红绿灯.*?:\s*\*\*(.*?)\*\*", c)
                if not m_light: m_light = re.search(r"当前红绿灯.*?:\s*(.*?)\n", c)
                if m_light: light = m_light.group(1).strip()
                if "熊市融券对冲建议" in c or "熊市反向对冲建议" in c:
                    hedge = "⚠️已触发红灯对冲防守"
            
            summary_md += f"| {d} | {light} | {hedge} | 🈳 **空仓避险** |\n"
        else:
            light = day_trades[0]['light']
            hedge = day_trades[0]['hedge']
            stocks = ", ".join([f"{t['name']}({t['symbol']})" for t in day_trades])
            summary_md += f"| {d} | {light} | {hedge} | {stocks} |\n"
    summary_md += "\n"

report_path = os.path.join(REPORTS_DIR, "backtest_slices_report.md")
with open(report_path, "w") as f:
    f.write(summary_md)

print(f"\n✅ 切片测试完成！分析报告已生成: {report_path}")
