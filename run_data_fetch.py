import sys
import os
import logging
from src.industry_validator import IndustryValidator
from src.bullwhip_engine import BullwhipEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bullwhip = BullwhipEngine()

commodities = bullwhip.scan_spot_commodities()
structural_reports = bullwhip.scan_structural_industry_reports()
analyst_upgrades = bullwhip.scan_analyst_upgrades()
insider_buybacks = bullwhip.scan_insider_buybacks()

print("\n--- RAW DATA ---")
print("1. 现货暴涨品种：", commodities)
print("2. 深度产业研报：", structural_reports)
print("3. 机构盈利上调：", analyst_upgrades)
print("4. 高管资金抢筹：", insider_buybacks)
