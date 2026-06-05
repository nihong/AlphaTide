import os
os.environ['NO_PROXY'] = '*'

import akshare as ak
import pandas as pd

import time
import random
import pickle
import requests
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

    # 极速模式：新浪和腾讯极少封锁，将停顿缩减到极小的象征性防刷即可
    time.sleep(0.1)
    
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


def fetch_a_stock_hist(symbol: str, period: str = "daily", start_date: str = "19700101", end_date: str = "20500101", adjust: str = "qfq"):
    """
    获取A股历史K线数据，带有三源随机负载均衡 (Load Balancing)：
    随机打乱 [东方财富, 新浪, 腾讯] 的请求顺序。
    这样每个数据源只承担 33% 的并发压力，极大降低被单一平台封禁的概率。
    """
    # 针对 ETF 基金 (如 510300) 的特殊处理
    if symbol.startswith('51') or symbol.startswith('15'):
        try:
            prefix = "sh" if symbol.startswith("51") else "sz"
            sina_symbol = f"{prefix}{symbol}"
            df_sina = ak.fund_etf_hist_sina(symbol=sina_symbol)
            if df_sina is not None and not df_sina.empty:
                # 过滤日期
                df_sina['date'] = pd.to_datetime(df_sina['date']).dt.strftime('%Y%m%d')
                df_sina = df_sina[(df_sina['date'] >= start_date) & (df_sina['date'] <= end_date)]
                df_sina['date'] = pd.to_datetime(df_sina['date']).dt.strftime('%Y-%m-%d')
                rename_map = {'date': '日期', 'open': '开盘', 'close': '收盘', 'high': '最高', 'low': '最低', 'volume': '成交量', 'amount': '成交额'}
                return df_sina.rename(columns=rename_map)
        except Exception as e:
            print(f"⚠️ ETF 历史数据获取失败 ({symbol}): {e}")
            return pd.DataFrame()

    sources = ['eastmoney', 'sina', 'tencent']
    random.shuffle(sources)
    
    for source in sources:
        try:
            if source == 'eastmoney':
                df = ak.stock_zh_a_hist(symbol=symbol, period=period, start_date=start_date, end_date=end_date, adjust=adjust)
                if df is not None and not df.empty:
                    return df
            
            elif source == 'sina':
                prefix = "sh" if symbol.startswith("6") else "sz"
                sina_symbol = f"{prefix}{symbol}"
                df_sina = ak.stock_zh_a_daily(symbol=sina_symbol, start_date=start_date, end_date=end_date, adjust=adjust)
                if df_sina is not None and not df_sina.empty:
                    rename_map = {'date': '日期', 'open': '开盘', 'close': '收盘', 'high': '最高', 'low': '最低', 'volume': '成交量', 'amount': '成交额'}
                    df_mapped = df_sina.rename(columns=rename_map)
                    if '日期' in df_mapped.columns: df_mapped['日期'] = df_mapped['日期'].astype(str)
                    return df_mapped
            
            elif source == 'tencent':
                prefix = "sh" if symbol.startswith("6") else "sz"
                tx_symbol = f"{prefix}{symbol}"
                df_tx = ak.stock_zh_a_hist_tx(symbol=tx_symbol, start_date=start_date, end_date=end_date, adjust=adjust)
                if df_tx is not None and not df_tx.empty:
                    rename_map = {'date': '日期', 'open': '开盘', 'close': '收盘', 'high': '最高', 'low': '最低', 'amount': '成交额'}
                    df_mapped = df_tx.rename(columns=rename_map)
                    if '成交量' not in df_mapped.columns: df_mapped['成交量'] = df_mapped['成交额'] / df_mapped['收盘'] * 100
                    if '日期' in df_mapped.columns: df_mapped['日期'] = df_mapped['日期'].astype(str)
                    return df_mapped
                    
        except Exception as e:
            print(f"⚠️ {source} 接口获取失败 ({symbol}): {e}，尝试下一个数据源...")
            time.sleep(1) # 失败后稍微休息一下再请求下一个

    print(f"❌ 所有历史接口(东财/新浪/腾讯)均获取彻底失败 ({symbol})")
    return pd.DataFrame()


