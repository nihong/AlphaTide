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

def run_bullwhip_pipeline():
    print("==================================================")
    print(f"🌊 ALPHATIDE V7.0 (BULLWHIP & BOTTLENECK) - {datetime.now().strftime('%Y-%m-%d')}")
    print("==================================================")
    
    validator = IndustryValidator()
    bullwhip = BullwhipEngine()
    universe = UniverseScreener()

    # 第一步：穿透获取全市场最新研报 (获取近 24 小时的深度研报)
    logger.info("正在执行 V7.0 第一步：穿透提取东方财富全市场研报库...")
    try:
        # 这里假设 validator 有一个方法能快速扫出最新的研报
        latest_reports = validator.scan_broker_reports(max_pages=2) 
    except Exception as e:
        logger.error(f"研报提取失败: {e}")
        latest_reports = []

    # 第二步：利用大模型执行“牛鞭效应”探测
    logger.info("正在执行 V7.0 第二步：大模型分析供需错配与卡脖子环节...")
    bottleneck_sectors = bullwhip.scan_bottleneck_industries(latest_reports)
    
    if not bottleneck_sectors:
        logger.warning("🛑 暂未发现具有『牛鞭效应』与『极致供需错配』的赛道。严格空仓，绝不交易次优级资产。")
        return
        
    logger.info(f"🔥 锁定卡脖子赛道: {bottleneck_sectors}")

    # 第三步：在赛道中寻找“绝对龙头”（RPS + 毛利率）
    logger.info("正在执行 V7.0 第三步：在目标赛道中锁定具有定价权的绝对龙头...")
    # 假设有个映射函数把行业转为股票代码列表，这里作为演示
    target_symbols = ["sh603688", "sz300308", "sz002466"] # 石英股份, 中际旭创, 天齐锂业 (演示用)
    
    apex_predators = bullwhip.screen_apex_predators(target_symbols)
    
    if not apex_predators:
        logger.warning("🛑 赛道中未发现满足 RPS 动量且 VCP 波动率收缩完美的龙头，继续潜伏等待右侧突破...")
        return
        
    for predator in apex_predators:
        logger.info(f"✅ 锁定【瓶颈龙头】: {predator['symbol']} | 逻辑: {predator['reason']} | 近期动量: {predator['momentum']:.2%}")
        
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
