import os
import sys
from datetime import datetime
import time
from src.data_fetcher import fetch_market_tide, fetch_a_stock_financials, fetch_market_index
from src.rotation_predictor import RotationPredictor
from src.screener import Screener
from src.history_manager import HistoryManager
from src.ai_analyst import AIAnalyst

from src.risk_manager import RiskManager

class MarketMonitor:
    def __init__(self):
        self.predictor = RotationPredictor()
        self.screener = Screener()
        self.history = HistoryManager()
        self.analyst = AIAnalyst()
        self.risk = RiskManager()

    def check_market_light(self):
        """红绿灯系统：根据沪深300指数的量价关系判断市场环境并输出仓位建议"""
        # 使用沪深300 sh000300
        df = fetch_market_index("sh000300")
        if df is None or df.empty: return "YELLOW", "数据获取失败，默认建议仓位: 30%"
        
        latest_price = df.iloc[-1]['close']
        ma20 = df.iloc[-20:]['close'].mean()
        
        latest_vol = df.iloc[-1]['volume']
        vol_ma5 = df.iloc[-5:]['volume'].mean()
        
        # 逻辑判断
        is_uptrend = latest_price > ma20
        is_expanding_vol = latest_vol > vol_ma5
        
        if is_uptrend:
            if is_expanding_vol:
                return "GREEN", f"🟢 多头环境且放量 (价格>MA20, 量>5日均量)，建议重仓 (仓位: 80%)"
            else:
                return "YELLOW", f"🟡 多头环境但缩量 (动能不足)，建议观望或轻仓 (仓位: 30%)"
        else:
            if is_expanding_vol:
                return "RED", f"🔴 空头环境且放量下跌 (价格<MA20, 量>5日均量)，风险极大，建议空仓避险 (仓位: 0%)"
            else:
                return "YELLOW", f"🟡 空头环境但缩量下跌 (存在止跌惜售迹象)，建议观望 (仓位: 30%)"

    def run_daily_scan(self):
        print(f"[{datetime.now()}] 🚀 启动每日自动哨兵监控...")
        
        # 0. 环境检查
        if not os.path.exists(".env"):
            print("⚠️ 警告: 根目录未发现 .env 文件，AI 点评功能将无法完整运行。请参考 .env.example 配置。")

        # 0. 大盘红绿灯
        light, light_msg = self.check_market_light()
        print(f"🚦 大盘红绿灯: {light} - {light_msg}")
        
        if light == "RED":
            self._generate_final_report([], light, light_msg, [])
            print("🛑 市场风险较大，已生成风险预警报告，停止进一步扫描。")
            return

        # 1. 识别蓄势板块
        potentials = self.predictor.predict_accumulation_sectors()
        if potentials is None or potentials.empty:
            print("⚠️ 未发现明显的蓄势板块，今天建议观望。")
            self._generate_final_report([], light, light_msg, [])
            return
        
        # 记录历史
        stats = {row['名称']: row['蓄势指数'] for _, row in potentials.iterrows() if '名称' in potentials.columns}
        self.history.record_daily_stats(stats)
        
        top_sectors = potentials.head(3)
        print(f"🔥 锁定今日 3 大蓄势行业: {list(top_sectors['名称'] if '名称' in top_sectors.columns else top_sectors['板块'])}")

        recommendations = []
        sell_warnings = []

        # 2. 在每个行业内精选个股
        for _, sector in top_sectors.iterrows():
            sector_name = sector['名称'] if '名称' in sector.index else sector['板块']
            print(f"\n🔍 正在扫描行业: {sector_name} ...")
            
            stocks = self.screener.get_stocks_in_sector(sector_name)
            if stocks is None or stocks.empty: continue
            
            for _, stock in stocks.head(10).iterrows():
                symbol = stock['代码']
                name = stock['名称']
                
                # A. 卖出信号检查 (针对持仓或关注列表)
                exit_signals, exit_desc = self.risk.evaluate_exit_signals(symbol)
                if exit_signals:
                    sell_warnings.append({"name": name, "symbol": symbol, "desc": exit_desc})

                # B. 买入机会筛选 (三维过滤)
                # 1. 相对强度检查 (RS)
                rs_score = self.risk.get_rs_rating(symbol)
                if rs_score < 0: continue # 走得比大盘还弱的，不要
                
                # 2. 财务体检
                financials = fetch_a_stock_financials(symbol)
                f_pass, f_detail = self.screener.screen_a_share(financials)
                
                if f_pass:
                    # 3. 技术面体检
                    t_pass, t_detail = self.screener.screen_technical(symbol)
                    if t_pass:
                        print(f"✨ 发现优质标的: {name} ({symbol}) | RS强度: {round(rs_score, 2)}")
                        
                        # D. 获取 AI 深度分析
                        prompt = self.analyst.generate_report_prompt(symbol, "A", financials, (f_pass, f_detail))
                        ai_insight = self.analyst.analyze_with_llm(prompt)
                        
                        recommendations.append({
                            "name": name,
                            "symbol": symbol,
                            "sector": sector_name,
                            "reason": f"{f_detail} | {t_detail} | RS强度: {round(rs_score, 2)}",
                            "ai_insight": ai_insight
                        })

        # 3. 生成报告
        self._generate_final_report(recommendations, light, light_msg, sell_warnings)

    def _generate_final_report(self, recommendations, light, light_msg, sell_warnings):
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        filename = f"{report_dir}/daily_decision_{datetime.now().strftime('%Y%m%d')}.md"
        
        content = f"# 投资哨兵每日决策日报 ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        content += f"## 🚦 市场环境监控\n"
        content += f"- **当前红绿灯**: {light}\n"
        content += f"- **状态描述**: {light_msg}\n\n"
        
        if sell_warnings:
            content += "## ⚠️ 卖出风险预警\n"
            for sw in sell_warnings:
                content += f"- **{sw['name']} ({sw['symbol']})**: \n{sw['desc']}\n"
            content += "\n"

        if light == "RED":
            content += "## 📢 策略建议：空仓避险\n"
            content += "大盘趋势转弱，目前不是介入良机。建议等待市场企稳回暖。\n"
        elif not recommendations:
            content += "## 📢 策略建议：观望\n"
            content += "大盘环境尚可，但全市场扫描未发现符合【基本面+蓄势板块+相对强度+技术面】多维过滤的优质标的。建议保持耐心。\n"
        else:
            content += "## 🚀 今日精选标的\n"
            for rec in recommendations:
                content += f"### {rec['name']} ({rec['symbol']})\n"
                content += f"- **所属板块**: {rec['sector']}\n"
                content += f"- **量化评分**: {rec['reason']}\n"
                content += f"#### 🧠 AI 深度点评:\n{rec['ai_insight']}\n\n"
        
        content += "\n---\n*本报告由 AlphaTide 自动化系统生成，仅供参考。风险自担。*"
        
        with open(filename, 'w') as f:
            f.write(content)
        print(f"\n✅ 每日决策报告已生成: {filename}")


if __name__ == "__main__":
    monitor = MarketMonitor()
    monitor.run_daily_scan()