def fetch_a_stock_hist_cached(symbol: str, period: str = "daily", start_date: str = "19700101", end_date: str = "20500101", adjust: str = "qfq", expiry_hours: int = 4):
    """获取A股历史K线，带有缓存和双源容错"""
    cache_key = f"hist_a_{symbol}_{adjust}_{period}"
    return fetch_with_cache(
        cache_key,
        fetch_a_stock_hist,
        expiry_hours=expiry_hours,
        symbol=symbol,
        period=period,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust
    )

def _fetch_hk_stock_hist(symbol: str):
    df = ak.stock_hk_daily(symbol=symbol)
    if df is not None and not df.empty:
        rename_map = {'date': '日期', 'open': '开盘', 'close': '收盘', 'high': '最高', 'low': '最低', 'volume': '成交量', 'amount': '成交额'}
        df = df.rename(columns=rename_map)
        if '日期' in df.columns: df['日期'] = df['日期'].astype(str)
        return df
    return pd.DataFrame()

def fetch_hk_stock_hist_cached(symbol: str, expiry_hours: int = 4):
    """获取港股历史K线，带有缓存"""
    cache_key = f"hist_hk_{symbol}"
    return fetch_with_cache(
        cache_key,
        _fetch_hk_stock_hist,
        expiry_hours=expiry_hours,
        symbol=symbol
    )


def fetch_a_stock_financials(symbol: str):
    """获取A股财报摘要，带24小时缓存"""
    return fetch_with_cache(f"fin_a_{symbol}", ak.stock_financial_abstract, expiry_hours=24, symbol=symbol)

def fetch_a_valuation_history(symbol: str):
    """获取A股估值历史(PE/PB)，带24小时缓存"""
    return fetch_with_cache(f"val_a_{symbol}", ak.stock_a_lg_indicator, expiry_hours=24, symbol=symbol)

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

def fetch_executive_holdings(pages: int = 5):
    """
    获取高管增持/减持明细数据 (东方财富)
    返回包含多页数据的 DataFrame
    带4小时缓存
    """
    def _fetch():
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        all_data = []
        for page in range(1, pages + 1):
            params = {
                "sortColumns": "CHANGE_DATE,SECURITY_CODE",
                "sortTypes": "-1,-1",
                "pageSize": "500",
                "pageNumber": str(page),
                "reportName": "RPT_EXECUTIVE_HOLD_DETAILS",
                "columns": "ALL",
                "source": "WEB",
                "client": "WEB",
            }
            try:
                r = requests.get(url, params=params, headers=get_headers(), timeout=10)
                data_json = r.json()
                if data_json and data_json.get("result") and data_json["result"].get("data"):
                    all_data.extend(data_json["result"]["data"])
                else:
                    break
            except Exception as e:
                print(f"Error fetching executive holdings page {page}: {e}")
                break
        return pd.DataFrame(all_data) if all_data else pd.DataFrame()
        
    return fetch_with_cache("executive_holdings", _fetch, expiry_hours=4)

def fetch_stock_repurchases():
    """
    获取股份回购数据 (东方财富)
    带24小时缓存
    """
    return fetch_with_cache("stock_repurchases", ak.stock_repurchase_em, expiry_hours=24)

def fetch_latest_zcfz():
    """
    获取最新一期的资产负债表(全市场)，用于筛选合同负债(预收账款)等。
    带24小时缓存。
    """
    def _fetch():
        # 尝试获取最近几个季度的资产负债表
        now = datetime.now()
        quarters = []
        year = now.year
        for _ in range(4): # 尝试过去4个季度
            for month, day in [(12, 31), (9, 30), (6, 30), (3, 31)]:
                if now.year == year and now.month < month:
                    continue
                quarters.append(f"{year}{month:02d}{day}")
            year -= 1
        
        for q in quarters[:4]: # 尝试最近4个可能存在的财报日期
            try:
                df = ak.stock_zcfz_em(date=q)
                if df is not None and not df.empty:
                    print(f"Fetched balance sheet data for {q}")
                    return df
            except Exception:
                pass
        return pd.DataFrame()

    return fetch_with_cache("latest_zcfz", _fetch, expiry_hours=24)

if __name__ == "__main__":
    # Test HK
    print("Testing HK data fetch for Tencent (00700)...")
    hk_data = fetch_hk_stock_financials("00700")
    if hk_data is not None:
        print(hk_data.head())
