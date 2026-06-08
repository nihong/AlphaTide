import pandas as pd
from src.data_fetcher import fetch_us_index, fetch_fx_spot

class MacroEngine:
    def __init__(self):
        pass

    def get_global_status(self):
        """
        获取全球宏观环境状态
        """
        status = {
            'nasdaq': self._analyze_index(".IXIC", "纳斯达克"),
            'sox': self._analyze_index(".SOX", "费城半导体"),
            'usdcny': self._analyze_fx(),
        }
        
        # 综合判定宏观“天气”
        score = 0
        if status['nasdaq']['trend'] == 'UP': score += 30
        if status['sox']['trend'] == 'UP': score += 30
        if status['usdcny']['trend'] == 'STABLE': score += 40
        elif status['usdcny']['trend'] == 'STRONG_RMB': score += 50
        
        status['overall_score'] = score # 0-110
        if score >= 80: status['weather'] = "晴朗 (全球共振向好)"
        elif score >= 50: status['weather'] = "多云 (局部机会，警惕波动)"
        else: status['weather'] = "雷雨 (外盘承压，建议防御)"
        
        return status

    def _analyze_index(self, symbol, name):
        df = fetch_us_index(symbol)
        if df is None or df.empty: return {'name': name, 'trend': 'UNKNOWN', 'desc': '数据获取失败'}
        
        latest_close = df.iloc[-1]['close']
        ma20 = df.iloc[-20:]['close'].mean()
        change = ((latest_close - df.iloc[-2]['close']) / df.iloc[-2]['close']) * 100
        
        trend = "UP" if latest_close > ma20 else "DOWN"
        return {
            'name': name,
            'price': round(latest_close, 2),
            'change': round(change, 2),
            'trend': trend,
            'desc': f"{'均线上方' if trend == 'UP' else '均线下方'} (昨收 {round(change, 2)}%)"
        }

    def _analyze_fx(self):
        df = fetch_fx_spot()
        if df is None or df.empty: return {'name': '美元/人民币', 'trend': 'UNKNOWN', 'desc': '数据获取失败'}
        
        try:
            # 查找 USD/CNY
            row = df[df['货币对'] == 'USD/CNY']
            if row.empty: return {'name': '美元/人民币', 'trend': 'UNKNOWN', 'desc': '找不到汇率对'}
            
            rate = float(row.iloc[0]['买报价'])
            # 简单逻辑：汇率 > 7.2 且在上涨通常对 A/HK 不利
            if rate > 7.3:
                return {'name': '美元/人民币', 'price': rate, 'trend': 'WEAK_RMB', 'desc': '人民币走势极弱 (汇率>7.3)'}
            elif rate < 7.1:
                return {'name': '美元/人民币', 'price': rate, 'trend': 'STRONG_RMB', 'desc': '人民币走势强劲 (汇率<7.1)'}
            else:
                return {'name': '美元/人民币', 'price': rate, 'trend': 'STABLE', 'desc': '汇率相对平稳'}
        except:
            return {'name': '美元/人民币', 'trend': 'UNKNOWN', 'desc': '解析失败'}

if __name__ == "__main__":
    engine = MacroEngine()
    print(engine.get_global_status())
