import sys
import os

# 彻底屏蔽 Mac 系统级代理与终端环境变量代理，实现“局部直连”
os.environ['NO_PROXY'] = '*'
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    os.environ.pop(proxy_var, None)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.universe_screener import UniverseScreener
from src.bullwhip_engine import BullwhipEngine

if __name__ == "__main__":
    print("1. 获取高管大额回购抢筹名单...")
    bullwhip = BullwhipEngine()
    buybacks = bullwhip.scan_insider_buybacks()
    print(f"回购名单: {buybacks}")
    
    print("\n2. 执行全市场 RPS 过滤 (过滤掉弱势股)...")
    screener = UniverseScreener()
    core_universe = screener.filter_universe()
    
    if not core_universe:
        print("致命错误: RPS 过滤熔断！")
        sys.exit(1)
        
    core_symbols = [item['名称'] for item in core_universe]
    
    print("\n3. 交叉比对: 哪些回购标的具有顶级 RPS (大资金真的在抢)?")
    valid_targets = [name for name in buybacks if name in core_symbols]
    print(f"最终过审名单 (RPS>90 + 巨额回购): {valid_targets}")
    
    # 打印这些股票的代码以便进一步生成报告
    for name in valid_targets:
        code = next(item['代码'] for item in core_universe if item['名称'] == name)
        print(f"  -> {name} ({code})")
