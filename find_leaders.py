import os

# 彻底屏蔽 Mac 系统级代理与终端环境变量代理，实现“局部直连”
os.environ['NO_PROXY'] = '*'
for proxy_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
    os.environ.pop(proxy_var, None)
from src.universe_screener import UniverseScreener
from src.bullwhip_engine import BullwhipEngine

screener = UniverseScreener()
core_universe = screener.filter_universe()

print(f"\n--- RPS TOP 10% 标的 ({len(core_universe)} 只) ---")
# 打印前 50 只让 AI 看一眼
print([item['名称'] for item in core_universe[:50]])

bullwhip = BullwhipEngine()
commodities = bullwhip.scan_spot_commodities()
upgrades = bullwhip.scan_analyst_upgrades()
buybacks = bullwhip.scan_insider_buybacks()
print("\n--- 交叉验证 ---")
print("commodities:", commodities)
print("upgrades:", upgrades)
print("buybacks:", buybacks)
