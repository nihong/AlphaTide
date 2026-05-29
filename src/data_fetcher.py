import akshare as ak
import pandas as pd

import os
import time
import random
import pickle
from datetime import datetime, timedelta

def get_headers():
    ua_list = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    return {"User-Agent": random.choice(ua_list)}

def fetch_with_cache(cache_key, fetch_func, expiry_hours=24, **kwargs):
    """带本地缓存的数据抓取函数，防止频繁请求被封"""
    cache_dir = ".cache"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{cache_key}.pkl")

    # 检查缓存是否有效
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            data, timestamp = pickle.load(f)
            if datetime.now() - timestamp < timedelta(hours=expiry_hours):
                return data

    # 随机延迟，模拟真实人类行为
    time.sleep(random.uniform(1.5, 3.5))
    
    # 强制设置代理环境变量（国内数据建议直连）
    os.environ["NO_PROXY"] = "*"
    
    try:
        data = fetch_func(**kwargs)
        if data is not None and not (hasattr(data, 'empty') and data.empty):
            with open(cache_file, 'wb') as f:
                pickle.dump((data, datetime.now()), f)
        return data
    except Exception as e:
        print(f"Fetch Error for {cache_key}: {e}")
        return None

def fetch_market_index(symbol="sh000300"):
    """获取大盘指数数据，带短期缓存(4小时)"""
    return fetch_with_cache(f"index_{symbol}", ak.stock_zh_index_daily, expiry_hours=4, symbol=symbol)

def fetch_hk_market_index(symbol="HSI"):
    """获取港股大盘指数数据(恒生指数)，带短期缓存(4小时)"""
    return fetch_with_cache(f"hk_index_{symbol}", ak.stock_hk_index_daily_sina, expiry_hours=4, symbol=symbol)

def fetch_us_index(symbol=".IXIC"):
    """获取美股指数数据 (.IXIC 纳指, .SOX 半导体)，带短期缓存(4小时)"""
    return fetch_with_cache(f"us_index_{symbol}", ak.index_us_stock_sina, expiry_hours=4, symbol=symbol)

def fetch_fx_spot():
    """获取汇率实时数据，带短期缓存(1小时)"""
    return fetch_with_cache("fx_spot", ak.fx_spot_quote, expiry_hours=1)


def fetch_market_tide():
    """获取行业资金流向数据"""
    return fetch_with_cache("market_tide", ak.stock_sector_fund_flow_rank, expiry_hours=4, indicator="5日")

def fetch_a_stock_financials(symbol: str):
    """获取A股财报摘要，带24小时缓存"""
    return fetch_with_cache(f"fin_a_{symbol}", ak.stock_financial_abstract, expiry_hours=24, symbol=symbol)

def fetch_hk_stock_financials(symbol: str):
    """获取港股财报指标，带24小时缓存"""
    return fetch_with_cache(f"fin_hk_{symbol}", ak.stock_financial_hk_analysis_indicator_em, expiry_hours=24, symbol=symbol)


def get_hk_stock_list():
    """Get all HK stock spots."""
    try:
        return ak.stock_hk_spot_em()
    except Exception as e:
        print(f"Error fetching HK stock list: {e}")
        return None

if __name__ == "__main__":
    # Test HK
    print("Testing HK data fetch for Tencent (00700)...")
    hk_data = fetch_hk_stock_financials("00700")
    if hk_data is not None:
        print(hk_data.head())
