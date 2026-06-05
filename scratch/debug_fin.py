import sys
import os
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_fetcher import fetch_a_stock_financials

fin = fetch_a_stock_financials("600519")
if fin is not None:
    row = fin[fin['指标'].str.contains('归母净利润', na=False, regex=False)]
    print(row)
