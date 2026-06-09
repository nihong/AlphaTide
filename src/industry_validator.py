import os
import json
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from src.data_fetcher import get_dynamic_hot_symbols

POOL_FILE = "validated_sectors.json"

class IndustryValidator:
    def __init__(self):
        self.pool_file = POOL_FILE
        self.cache_file = ".cache/parsed_reports_cache.json"
        self.active_sectors = self._load_pool()
        self.parsed_reports = self._load_cache()
        
        # 👑 核心白名单：匹配东方财富免费数据源中研究实力最强的券商（注：中信/中金等通常不公开发布至该免费接口）
        self.TOP_TIER_INSTITUTIONS = [
            "国信证券", "国金证券", "东吴证券", "民生证券", 
            "中银证券", "开源证券", "华安证券", "信达证券", 
            "西南证券", "太平洋", "东兴证券", "山西证券"
        ]

    def _load_pool(self):
        if os.path.exists(self.pool_file):
            with open(self.pool_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _load_cache(self):
        """加载已读研报的缓存，防止重复读取"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.parsed_reports), f, ensure_ascii=False, indent=4)

    def _save_pool(self):
        with open(self.pool_file, 'w', encoding='utf-8') as f:
            json.dump(self.active_sectors, f, ensure_ascii=False, indent=4)

    def scan_broker_reports(self, target_symbols=None, target_date=None):
        """
        全息研报雷达 (极速版)：
        直接通过东方财富底层 API 抓取全市场最新研报，无需再扫描 5000 只个股。
        执行【白名单过滤】与【去重审查】。
        """
        valid_reports = []
        
        # 处理时间窗口
        end_date = datetime.strptime(target_date, "%Y-%m-%d") if target_date else datetime.now()
        start_date = end_date - timedelta(days=7)
        
        if not target_symbols:
            print(f"🌐 [启动全市场极速雷达] 正在直接拉取全市场最新机构研报 (截止: {end_date.strftime('%Y-%m-%d')})...")
            import requests
            url = "https://reportapi.eastmoney.com/report/list"
            params = {
                "industryCode": "*", "pageSize": "200", "industry": "*",
                "rating": "*", "ratingChange": "*", "beginTime": start_date.strftime("%Y-%m-%d"),
                "endTime": end_date.strftime("%Y-%m-%d"), "pageNo": "1",
                "fields": "", "qType": "0", "orgCode": "", "code": "*",
                "rcode": "", "p": "1", "pageNum": "1", "pageNumber": "1",
            }
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                r = requests.get(url, params=params, headers=headers, timeout=10)
                data = r.json()
                if data and "data" in data and data["data"]:
                    for item in data["data"]:
                        inst = item.get('orgSName')
                        title = item.get('title')
                        stock = item.get('stockName')
                        
                        if inst not in self.TOP_TIER_INSTITUTIONS:
                            continue
                            
                        cache_key = f"{stock}_{inst}_{title}"
                        if cache_key in self.parsed_reports:
                            continue
                            
                        valid_reports.append({
                            'date': item.get('publishDate', '')[:10],
                            'stock': stock,
                            'title': title,
                            'industry': item.get('indvInduName'),
                            'institution': inst,
                            'rating': item.get('emRatingName', '')
                        })
                        self.parsed_reports.add(cache_key)
                else:
                    raise ValueError("API response structural change detected or Empty data.")
            except Exception as e:
                print(f"⚠️ [警告] 极速全市场研报 API 抓取失败或被封禁 ({e})。")
                print("🔄 [容灾机制] 正在自动降级为使用 Akshare 稳定版逐个扫描核心底池...")
                # Fallback to scanning a dynamic/core list of symbols using the stable library
                fallback_symbols = get_dynamic_hot_symbols() if callable(get_dynamic_hot_symbols) else ["sh600519", "sz000858", "sz300750", "sh601899", "sh601088", "sz000333", "sh600900", "sz002475"]
                return self.scan_broker_reports(target_symbols=fallback_symbols, target_date=target_date)
        else:
            print(f"🔍 正在拉取雷达锁定标的的研报 ({len(target_symbols)}只核心龙头)...")
            for sym in target_symbols:
                try:
                    df = ak.stock_research_report_em(symbol=sym)
                    if df is None or df.empty:
                        continue
                        
                    for _, row in df.iterrows():
                        inst = row.get('机构', '')
                        title = row.get('报告名称', '')
                        stock = row.get('股票简称', '')
                        
                        if inst not in self.TOP_TIER_INSTITUTIONS:
                            continue
                            
                        cache_key = f"{stock}_{inst}_{title}"
                        if cache_key in self.parsed_reports:
                            continue
                            
                        valid_reports.append({
                            'date': str(row.get('日期', '')),
                            'stock': stock,
                            'title': title,
                            'industry': row.get('行业', ''),
                            'institution': inst,
                            'rating': row.get('东财评级', '')
                        })
                        self.parsed_reports.add(cache_key)
                except Exception as e:
                    continue
                    
        self._save_cache()
        print(f"✅ 成功提取 {len(valid_reports)} 份【头部券商】全新研报（已剔除低质量/重复项）。")
        return valid_reports

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
