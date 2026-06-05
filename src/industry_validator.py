import os
import json
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

POOL_FILE = "validated_sectors.json"

class IndustryValidator:
    def __init__(self):
        self.pool_file = POOL_FILE
        self.active_sectors = self._load_pool()

    def _load_pool(self):
        if os.path.exists(self.pool_file):
            with open(self.pool_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_pool(self):
        with open(self.pool_file, 'w', encoding='utf-8') as f:
            json.dump(self.active_sectors, f, ensure_ascii=False, indent=4)

    def scan_broker_reports(self):
        """
        第一步：扫描全市场最新研报，提取被密集覆盖的行业
        """
        print("🔍 正在扫描东方财富全市场研报...")
        try:
            # 获取最新研报
            df = ak.stock_research_report_em()
            # 根据行业类别进行词频统计或分组 (具体逻辑后续对接大模型进一步提纯)
            print(f"✅ 成功抓取最新 {len(df)} 份研报。")
            return df
        except Exception as e:
            print(f"❌ 研报抓取失败: {e}")
            return None

    def validate_macro_data(self, sector_name):
        """
        第二步：宏观数据打假验证 (防券商忽悠)
        根据行业名称映射底层的真实宏观数据指标。
        """
        print(f"📊 正在验证 {sector_name} 的底层宏观数据...")
        is_validated = False
        reason = ""
        
        # 示例逻辑：航运板块验证
        if "航运" in sector_name or "造船" in sector_name:
            try:
                bdi_df = ak.macro_shipping_bdi()
                # 提取最近数据进行环比/同比判断
                latest_bdi = float(bdi_df.iloc[-1]['最新值'])
                prev_bdi = float(bdi_df.iloc[-20]['最新值']) # 近一个月前
                if latest_bdi > prev_bdi * 1.05: # 上涨超过5%
                    is_validated = True
                    reason = f"BDI指数近一个月强势上涨 (最新: {latest_bdi}, 前值: {prev_bdi})"
                else:
                    reason = f"BDI运价未见5%以上涨幅 (最新: {latest_bdi}, 前值: {prev_bdi})"
            except Exception as e:
                reason = f"BDI数据获取失败: {e}"

        # 示例逻辑：大宗商品验证 (如：有色、煤炭)
        # TODO: 接入COMEX期货、LME数据
        
        return is_validated, reason

    def update_dynamic_pool(self, new_sector, reason):
        """
        动态入池
        """
        self.active_sectors[new_sector] = {
            "entered_at": datetime.now().strftime("%Y-%m-%d"),
            "last_validated": datetime.now().strftime("%Y-%m-%d"),
            "reason": reason
        }
        self._save_pool()
        print(f"🌟 新增入池: {new_sector} ({reason})")

    def run_eviction_check(self):
        """
        第三步：动态淘汰机制 (Macro Deterioration & Time Decay)
        """
        print("🧹 正在执行动态池末位淘汰审查...")
        to_remove = []
        current_date = datetime.now()
        
        for sector, info in self.active_sectors.items():
            entered_at = datetime.strptime(info["entered_at"], "%Y-%m-%d")
            # 1. 时效衰减剔除 (Time Decay)：如果入池超过 90 天
            if (current_date - entered_at).days > 90:
                print(f"❌ 剔除 {sector}: 入池时间过长，题材热度已衰减。")
                to_remove.append(sector)
                continue
                
            # 2. 宏观恶化审查 (Macro Deterioration)
            is_valid, reason = self.validate_macro_data(sector)
            if not is_valid:
                print(f"❌ 剔除 {sector}: 宏观数据已恶化被证伪 ({reason})。")
                to_remove.append(sector)
                
        for r in to_remove:
            del self.active_sectors[r]
            
        if to_remove:
            self._save_pool()
            print(f"🗑️ 共剔除 {len(to_remove)} 个过期/被证伪的行业。")
        else:
            print("✅ 现有行业池逻辑健康，无淘汰。")

if __name__ == "__main__":
    validator = IndustryValidator()
    # 测试打假逻辑
    is_valid, reason = validator.validate_macro_data("航运")
    print(f"测试航运验证结果: {is_valid}, 原因: {reason}")
