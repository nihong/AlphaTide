import pandas as pd
import akshare as ak
import os
import time
from datetime import datetime, timedelta
from src.data_fetcher import fetch_with_cache

class MacroCycleEngine:
    def __init__(self):
        pass

    def get_shipping_cycle(self):
        """
        获取航运宏观周期 (波罗的海BDI指数)
        用于前瞻航运物流板块的业绩拐点
        """
        def _fetch_bdi():
            return ak.macro_shipping_bdi()
            
        try:
            df = fetch_with_cache("macro_bdi", _fetch_bdi, expiry_hours=24)
            if df is not None and not df.empty:
                # 分析近 30 天的涨跌趋势
                recent = df.tail(30)
                latest_val = float(recent.iloc[-1]['最新值'])
                oldest_val = float(recent.iloc[0]['最新值'])
                trend_pct = (latest_val - oldest_val) / oldest_val
                
                is_booming = trend_pct > 0.15 # 一个月内运价飙升15%定义为景气周期
                return {
                    'indicator': 'BDI',
                    'latest_value': latest_val,
                    '30d_trend_pct': trend_pct,
                    'is_booming': is_booming
                }
        except Exception as e:
            print(f"BDI 抓取失败: {e}")
        return None

    def get_commodity_cycle(self, symbol="CU0", name="铜"):
        """
        获取大宗商品/原材料价格周期（用于前瞻资源股、周期股）
        symbol: CU0 (沪铜), AU0 (沪金), RB0 (螺纹钢)
        """
        def _fetch_commodity():
            return ak.futures_zh_daily_sina(symbol=symbol)
            
        try:
            df = fetch_with_cache(f"macro_commodity_{symbol}", _fetch_commodity, expiry_hours=24)
            if df is not None and not df.empty:
                recent = df.tail(60) # 看近三个月
                latest_val = float(recent.iloc[-1]['close'])
                oldest_val = float(recent.iloc[0]['close'])
                trend_pct = (latest_val - oldest_val) / oldest_val
                
                is_booming = trend_pct > 0.10 # 三个月内涨幅超过 10%
                return {
                    'indicator': name,
                    'latest_value': latest_val,
                    '60d_trend_pct': trend_pct,
                    'is_booming': is_booming
                }
        except Exception as e:
            print(f"{name} 抓取失败: {e}")
        return None

    def get_macro_indicator(self, indicator_type="export", name="出口数据"):
        """
        获取其它泛宏观指标 (出口、乘用车、社融、新房价格、CPI、票房等)
        """
        def _fetch_data():
            if indicator_type == "export":
                return ak.macro_china_exports_yoy()
            elif indicator_type == "auto":
                return ak.macro_china_passenger_load_factor()
            elif indicator_type == "finance":
                return ak.macro_china_shrzgm() # 社会融资规模
            elif indicator_type == "real_estate":
                return ak.macro_china_new_house_price()
            elif indicator_type == "cpi":
                return ak.macro_china_cpi()
            return pd.DataFrame()
            
        try:
            df = fetch_with_cache(f"macro_{indicator_type}", _fetch_data, expiry_hours=24)
            if df is not None and not df.empty:
                # 获取最新一期的值和前一期的值进行对比
                # 由于不同接口的列名不同，这里做简单容错处理
                latest_row = df.iloc[-1]
                prev_row = df.iloc[-2] if len(df) > 1 else latest_row
                
                # 尝试找到数值列
                val_cols = [c for c in df.columns if '值' in c or '今' in c or '当月' in c or '同比' in c]
                if val_cols:
                    val_col = val_cols[0]
                    latest_val = float(latest_row[val_col]) if pd.notna(latest_row[val_col]) else 0
                    prev_val = float(prev_row[val_col]) if pd.notna(prev_row[val_col]) else 0
                    
                    is_booming = latest_val > prev_val and latest_val > 0
                    trend_pct = (latest_val - prev_val) / abs(prev_val) if prev_val != 0 else 0
                    
                    return {
                        'indicator': name,
                        'latest_value': latest_val,
                        'trend_pct': trend_pct,
                        'is_booming': is_booming
                    }
        except Exception as e:
            print(f"{name} 宏观抓取失败: {e}")
        return None

    def verify_industry_trend(self, industry_name):
        """
        [核心] 宏观物理数据交叉验证！
        如果券商研报吹捧某个行业，必须经过此函数的“客观数据证伪”。
        返回: (bool 是否通过验证, str 验证详情)
        """
        print(f"🔎 正在对研报推荐板块【{industry_name}】进行客观物理数据交叉验证...")
        
        # 建立映射字典 (全面扩容)
        validation_matrix = {
            '航运': lambda: self.get_shipping_cycle(),
            '港口': lambda: self.get_shipping_cycle(),
            '有色': lambda: self.get_commodity_cycle("CU0", "沪铜"),
            '黄金': lambda: self.get_commodity_cycle("AU0", "沪金"),
            '生猪': lambda: self.get_commodity_cycle("lh0", "生猪期货"),
            '煤炭': lambda: self.get_commodity_cycle("jm0", "焦煤"),
            '白糖': lambda: self.get_commodity_cycle("SR0", "白糖"),
            '出海': lambda: self.get_macro_indicator("export", "出口年率"),
            '跨境': lambda: self.get_macro_indicator("export", "出口年率"),
            '汽车': lambda: self.get_macro_indicator("auto", "乘用车销量"),
            '新能源车': lambda: self.get_macro_indicator("auto", "乘用车销量"),
            '银行': lambda: self.get_macro_indicator("finance", "社会融资规模"),
            '金融': lambda: self.get_macro_indicator("finance", "社会融资规模"),
            '地产': lambda: self.get_macro_indicator("real_estate", "新房价格指数"),
            '建材': lambda: self.get_macro_indicator("real_estate", "新房价格指数"),
            '消费': lambda: self.get_macro_indicator("cpi", "CPI消费者物价"),
            '白酒': lambda: self.get_macro_indicator("cpi", "CPI消费者物价")
        }
        
        # 寻找匹配的宏观校验函数
        validator = None
        matched_key = ""
        for key in validation_matrix:
            if key in industry_name:
                validator = validation_matrix[key]
                matched_key = key
                break
                
        if not validator:
            return True, f"⚠️ 【{industry_name}】暂无对应的物理高频校验接口，放行但需谨慎。"
            
        result = validator()
        if not result:
            return False, f"❌ 数据获取失败，无法证伪【{industry_name}】，出于安全拒绝放行。"
            
        # 根据返回的结果判断
        trend_key = '60d_trend_pct' if '60d_trend_pct' in result else '30d_trend_pct'
        if 'trend_pct' in result: trend_key = 'trend_pct'
        
        trend_val = result[trend_key]
        
        if result['is_booming']:
            return True, f"✅ 物理数据验证成功！{result['indicator']} 近期趋势改善 ({trend_val:.2%})，与券商研报吻合！"
        else:
            return False, f"❌ 物理数据证伪！{result['indicator']} 近期趋势疲软 ({trend_val:.2%})，研报可能存在诱多嫌疑，拒绝买入！"

    def get_research_consensus_stocks(self, top_n=50):
        """
        获取全市场“盈利一致预期”最强烈的股票池。
        十倍股的启动伴随着券商研报的密集覆盖和盈利预测的大幅上调。
        返回：被研报覆盖最多、且未来两年预期利润高速增长的公司。
        """
        def _fetch_forecast():
            return ak.stock_profit_forecast_em()
            
        try:
            df = fetch_with_cache("macro_profit_forecast", _fetch_forecast, expiry_hours=24)
            if df is not None and not df.empty:
                # 清洗数据
                df['研报数'] = pd.to_numeric(df['研报数'], errors='coerce').fillna(0)
                # 取出当前年份的后两年（例如目前是2026年，就看2027和2028）
                # 由于列名可能随时变化，我们直接通过位置或关键词找
                forecast_cols = [c for c in df.columns if '预测每股收益' in c]
                
                if len(forecast_cols) >= 2:
                    col_year1 = forecast_cols[0] # 今年
                    col_year2 = forecast_cols[1] # 明年
                    
                    df[col_year1] = pd.to_numeric(df[col_year1], errors='coerce').fillna(0)
                    df[col_year2] = pd.to_numeric(df[col_year2], errors='coerce').fillna(0)
                    
                    # 过滤掉利润为负的
                    df = df[(df[col_year1] > 0) & (df[col_year2] > 0)]
                    # 计算预期成长率
                    df['预期增速'] = (df[col_year2] - df[col_year1]) / df[col_year1]
                    
                    # 过滤：研报数必须 >= 10 (机构高度关注)
                    df = df[df['研报数'] >= 10]
                    
                    # 按研报数量和预期增速排序
                    # 权重：研报数占40%，增速占60%
                    df['score'] = df['研报数'].rank(pct=True) * 0.4 + df['预期增速'].rank(pct=True) * 0.6
                    df = df.sort_values('score', ascending=False)
                    
                    top_df = df.head(top_n).copy()
                    return top_df[['代码', '名称', '研报数', '预期增速', col_year1, col_year2]]
        except Exception as e:
            print(f"盈利预测抓取失败: {e}")
            
        return pd.DataFrame()

    def analyze_macro_environment(self):
        """
        汇总所有的宏观感知器，输出当前的宏观景气赛道
        """
        print("🌍 [AI宏观雷达] 正在扫描全球产业链价格及机构一致预期...")
        
        # 1. 扫描航运大宗
        shipping = self.get_shipping_cycle()
        if shipping and shipping['is_booming']:
            print(f"🚢 [宏观爆破点] BDI指数近期飙升 {shipping['30d_trend_pct']:.2%}！航运周期反转，建议长线潜伏【港口航运/物流】。")
            
        # 2. 扫描核心大宗商品 (铜、金)
        copper = self.get_commodity_cycle("CU0", "沪铜")
        if copper and copper['is_booming']:
            print(f"⚡ [宏观爆破点] 铜价近期强势上涨 {copper['60d_trend_pct']:.2%}！建议长线潜伏【有色金属/铜矿资源】。")
            
        gold = self.get_commodity_cycle("AU0", "沪金")
        if gold and gold['is_booming']:
            print(f"👑 [避险爆破点] 金价飙升 {gold['60d_trend_pct']:.2%}！建议潜伏【黄金概念】。")
            
        # 3. 扫描研报共振 (戴维斯双击候选人)
        consensus = self.get_research_consensus_stocks(top_n=20)
        if not consensus.empty:
            print("\n📈 [戴维斯双击储备池] 以下标的获得机构密集覆盖，且明后年预期利润大幅上调：")
            for _, row in consensus.iterrows():
                print(f"   - {row['名称']} ({row['代码']}): 研报覆盖 {int(row['研报数'])} 篇 | 预期增速 {row['预期增速']:.2%}")
                
        return {
            'shipping': shipping,
            'consensus_stocks': consensus['代码'].tolist() if not consensus.empty else []
        }

if __name__ == "__main__":
    engine = MacroCycleEngine()
    engine.analyze_macro_environment()
