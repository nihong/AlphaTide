import os
import glob
import re

def update_master_summary():
    reports = glob.glob('reports/daily_decision_*.md')
    if not reports:
        return
    
    def extract_date(filepath):
        match = re.search(r'(\d{8})', filepath)
        return match.group(1) if match else "00000000"
        
    # 按日期降序排列，最新的在最上面
    reports.sort(key=extract_date, reverse=True)
    
    rows = []
    for filepath in reports:
        # Extract Market
        market = "A股" if "_A_" in filepath else "港股"
        
        # Extract Date
        date_match = re.search(r'(\d{8})', filepath)
        if not date_match: continue
        d_str = date_match.group(1)
        date_formatted = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 匹配红绿灯状态
        signal_match = re.search(r'当前红绿灯: (.*?)\n', content)
        if not signal_match:
            signal_match = re.search(r'当前大盘状态: \*\*(.*?)\*\*', content)
        market_signal = signal_match.group(1).strip() if signal_match else "未知"
        
        # 匹配推荐的个股
        matches = re.findall(r'### (.*?) \((\d{5,6})\)', content)
        if matches:
            stocks_str = "<br>".join([f"**{n}** ({s})" for n, s in matches])
        else:
            stocks_str = "无 (观望)"
            
        rows.append(f"| {date_formatted} | {market} | {market_signal} | {stocks_str} | [查看详情]({os.path.basename(filepath)}) |")
        
    master_content = "# 📊 AlphaTide 历史策略汇总看板\n\n"
    master_content += "本表格由系统在每次生成日报后 **自动更新**，记录了每一次 AI 哨兵扫描的核心决策结果，方便您追踪策略的历史表现与推荐标的。\n\n"
    master_content += "| 日期 | 市场 | 大盘红绿灯 | 精选标的 | 原始报告 |\n"
    master_content += "| :--- | :--- | :--- | :--- | :--- |\n"
    master_content += "\n".join(rows)
    
    # 写入文件
    summary_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports', 'master_summary.md')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(master_content)
