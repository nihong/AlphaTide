import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.industry_validator import IndustryValidator
from src.bullwhip_engine import BullwhipEngine
from src.universe_screener import UniverseScreener

# 配置终端与日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_macro_environment() -> bool:
    """
    大盘环境风控锁 (Macro Market Risk Lock) - 抵御系统性流动性危机
    逻辑：当沪深300指数跌破 20 日均线时，代表大盘进入主跌浪或流动性枯竭。
    此时任何个股的 VCP 形态都有极大概率被大盘恐慌盘砸穿，系统必须强行熔断休眠。
    """
    logger.info("🛡️ [风控中心] 正在执行系统性流动性危机排查 (沪深300指数)...")
    try:
        import akshare as ak
        df = ak.stock_zh_index_daily_em(symbol="sh000300")
        if df.empty or len(df) < 20:
            return True
            
        current_close = df['close'].iloc[-1]
        ma_20 = df['close'].iloc[-20:].mean()
        
        if current_close < ma_20:
            logger.error(f"☠️ [SYSTEM HALT] 沪深300当前点位 ({current_close:.2f}) 跌破 20日生命线 ({ma_20:.2f})！")
            logger.error("🛑 系统判定当前存在【系统性流动性危机】。覆巢之下无完卵，AlphaTide V8.0 强制熔断，停止一切多头买入操作！")
            return False
            
        logger.info(f"✅ [大盘风控通过] 沪深300 ({current_close:.2f}) 稳居 20日均线 ({ma_20:.2f}) 之上，未见流动性衰竭。")
        return True
    except Exception as e:
        logger.warning(f"⚠️ 无法获取大盘数据 (通常因本地 VPN 导致)。暂且降级跳过宏观风控锁。异常: {e}")
        return True

def run_bullwhip_pipeline():
    # 【新增：大盘熔断锁】
    if not check_macro_environment():
        return

    print("==================================================")
    print(f"🌊 ALPHATIDE V8.0 (Super Early Radar) - {datetime.now().strftime('%Y-%m-%d')}")
    print("==================================================")
    
    validator = IndustryValidator()
    bullwhip = BullwhipEngine()

    # 第一步：穿透获取全市场最新研报 (获取近 24 小时的深度研报)
    logger.info("正在执行 V8.0 第一步：穿透提取东方财富全市场研报库...")
    try:
        latest_reports = validator.scan_broker_reports() 
    except Exception as e:
        logger.error(f"研报提取失败: {e}")
        latest_reports = []

    # 第二步：利用大模型执行“多源三角验证”
    logger.info("正在执行 V8.0 第二步：启动多源交叉验证提取卡脖子环节...")
    bottleneck_sectors = bullwhip.scan_bottleneck_industries(latest_reports)
    
    if not bottleneck_sectors:
        logger.warning("🛑 暂未发现具有『牛鞭效应』与『极致供需错配』的赛道。严格空仓，绝不交易次优级资产。")
        return
        
    logger.info(f"🔥 锁定多源印证赛道: {bottleneck_sectors}")

    # 第三步：在赛道中寻找“第一基底龙头”
    logger.info("正在执行 V8.0 第三步：在目标赛道中锁定量价与财务共振的绝对龙头...")
    # 系统根据赛道自动映射 A 股标的 (此处为映射后的代码，包含被动元件与液冷)
    target_symbols = ["sz300408", "sz000636", "sz002837"] # 三环集团, 风华高科, 英维克
    
    apex_predators = bullwhip.screen_apex_predators(target_symbols)
    
    if not apex_predators:
        logger.warning("🛑 赛道中未发现满足量价动量且 VCP 波动率收缩完美的龙头，继续潜伏等待右侧突破...")
        return
        
    for predator in apex_predators:
        logger.info(f"✅ 锁定【早期龙头】: {predator['symbol']} | 现价: {predator.get('current_price', 'N/A')} | 逻辑: {predator['reason']} | 近期动量: {predator['momentum']}%")
        
    # 第四步：离场防线计算 (演示)
    logger.info("正在执行 V7.0 第四步：为持仓股票计算 ATR 吊灯止损位与 20 日均线防线...")
    for predator in apex_predators:
        # 假设买入价为当前价，最高价也为当前价
        should_exit = bullwhip.evaluate_exit(predator['symbol'], entry_price=100.0, highest_price=100.0)
        if should_exit:
            logger.warning(f"💥 {predator['symbol']} 触发纪律斩仓线！牛鞭效应极大概率见顶，立即清仓！")
        else:
            logger.info(f"🛡️ {predator['symbol']} 尚未触发斩仓线，继续持有让利润奔跑。")

    print("==================================================")
    print("🏁 ALPHATIDE V7.0 - PIPELINE COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_bullwhip_pipeline()
