import pandas as pd

import akshare as ak

from src.data_fetcher import (
    fetch_with_cache, fetch_a_valuation_history, fetch_a_stock_hist_cached,
    fetch_latest_zcfz, fetch_executive_holdings, fetch_stock_repurchases
)

class Screener:
    def __init__(self):
        # 基础筛选条件 (放宽ROE要求，交由AI深度判断困境反转)
        self.min_roe = 5.0
        self.min_growth = 20.0
        self.max_debt_ratio = 50.0
        self.min_cash_profit_ratio = 0.8
        
        # Load extra datasets once per screener instance to save time
        self.zcfz_df = fetch_latest_zcfz()
        self.executive_df = fetch_executive_holdings()
        self.repurchase_df = fetch_stock_repurchases()

    def screen_valuation(self, symbol, target_date=None):
        """
        估值百分位筛选：判断当前 PE 是否处于历史低位 (过去5年)
        """
        try:
            df = fetch_a_valuation_history(symbol)
            if df is None or df.empty: return True, "估值数据缺失"
            
            if target_date:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
                df = df[df['trade_date'] <= pd.to_datetime(target_date)]
            
            # 取最近 1250 个交易日 (约5年)
            df_5y = df.tail(1250)
            if df_5y.empty: return True, "估值样本不足"
            
            latest_pe = df_5y.iloc[-1]['pe']
            if pd.isna(latest_pe): return True, "当前PE数据无效"
            
            # 计算百分位
            pe_series = df_5y['pe'].dropna()
            if pe_series.empty: return True, "无有效历史PE数据"
            
            percentile = (pe_series < latest_pe).mean() * 100
            
            if percentile > 85:
                return False, f"估值过高: PE百分位 {round(percentile, 1)}% (>85%)"
            return True, f"估值合理: PE百分位 {round(percentile, 1)}%"
        except Exception as e:
            return True, f"估值分析跳过: {e}"

    def screen_technical(self, symbol, target_date=None, mode='value'):
        """
        Technical Screen with Dual Engines:
        mode 'value': Fundamental Pullback (缩量回踩 EMA20/30) - For white horses.
        mode 'momentum': Breakout/Surge (近5日异动大阳线) - For hot sectors.
        """
        try:
            df = fetch_a_stock_hist_cached(symbol, period="daily", adjust="qfq", expiry_hours=24)
            
            if target_date:
                df['日期'] = pd.to_datetime(df['日期'])
                df = df[df['日期'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 60: return False, "数据不足60天"
            
            # 流动性基础过滤：近5日平均成交额大于 5000 万
            avg_turnover_5d = df.iloc[-5:]['成交额'].mean()
            if avg_turnover_5d < 50_000_000:
                return False, f"流动性不足 (日均成交<5000万)"

            latest_price = df.iloc[-1]['收盘']
            latest_vol = df.iloc[-1]['成交量']
            
            # 使用 EMA 替代 SMA (反应更灵敏)
            df['ema20'] = df['收盘'].ewm(span=20, adjust=False).mean()
            df['ema60'] = df['收盘'].ewm(span=60, adjust=False).mean()
            
            ema20 = df['ema20'].iloc[-1]
            ema60 = df['ema60'].iloc[-1]
            vol_ma5 = df.iloc[-5:]['成交量'].mean()
            
            # MACD 计算
            ema12 = df['收盘'].ewm(span=12, adjust=False).mean()
            ema26 = df['收盘'].ewm(span=26, adjust=False).mean()
            diff = ema12 - ema26
            dea = diff.ewm(span=9, adjust=False).mean()
            macd = 2 * (diff - dea)
            
            latest_macd = macd.iloc[-1]
            prev_macd = macd.iloc[-2]

            if mode == 'value':
                # 白马回踩引擎：EMA60向上，近期回调到 EMA20 附近 且 显著缩量，且 MACD 未死叉或正处于金叉初期
                ema60_prev = df['ema60'].iloc[-10]
                is_uptrend = ema60 > ema60_prev or latest_price > ema60
                
                bias_ema20 = abs(latest_price - ema20) / ema20
                is_pullback = bias_ema20 < 0.03  # 距离EMA20不到3%
                is_shrinking = latest_vol < vol_ma5 * 0.8 # 明显缩量
                
                # MACD 辅助确认：红柱放大或绿柱缩短
                macd_ok = latest_macd > prev_macd
                
                if is_uptrend and is_pullback and is_shrinking and macd_ok:
                    return True, f"价值引擎: 缩量回踩 EMA20 企稳 (MACD动能改善)"
                else:
                    return False, "未满足缩量回踩或MACD走弱"
                    
            elif mode == 'momentum':
                # 游资异动引擎（改良版）：近期(2-5日内)有标志性突破放量大阳线，但目前处于缩量回踩阶段，避免高位接盘
                recent_5d = df.iloc[-5:]
                recent_30d_vol_avg = df.iloc[-30:]['成交量'].mean()
                
                breakout_idx = -1
                breakout_row = None
                
                # 从过去5日数据中（不包含今天）寻找标志性放量突破大阳线
                for i in range(len(recent_5d) - 1):
                    row = recent_5d.iloc[i]
                    pct_change = (row['收盘'] - row['开盘']) / row['开盘']
                    vol_ratio = row['成交量'] / recent_30d_vol_avg
                    if pct_change > 0.05 and vol_ratio > 1.5:
                        breakout_idx = i
                        breakout_row = row
                        break
                
                # 如果没有近期突破，或者突破发生在今天（代表今天正在暴涨，只有低位首板才允许买入）
                if breakout_row is None:
                    latest_row = recent_5d.iloc[-1]
                    pct_change = (latest_row['收盘'] - latest_row['开盘']) / latest_row['开盘']
                    vol_ratio = latest_row['成交量'] / recent_30d_vol_avg
                    if pct_change > 0.05 and vol_ratio > 1.5:
                        # 检查今天是否离均线过远 (比如偏离 EMA10 > 6% 代表追高)
                        df['ema10'] = df['收盘'].ewm(span=10, adjust=False).mean()
                        ema10 = df['ema10'].iloc[-1]
                        bias_ema10 = (latest_price - ema10) / ema10
                        if bias_ema10 <= 0.06 and latest_macd > 0:
                            return True, f"游资引擎 (日内异动): 今日低位放量首板启动 (MACD多头)"
                    return False, "缺乏近期资金突破或今日已涨幅过高"
                
                # 存在近期突破大阳线，判断今天是否是“缩量回踩”
                # 1. 今天收盘价高于 EMA10 (趋势仍在)
                df['ema10'] = df['收盘'].ewm(span=10, adjust=False).mean()
                ema10 = df['ema10'].iloc[-1]
                is_above_support = latest_price > ema10
                
                # 2. 今天收盘价低于或等于突破日收盘价，或者处于突破高点的小幅回撤区间（防连续暴涨）
                is_pullback = latest_price <= breakout_row['收盘'] * 1.02
                
                # 3. 今天成交量显著缩量（成交量小于 5 日均量，且小于突破日成交量的 70%）
                is_shrinking = latest_vol < vol_ma5 and latest_vol < breakout_row['成交量'] * 0.7
                
                if is_above_support and is_pullback and is_shrinking and latest_macd > 0:
                    return True, f"游资引擎 (回踩买点): 近期异动大阳线后缩量回踩 EMA10 (MACD多头)"
                else:
                    return False, "突破后未缩量或股价未能企稳回踩"
                    
            return False, "未知模式"
        except Exception as e:
            return False, f"技术面分析失败: {str(e)}"

    def get_stocks_in_sector(self, sector_name, sector_label=None):
        """获取板块内的个股代码"""
        # 定义东财到新浪板块标签的映射，应对东财被封锁的情况
        em_to_sina = {
            # 通信/电子/半导体 -> 电子信息/电子器件
            "通信设备": "new_dzxx", "通信": "new_dzxx", "通信网络设备及器件": "new_dzxx",
            "计算机设备": "new_dzxx", "软件开发": "new_dzxx", "IT服务": "new_dzxx",
            "半导体": "new_dzqj", "电子元件": "new_dzqj", "光学光电子": "new_dzqj",
            "消费电子": "new_dzqj", "电子化学品": "new_dzqj",
            # 资源/化工/有色/煤炭/石油/钢铁
            "有色金属": "new_ysjs", "小金属": "new_ysjs", "金属新材料": "new_ysjs",
            "煤炭行业": "new_mthy", "石油行业": "new_syhy", "石油加工": "new_syhy",
            "钢铁行业": "new_gthy", "化学制品": "new_hghy", "化学原料": "new_hghy",
            "农药兽药": "new_nyhf", "化肥行业": "new_nyhf", "塑料制品": "new_slzp",
            "橡胶制品": "new_slzp", "化学纤维": "new_hqhy",
            # 电力/新能源/设备
            "电力行业": "new_dlhy", "光伏设备": "new_fdsb", "风电设备": "new_fdsb",
            "电网设备": "new_dqhy", "电机": "new_dqhy", "电池": "new_dqhy",
            # 医药/医疗
            "化学制药": "new_swzz", "生物制品": "new_swzz", "中药": "new_swzz",
            "医药商业": "new_sybh", "医疗器械": "new_ylqx", "医疗服务": "new_ylqx",
            # 机械/制造
            "通用设备": "new_jxhy", "专用设备": "new_jxhy", "仪器仪表": "new_yqyb",
            "轨交设备": "new_jxhy", "工程机械": "new_jxhy", "船舶制造": "new_cbzz",
            "航空机场": "new_jtys", "航天航空": "new_fjzz", "汽车整车": "new_qczz",
            "汽车零部件": "new_qczz",
            # 消费/金融/其他
            "酿酒行业": "new_ljhy", "食品饮料": "new_sphy", "农林牧渔": "new_nlmy",
            "家电行业": "new_jdhy", "装修建材": "new_jzjc", "水泥建材": "new_snhy",
            "房地产开发": "new_fdc", "房地产服务": "new_fdc", "银行": "new_jrhy",
            "证券": "new_jrhy", "保险": "new_jrhy", "多元金融": "new_jrhy",
            "工程建设": "new_jzjc", "商业百货": "new_sybh", "旅游酒店": "new_jdly",
            "传媒": "new_cmyl", "游戏": "new_cmyl",
        }

        # 如果没有传 sector_label，尝试从映射表中查找
        if not sector_label and sector_name in em_to_sina:
            sector_label = em_to_sina[sector_name]

        # 1. 尝试使用 Sina 接口 (更稳定，不怕封锁)
        if sector_label:
            try:
                df = ak.stock_sector_detail(sector=sector_label)
                if df is not None and not df.empty:
                    df = df.rename(columns={'code': '代码', 'name': '名称'})
                    return df[['代码', '名称']]
            except Exception as e:
                print(f"⚠️ 使用新浪接口获取板块 [{sector_name}] 成分股失败: {e}")

        # 2. 备选：使用东财板块成分股接口
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            if df is not None and not df.empty:
                return df[['代码', '名称']]
        except Exception as e:
            print(f"⚠️ 使用东财接口获取板块 [{sector_name}] 成分股失败: {e}")

        return None

    def screen_a_share(self, symbol, df, min_roe=None):
        """
        Screen A-share based on abstract data.
        Indicators: ROE, Growth Trend, Cash-to-Profit Ratio.
        """
        if df is None or df.empty:
            return False, "无数据"
        
        target_roe = min_roe if min_roe is not None else self.min_roe
        
        try:
            reasons = []
            passed = True

            def get_series(name):
                row = df[df['指标'].str.contains(name, na=False, regex=False)]
                if not row.empty:
                    # Get all numeric values from columns starting from index 2
                    vals = []
                    for col_idx in range(2, min(len(row.columns), 6)):
                        val = row.iloc[0, col_idx]
                        if pd.notnull(val):
                            try:
                                vals.append(float(val))
                            except: pass
                    return vals
                return []

            # 1. ROE (最新一期)
            roe_list = get_series('净资产收益率(ROE)')
            if not roe_list: roe_list = get_series('净资产收益率')
            
            latest_roe = roe_list[0] if roe_list else None
            
            # 根据财报公布期进行年化处理（解决一季报、半年报等非年度指标偏低导致被误杀的问题）
            latest_date = str(df.columns[2]) if len(df.columns) > 2 else ""
            roe_multiplier = 1.0
            quarter_name = "年报"
            if latest_date.endswith("0331"):
                roe_multiplier = 4.0
                quarter_name = "一季报(已年化)"
            elif latest_date.endswith("0630"):
                roe_multiplier = 2.0
                quarter_name = "半年报(已年化)"
            elif latest_date.endswith("0930"):
                roe_multiplier = 4.0 / 3.0
                quarter_name = "三季报(已年化)"
                
            if latest_roe is not None:
                annualized_roe = latest_roe * roe_multiplier
                if annualized_roe >= target_roe:
                    reasons.append(f"ROE: {round(annualized_roe, 2)}% ({quarter_name})")
                else:
                    passed = False
                    reasons.append(f"ROE不达标: {round(annualized_roe, 2)}% ({quarter_name}, 要求>={target_roe}%)")
            else:
                passed = False
                reasons.append("无有效ROE数据")

            # 2. 增长斜率 (归母净利润同比)
            growth_list = get_series('归母净利润同比增长')
            if not growth_list: growth_list = get_series('净利润同比增长')
            
            if len(growth_list) >= 3:
                # 检查是否加速增长: 最近 > 上一期 > 上上期
                if growth_list[0] > growth_list[1] > growth_list[2]:
                    reasons.append(f"🔥 业绩加速: {growth_list[0]}% > {growth_list[1]}% > {growth_list[2]}%")
                elif growth_list[0] < 0:
                    passed = False
                    reasons.append(f"业绩下滑: {growth_list[0]}%")
                else:
                    reasons.append(f"增长: {growth_list[0]}%")
            elif growth_list:
                 reasons.append(f"增长: {growth_list[0]}%")

            # 3. 净现比 (经营现金流 / 净利润)
            net_profit_list = get_series('归母净利润')
            cash_flow_list = get_series('经营现金流量净额')
            if net_profit_list and cash_flow_list and net_profit_list[0] != 0:
                ratio = cash_flow_list[0] / net_profit_list[0]
                if ratio > self.min_cash_profit_ratio:
                    reasons.append(f"净现比: {round(ratio, 2)}")
                else:
                    passed = False
                    reasons.append(f"净现比低: {round(ratio, 2)}")

            # 4. 合同负债 (前瞻性) - 使用资产负债表数据 (预收账款/合同负债)
            if self.zcfz_df is not None and not self.zcfz_df.empty:
                stock_zcfz = self.zcfz_df[self.zcfz_df['股票代码'] == symbol]
                if not stock_zcfz.empty:
                    adv_receipts = stock_zcfz.iloc[0].get('负债-预收账款', 0)
                    if pd.notna(adv_receipts) and float(adv_receipts) > 0:
                        reasons.append(f"有合同负债(预收): {round(float(adv_receipts)/100000000, 2)}亿")
                        
            # 5. 高管增持 / 股份回购 (内部人信心)
            has_insider_support = False
            if self.executive_df is not None and not self.executive_df.empty:
                # 检查高管增持
                exec_changes = self.executive_df[self.executive_df['SECURITY_CODE'] == symbol]
                if not exec_changes.empty:
                    # 判断是否有增持
                    buy_actions = exec_changes[exec_changes['CHANGE_DIR'] == '增持']
                    if not buy_actions.empty:
                        has_insider_support = True
                        reasons.append(f"⭐ 近期有高管增持")
            
            if self.repurchase_df is not None and not self.repurchase_df.empty:
                # 检查股份回购
                repurchases = self.repurchase_df[self.repurchase_df['股票代码'] == symbol]
                if not repurchases.empty:
                    has_insider_support = True
                    reasons.append(f"⭐ 近期有股份回购计划")

            return passed, ", ".join(reasons)
            
        except Exception as e:
            return False, f"筛选出错: {e}"

    def screen_hk_technical(self, symbol, target_date=None):
        """
        HK Technical Screen (Mean Reversion & Value Investing):
        1. Liquidity: 20-day avg turnover > 100M HKD
        2. Trend: Price < MA60 (Mean Reversion) & RSI(14) < 40 (Oversold) OR Price near MA250 (Support)
        """
        try:
            # 使用新浪接口防止被封
            df = fetch_with_cache(f"hist_hk_{symbol}", ak.stock_hk_daily, expiry_hours=24, symbol=symbol, adjust="qfq")
            
            if target_date:
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] <= pd.to_datetime(target_date)]

            if df.empty or len(df) < 60: return False, "数据不足60天"
            
            # 流动性过滤：近20日平均成交额大于1亿
            avg_turnover_20d = df.iloc[-20:]['amount'].mean()
            if avg_turnover_20d < 100_000_000:
                return False, f"流动性不足 (日均成交<1亿港币)"

            latest_price = df.iloc[-1]['close']
            df['ema60'] = df['close'].ewm(span=60, adjust=False).mean()
            ema60 = df['ema60'].iloc[-1]
            
            # 简单 RSI 计算
            delta = df['close'].diff()
            up = delta.clip(lower=0)
            down = -1 * delta.clip(upper=0)
            ema_up = up.ewm(com=13, adjust=False).mean()
            ema_down = down.ewm(com=13, adjust=False).mean()
            rs = ema_up / ema_down
            rsi_14 = 100 - (100 / (1 + rs))
            latest_rsi = rsi_14.iloc[-1]
            
            # 左侧均值回归逻辑：在半年线(EMA60)下方，且出现超卖信号(RSI<40)
            if latest_price < ema60 and latest_rsi < 40:
                return True, f"左侧潜伏点 (流动性>1亿, 在EMA60下方且RSI={round(latest_rsi,1)} 超卖)"
            else:
                return False, f"未见严重超卖或价格过高 (RSI={round(latest_rsi,1)})"
        except Exception as e:
            return False, f"技术面分析失败: {str(e)}"

    def screen_hk_share(self, df, min_roe=None):
        """
        Screen HK stock based on Value indicators (Dividend Yield & PB).
        """
        if df is None or df.empty:
            return False, "无数据"
        
        try:
            latest = df.iloc[0]
            
            # 获取港股红利与估值指标 (根据 akshare 字段调整，部分可能需容错)
            # 注意: ak.stock_hk_spot_em() 或 ak.stock_hk_indicator_em() 提供的字段可能有差异
            # 这里尝试获取常见字段
            div_yield = latest.get('股息率(%)', latest.get('股息率', 0))
            pb = latest.get('市净率', latest.get('PB', 1.0))
            
            div_yield = float(div_yield) if pd.notna(div_yield) and str(div_yield).replace('.','',1).isdigit() else 0
            pb = float(pb) if pd.notna(pb) and str(pb).replace('.','',1).isdigit() else 1.0
            
            reasons = []
            passed = True
            
            # 核心1：股息率防守
            if div_yield >= 4.0:
                reasons.append(f"高股息: {div_yield}%")
            else:
                passed = False
                reasons.append(f"股息率过低: {div_yield}% (要求>=4%)")
                
            # 核心2：估值保护 (防老千股，也防泡沫股)
            if 0.3 <= pb <= 1.5:
                reasons.append(f"估值合理: PB={pb}")
            else:
                passed = False
                reasons.append(f"估值不符合要求: PB={pb} (要求 0.3-1.5)")

            return passed, ", ".join(reasons)
        except Exception as e:
            return False, f"筛选出错: {e}"
