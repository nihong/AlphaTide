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
    大盘环境风控锁 V8.1 (双轨广度防御系统)
    解决沪深300失真问题：同时监控【沪深300(大盘价值)】与【中证1000(中小盘成长)】。
    只要有任意一个指数稳在 20日均线之上，就判定存在“结构性多头环境”，允许机器运作。
    只有当两个指数全部跌破 20日均线时，才确认发生全市场系统性股灾，全面断电熔断。
    """
    logger.info("🛡️ [风控中心] 正在执行系统性流动性排查 (启动沪深300+中证1000双轨防御)...")
    try:
        import akshare as ak
        # 拉取沪深300 (代表大盘权重)
        df_300 = ak.stock_zh_index_daily_em(symbol="sh000300")
        # 拉取中证1000 (代表中小盘科技与成长)
        df_1000 = ak.stock_zh_index_daily_em(symbol="sh000852")
        
        if df_300.empty or df_1000.empty or len(df_300) < 20 or len(df_1000) < 20:
            return True
            
        c_300 = df_300['close'].iloc[-1]
        ma_300 = df_300['close'].iloc[-20:].mean()
        
        c_1000 = df_1000['close'].iloc[-1]
        ma_1000 = df_1000['close'].iloc[-20:].mean()
        
        is_300_safe = c_300 >= ma_300
        is_1000_safe = c_1000 >= ma_1000
        
        if not is_300_safe and not is_1000_safe:
            logger.error(f"☠️ [SYSTEM HALT] 沪深300({c_300:.2f} < {ma_300:.2f}) 与 中证1000({c_1000:.2f} < {ma_1000:.2f}) 双双破位！")
            logger.error("🛑 大盘权重与中小盘科技全线崩塌，确认发生系统性股灾。AlphaTide 强制熔断休眠！")
            return False
            
        if is_300_safe and not is_1000_safe:
            logger.info("⚠️ [结构性行情] 沪深300安全，但中小盘走弱。系统放行，切换为【权重防御模式】。")
        elif not is_300_safe and is_1000_safe:
            logger.info("🔥 [结构性牛市] 沪深300走弱，但中证1000活跃！无视指数失真，系统放行，开启【科技成长狙击模式】！")
        else:
            logger.info("✅ [全量牛市] 两大核心指数均稳居生命线之上，市场广度极佳！")
            
        return True
    except Exception as e:
        logger.warning(f"⚠️ 无法获取大盘数据 (降级跳过宏观风控锁)。异常: {e}")
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
    
    # 3.1 获取全市场强势股底池 (RPS > 90)
    screener = UniverseScreener()
    core_universe = screener.filter_universe()
    
    if not core_universe:
        logger.warning("🛑 当前市场极度恶劣，无任何满足 RPS 强势条件的股票，空仓等待。")
        return

    # 3.2 使用 AI 将牛鞭效应赛道映射到具体的 A 股强势标的
    logger.info("🤖 正在调用 Antigravity AI 映射核心标的...")
    target_symbols = bullwhip.ai.map_sectors_to_symbols(bottleneck_sectors, core_universe)
    
    if not target_symbols:
        logger.warning("🛑 强势股池中未发现符合牛鞭效应赛道的公司。绝不将就！")
        return
        
    logger.info(f"🎯 AI 成功映射赛道核心标的: {target_symbols}")
    
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
