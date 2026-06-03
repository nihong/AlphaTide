import os
import sys
import pandas as pd
from datetime import datetime
import time
from src.data_fetcher import fetch_market_tide, fetch_a_stock_financials, fetch_hk_stock_financials, fetch_market_index
from src.rotation_predictor import RotationPredictor
from src.screener import Screener
from src.history_manager import HistoryManager
from src.ai_analyst import AIAnalyst
from src.sentiment_engine import SentimentEngine
from src.risk_manager import RiskManager
from src.macro_engine import MacroEngine


class MarketMonitor:
    def __init__(self):
        self.predictor = RotationPredictor()
        self.screener = Screener()
        self.history = HistoryManager()
        self.analyst = AIAnalyst()
        self.risk = RiskManager()
        self.sentiment = SentimentEngine()
        self.macro = MacroEngine()


    def check_market_light(self, target_date=None):
        """红绿灯系统：根据大盘与中证500(中小盘赚钱效应)判断市场环境"""
        # 使用沪深300 sh000300 代表权重
        df_300 = fetch_market_index("sh000300")
        # 使用中证500 sh000905 代表中小盘活跃度(赚钱效应代理)
        df_500 = fetch_market_index("sh000905")
        
        if df_300 is None or df_300.empty: return "YELLOW", "数据获取失败，默认建议仓位: 30%"
        
        if target_date:
            df_300['date'] = pd.to_datetime(df_300['date'])
            df_300 = df_300[df_300['date'] <= pd.to_datetime(target_date)]
            if df_500 is not None and not df_500.empty:
                df_500['date'] = pd.to_datetime(df_500['date'])
                df_500 = df_500[df_500['date'] <= pd.to_datetime(target_date)]
            if df_300.empty: return "YELLOW", f"找不到 {target_date} 之前的数据"

        latest_price = df_300.iloc[-1]['close']
        ma20 = df_300.iloc[-20:]['close'].mean()
        latest_vol = df_300.iloc[-1]['volume']
        vol_ma5 = df_300.iloc[-5:]['volume'].mean()
        
        is_uptrend = latest_price > ma20
        is_expanding_vol = latest_vol > vol_ma5
        
        # 中小盘赚钱效应代理 (CSI 500 > MA20)
        has_breadth = False
        if df_500 is not None and len(df_500) >= 20:
            latest_500 = df_500.iloc[-1]['close']
            ma20_500 = df_500.iloc[-20:]['close'].mean()
            has_breadth = latest_500 > ma20_500
        
        if is_uptrend:
            if is_expanding_vol:
                return "GREEN", f"🟢 多头环境且放量 (沪深300>MA20, 量>5日均量)，建议重仓 (仓位: 80%)"
            else:
                if has_breadth:
                    return "GREEN", f"🟢 沪深300缩量但中证500活跃(存在结构性赚钱效应)，允许游资出击 (仓位: 60%)"
                return "YELLOW", f"🟡 多头环境但缩量 (动能不足)，建议观望或轻仓 (仓位: 30%)"
        else:
            if is_expanding_vol:
                return "RED", f"🔴 空头环境且放量下跌，风险极大，建议空仓避险 (仓位: 0%)"
            else:
                if has_breadth:
                    return "YELLOW", f"🟡 权重护盘不力但中小盘活跃(题材行情)，建议轻仓参与题材 (仓位: 30%)"
                return "YELLOW", f"🟡 空头环境但缩量下跌 (存在止跌惜售迹象)，建议观望 (仓位: 30%)"

    def check_hk_market_light(self, target_date=None):
        from src.data_fetcher import fetch_hk_market_index
        df = fetch_hk_market_index("HSI")
        if df is None or df.empty: return "YELLOW", "数据获取失败，默认建议仓位: 30%"
        
        if target_date:
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] <= pd.to_datetime(target_date)]
            if df.empty: return "YELLOW", f"找不到 {target_date} 之前的数据"

        latest_price = df.iloc[-1]['close']
        ma20 = df.iloc[-20:]['close'].mean()
        latest_vol = df.iloc[-1]['volume']
        vol_ma5 = df.iloc[-5:]['volume'].mean()
        
        is_uptrend = latest_price > ma20
        is_expanding_vol = latest_vol > vol_ma5
        
        if is_uptrend:
            if is_expanding_vol:
                return "GREEN", f"🟢 多头环境且放量 (恒指>MA20, 量>5日均量)，建议重仓 (仓位: 80%)"
            else:
                return "YELLOW", f"🟡 多头环境但缩量 (动能不足)，建议观望或轻仓 (仓位: 30%)"
        else:
            if is_expanding_vol:
                return "RED", f"🔴 空头环境且放量下跌 (恒指<MA20, 量>5日均量)，风险极大，建议空仓避险 (仓位: 0%)"
            else:
                return "YELLOW", f"🟡 空头环境但缩量下跌 (存在止跌惜售迹象)，建议观望 (仓位: 30%)"

    def run_hk_scan(self, target_date=None):
        run_time = target_date if target_date else datetime.now().strftime('%Y-%m-%d')
        print(f"[{run_time}] 🚀 启动 [港股] 自动哨兵监控...")
        
        light, light_msg = self.check_hk_market_light(target_date)
        print(f"🚦 港股大盘红绿灯: {light} - {light_msg}")
        
        if light == "RED":
            self._generate_final_report([], light, light_msg, [], target_date, market="HK")
            print("🛑 港股市场风险较大，已生成风险预警报告，停止进一步扫描。")
            return

        try:
            import akshare as ak
            df_hk = ak.stock_hk_spot()
            df_hk['成交额'] = pd.to_numeric(df_hk['成交额'], errors='coerce')
            df_hk['涨跌幅'] = pd.to_numeric(df_hk['涨跌幅'], errors='coerce')
            
            # 港股高流动性池：成交额前50名，且非大跌（涨跌幅 > -5%）
            top_hk = df_hk[df_hk['涨跌幅'] > -5].sort_values(by='成交额', ascending=False).head(50)
            
        except Exception as e:
            print(f"获取港股列表失败: {e}")
            return
            
        recommendations = []
        sell_warnings = []

        print(f"\n🔍 正在扫描港股高流动性池 (Top 50) ...")
        for _, stock in top_hk.iterrows():
            symbol = str(stock['代码'])
            name = stock['中文名称']
            
            # A. 卖出信号检查
            exit_signals, exit_desc = self.risk.evaluate_hk_exit_signals(symbol, target_date=target_date)
            if exit_signals:
                sell_warnings.append({"name": name, "symbol": symbol, "desc": exit_desc})

            # B. 买入机会筛选 (三维过滤)
            rs_score = self.risk.get_hk_rs_rating(symbol, target_date=target_date)
            if rs_score < 0: continue
            
            financials = fetch_hk_stock_financials(symbol)
            f_pass, f_detail = self.screener.screen_hk_share(financials)
            
            if f_pass:
                t_pass, t_detail = self.screener.screen_hk_technical(symbol, target_date=target_date)
                if t_pass:
                    print(f"✨ 发现优质港股: {name} ({symbol}) | RS强度: {round(rs_score, 2)}")
                    
                    suggested_pos = self.risk.calculate_hk_position_size(symbol, target_date=target_date)
                    pos_str = f"{round(suggested_pos * 100, 1)}%"
                    
                    prompt = self.analyst.generate_report_prompt(symbol, "HK", financials, (f_pass, f_detail))
                    ai_insight = self.analyst.analyze_with_llm(prompt)
                    
                    recommendations.append({
                        "name": name,
                        "symbol": symbol,
                        "sector": "港股核心资产",
                        "reason": f"{f_detail} | {t_detail} | RS强度: {round(rs_score, 2)}",
                        "position": pos_str,
                        "ai_insight": ai_insight,
                        "resonance_count": 0
                    })

        self._generate_final_report(recommendations, light, light_msg, sell_warnings, target_date, market="HK")

    def run_daily_scan(self, target_date=None, market="A"):
        if market == "HK":
            self.run_hk_scan(target_date)
            return
            
        run_time = target_date if target_date else datetime.now().strftime('%Y-%m-%d')
        print(f"[{run_time}] 🚀 启动 [A股] 自动哨兵监控" + (" (历史回测模式)..." if target_date else "..."))
        
        # 0. 全球宏观环境监控 (方案 A)
        macro_status = None
        if not target_date:
            macro_status = self.macro.get_global_status()
            print(f"🌍 全球宏观天气: {macro_status['weather']}")

        
        # 0. 环境检查
        if not os.path.exists(".env"):
            print("⚠️ 警告: 根目录未发现 .env 文件，AI 点评功能将无法完整运行。请参考 .env.example 配置。")

        # 0. 大盘红绿灯
        light, light_msg = self.check_market_light(target_date)
        print(f"🚦 大盘红绿灯: {light} - {light_msg}")
        
        if light == "RED":
            self._generate_final_report([], light, light_msg, [], target_date, market=market)
            print("🛑 市场风险较大，已生成风险预警报告，停止进一步扫描。")
            return

        # 1. 舆情热点探测 (降维打击：感知市场体温)
        market_temperature = []
        if not target_date and market == "A": 
            market_temperature = self.sentiment.get_hot_sectors_with_news(top_n=5)

        # 2. 双核引擎识别蓄势与热门板块
        acc_df, mom_df = self.predictor.predict_sectors()
        
        sectors_to_scan = []
        
        # 精细化板块分析：识别“新晋”热门板块 (过去3天未出现在 Top 3 中)
        history_data = {}
        try:
            with open(self.history.storage_path, 'r') as f:
                history_data = json.load(f)
        except: pass
        
        past_3d_sectors = set()
        dates = sorted(history_data.keys(), reverse=True)[:3]
        for d in dates:
            past_3d_sectors.update(history_data[d].keys())

        if acc_df is not None and not acc_df.empty:
            acc_top = acc_df.head(3)
            for _, row in acc_top.iterrows():
                name = row['名称'] if '名称' in row else row['板块']
                label = row['label'] if 'label' in row else None
                is_new = name not in past_3d_sectors
                sectors_to_scan.append({'name': name, 'label': label, 'type': '潜伏蓄势', 'is_new': is_new})
            print(f"🔥 锁定 Top 3 蓄势板块: {[s['name'] for s in sectors_to_scan if s['type'] == '潜伏蓄势']}")
            
        if mom_df is not None and not mom_df.empty:
            mom_top = mom_df.head(3)
            for _, row in mom_top.iterrows():
                name = row['名称'] if '名称' in row else row['板块']
                label = row['label'] if 'label' in row else None
                is_new = name not in past_3d_sectors
                sectors_to_scan.append({'name': name, 'label': label, 'type': '动量热门', 'is_new': is_new})
            print(f"🔥 锁定 Top 3 热门板块: {[s['name'] for s in sectors_to_scan if s['type'] == '动量热门']}")

        # 记录今日板块数据以便后续识别“新晋”
        current_stats = {s['name']: 100 for s in sectors_to_scan}
        self.history.record_daily_stats(current_stats)

        if not sectors_to_scan:
            print("⚠️ 未发现明显机会板块，今天建议观望。")
            self._generate_final_report([], light, light_msg, [], target_date, market=market, sentiment_data=market_temperature)
            return

        recommendations = []
        sell_warnings = []
        
        # 去重与题材共振追踪
        scanned_symbols = {} # {symbol: {data, sectors: []}}

        # 3. 在每个行业内精选个股
        for sector_info in sectors_to_scan:
            sector_name = sector_info['name']
            sector_label = sector_info['label']
            sector_type = sector_info['type']
            is_new_sector = sector_info['is_new']
            
            tag = " [新晋!]" if is_new_sector else ""
            print(f"\n🔍 正在扫描 [{sector_type}]{tag} 板块: {sector_name} ...")
            stocks = self.screener.get_stocks_in_sector(sector_name, sector_label=sector_label)
            if stocks is None or stocks.empty: continue
            
            # 每个行业扫描前30只龙头股
            count = 0
            for _, stock in stocks.head(30).iterrows():
                symbol = str(stock['代码'])
                name = stock['名称']
                
                # 过滤北交所股票 (代码以 '8' 或 '4' 开头) 和 ST 股
                if symbol.startswith('8') or symbol.startswith('4') or 'ST' in name:
                    continue
                
                count += 1
                # 记录题材共振
                if symbol in scanned_symbols:
                    if sector_name not in scanned_symbols[symbol]['sectors']:
                        scanned_symbols[symbol]['sectors'].append(sector_name)
                    continue
                else:
                    scanned_symbols[symbol] = {'name': name, 'sectors': [sector_name]}
                
                # A. 卖出信号检查
                exit_signals, exit_desc = self.risk.evaluate_exit_signals(symbol, target_date=target_date)
                if exit_signals:
                    sell_warnings.append({"name": name, "symbol": symbol, "desc": exit_desc})

                # B. 买入机会筛选
                rs_score = self.risk.get_rs_rating(symbol, target_date=target_date)
                if rs_score < 0: 
                    print(f"  - {name} ({symbol}) RS分过低: {round(rs_score, 2)}")
                    continue
                
                # C. 估值百分位过滤 (新增)
                v_pass, v_detail = self.screener.screen_valuation(symbol, target_date=target_date)
                if not v_pass:
                    print(f"  - {name} ({symbol}) 估值过高: {v_detail}")
                    continue

                # 策略改进：双引擎解耦
                if sector_type == '潜伏蓄势':
                    target_roe = 5.0
                    tech_mode = 'value'
                else:
                    target_roe = 3.0 # 热门股放宽基本面要求
                    tech_mode = 'momentum'
                
                financials = fetch_a_stock_financials(symbol)
                f_pass, f_detail = self.screener.screen_a_share(symbol, financials, min_roe=target_roe)
                
                if not f_pass:
                    print(f"  - {name} ({symbol}) 基本面未过: {f_detail}")
                    continue

                t_pass, t_detail = self.screener.screen_technical(symbol, target_date=target_date, mode=tech_mode)
                if t_pass:
                    suggested_pos = self.risk.calculate_position_size(symbol, target_date=target_date)
                    pos_str = f"{round(suggested_pos * 100, 1)}%"
                    
                    scanned_symbols[symbol]['passed'] = True
                    scanned_symbols[symbol]['f_detail'] = f_detail + " | " + v_detail
                    scanned_symbols[symbol]['t_detail'] = t_detail
                    scanned_symbols[symbol]['rs_score'] = rs_score
                    scanned_symbols[symbol]['pos_str'] = pos_str
                    scanned_symbols[symbol]['financials'] = financials
                else:
                    print(f"  - {name} ({symbol}) 技术面未过: {t_detail}")
                    pass
            print(f"  - 板块 {sector_name} 扫描完成，实际检查个股数: {count}")

        # 4. 汇总与共振加分
        for symbol, data in scanned_symbols.items():
            if data.get('passed'):
                resonance_str = " | ".join(data['sectors'])
                resonance_bonus = "🌟 (题材共振)" if len(data['sectors']) > 1 else ""
                
                # 识别是否包含新晋题材
                is_new_resonance = any(s in [sec['name'] for sec in sectors_to_scan if sec['is_new']] for s in data['sectors'])
                new_tag = " 🔥 [新题材!]" if is_new_resonance else ""
                
                print(f"✨ 发现优质标的: {data['name']} ({symbol}) {resonance_bonus}{new_tag} | RS强度: {round(data['rs_score'], 2)}")
                
                prompt = self.analyst.generate_report_prompt(symbol, "A", data['financials'], (True, data['f_detail']))
                ai_insight = self.analyst.analyze_with_llm(prompt)
                
                recommendations.append({
                    "name": data['name'],
                    "symbol": symbol,
                    "sector": resonance_str + " " + resonance_bonus + new_tag,
                    "reason": f"{data['f_detail']} | {data['t_detail']} | RS强度: {round(data['rs_score'], 2)}",
                    "position": data['pos_str'],
                    "ai_insight": ai_insight,
                    "resonance_count": len(data['sectors'])
                })
                
        recommendations.sort(key=lambda x: x['resonance_count'], reverse=True)

        # 5. 生成报告
        self._generate_final_report(recommendations, light, light_msg, sell_warnings, target_date, market=market, sentiment_data=market_temperature, macro_data=macro_status)


    def _generate_final_report(self, recommendations, light, light_msg, sell_warnings, target_date=None, market="A", sentiment_data=None, macro_data=None):
        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        report_date = target_date.replace("-", "") if target_date else datetime.now().strftime('%Y%m%d')
        display_date = target_date if target_date else datetime.now().strftime('%Y-%m-%d')
        
        market_str = "A股" if market == "A" else "港股"
        filename = f"{report_dir}/daily_decision_{market}_{report_date}.md"
        
        content = f"# AlphaTide [{market_str}] 决策日报 (时间: {display_date})\n\n"
        
        if macro_data:
            content += f"## 🌍 全球宏观视野\n"
            content += f"- **宏观天气**: {macro_data['weather']}\n"
            content += f"- **纳斯达克**: {macro_data['nasdaq']['price']} ({macro_data['nasdaq']['desc']})\n"
            content += f"- **半导体指数**: {macro_data['sox']['price']} ({macro_data['sox']['desc']})\n"
            content += f"- **离岸汇率**: {macro_data['usdcny']['price']} ({macro_data['usdcny']['desc']})\n\n"

        content += f"## 🚦 市场环境监控\n"

        content += f"- **当前红绿灯**: {light}\n"
        content += f"- **状态描述**: {light_msg}\n\n"
        
        if sentiment_data:
            content += "## 🌡️ 全市场舆情体温 (AI 实时判读)\n"
            content += "| 板块名称 | 情绪分 | AI 核心逻辑与参与建议 |\n"
            content += "| :--- | :--- | :--- |\n"
            for item in sentiment_data:
                content += f"| {item['sector']} | **{item['score']}** | {item['summary']} |\n"
            content += "\n"

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
            content += "大盘环境尚可，但全市场扫描未发现符合【基本面+题材+相对强度+技术面】多维过滤的优质标的。建议保持耐心。\n"
        else:
            content += "## 🚀 今日精选标的\n"
            for rec in recommendations:
                content += f"### {rec['name']} ({rec['symbol']})\n"
                content += f"- **所属板块/题材**: {rec['sector']}\n"
                content += f"- **科学仓位建议**: 建议买入总资金的 **{rec['position']}** (基于 ATR 波动风险平权)\n"
                content += f"- **量化评分**: {rec['reason']}\n"
                content += f"#### 🧠 AI 深度点评:\n{rec['ai_insight']}\n\n"
        
        content += "\n---\n*本报告由 AlphaTide 自动化系统生成，仅供参考。风险自担。*"
        
        with open(filename, 'w') as f:
            f.write(content)
        print(f"\n✅ 每日决策报告已生成: {filename}")


if __name__ == "__main__":
    monitor = MarketMonitor()
    monitor.run_daily_scan()
