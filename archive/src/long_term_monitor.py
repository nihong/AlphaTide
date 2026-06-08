import sys
import os
import time
from datetime import datetime

# 确保能找到 src 目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.macro_cycle_engine import MacroCycleEngine
from src.screener import Screener
from src.ai_analyst import AIAnalyst
from src.watchlist_manager import WatchlistManager
from src.data_fetcher import fetch_a_stock_hist_cached, fetch_a_stock_financials

class LongTermMonitor:
    def __init__(self):
        self.macro_engine = MacroCycleEngine()
        self.screener = Screener()
        self.ai = AIAnalyst()
        self.watchlist = WatchlistManager()

    def run_diamond_scan(self):
        print("========== 💎 钻石手长线潜伏引擎启动 ==========")
        
        # 1. 提取研报一致预期最强烈的戴维斯双击候选池
        print("\n[第一步] 扫描全市场研报池，提取被最高频覆盖的个股...")
        macro_env = self.macro_engine.analyze_macro_environment()
        consensus_df = self.macro_engine.get_research_consensus_stocks(top_n=30)
        
        if consensus_df.empty:
            print("未找到强烈的机构预期上调标的。")
            return
            
        # 2. 调用 AI 大模型提取核心行业
        print("\n[第二步] 调用 AI (DeepSeek) 阅读研报摘要，提取 Top 3 共振行业...")
        top_industries = self.ai.extract_hot_industries_from_reports(consensus_df)
        if not top_industries:
            print("⚠️ AI 提取行业失败，跳过行业打假阶段，全盘扫描。")
            valid_industries = []
        else:
            print(f"🧠 AI 提取的核心推荐行业为: {', '.join(top_industries)}")
            
            # 3. 宏观物理打假
            print("\n[第三步] 调用宏观大宗/现货接口，对 AI 提取的行业进行物理交叉验证...")
            valid_industries = []
            for ind in top_industries:
                is_valid, reason = self.macro_engine.verify_industry_trend(ind)
                print(reason)
                if is_valid:
                    valid_industries.append(ind)
                    
            if not valid_industries:
                print("❌ 所有研报推荐行业均被物理数据证伪！放弃今日新增潜伏。")
            else:
                print(f"🛡️ 成功通过物理验证的行业：{', '.join(valid_industries)}")
        
        # 4. 财务困境反转/加速筛选，并存入本地潜伏池
        print("\n[第四步] 财报深度体检：寻找业绩加速与困境反转，注入本地潜伏沙盒...")
        added_count = 0
        for _, row in consensus_df.iterrows():
            symbol = str(row['代码']).zfill(6)
            name = row['名称']
            
            # 如果 AI 成功提取了行业，我们可以尝试匹配（这里为了容错，如果名字或基本面太好可以通融）
            # 但作为严格验证，我们这里可以筛选
            
            # 拉取财报
            fin_df = fetch_a_stock_financials(symbol)
            if fin_df is None or fin_df.empty:
                continue
                
            # 执行困境反转/业绩加速扫描
            passed, fin_reason = self.screener.screen_turnaround_fundamental(symbol, fin_df)
            if passed:
                is_new = self.watchlist.add_to_watchlist(symbol, name, "核心共振", fin_reason)
                if is_new:
                    print(f"⭐ [新增入库] {name}({symbol}) 存入沙盒！逻辑: {fin_reason}")
                    added_count += 1
                    
        if added_count == 0:
            print("今日无新增达标入库的标的。")
            
        # 5. 择时执行 (扫描本地潜伏池)
        print("\n[第五步] 巡逻本地潜伏沙盒，寻找【价值深坑+MACD企稳】的完美击球点...")
        pool = self.watchlist.get_watchlist()
        if not pool:
            print("📭 本地潜伏池为空，继续等待好公司的出现。")
            return
            
        print(f"📊 当前本地沙盒共有 {len(pool)} 只优质备选标的，开始技术面择时扫描...")
        selected_stocks = []
        for item in pool:
            symbol = item['symbol']
            try:
                # 触发 lurk_diamond 长线底背离模式
                passed, tech_reason = self.screener.screen_technical(symbol, mode='lurk_diamond')
                if passed:
                    hist = fetch_a_stock_hist_cached(symbol)
                    if hist is not None and not hist.empty:
                        latest_price = hist['收盘'].iloc[-1]
                        selected_stocks.append({
                            'symbol': symbol,
                            'name': item['name'],
                            'price': latest_price,
                            'fundamental': item['reasons'],
                            'technical': tech_reason
                        })
            except Exception as e:
                continue

        print("\n================ 扫描完成 ================")
        if selected_stocks:
            print("🎯 [开火指令] 沙盒中发现符合【钻石潜伏】买点的标的！")
            for s in selected_stocks:
                print(f"  - {s['name']} ({s['symbol']}) | 现价: {s['price']:.2f}")
                print(f"    🌟 基本面支撑: {s['fundamental']}")
                print(f"    📈 技术面买点: {s['technical']}")
            print("\n💡 [风控提醒] 请独立仓位建仓！防守底线：【宏观数据拐头】或【连续两季度净利润失速】。")
        else:
            print("💡 当前沙盒中的牛股大多在高位运行或未止跌。坚持原则，绝不追高！继续耐心潜伏。")

if __name__ == "__main__":
    monitor = LongTermMonitor()
    monitor.run_diamond_scan()
