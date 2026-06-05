import akshare as ak

print("Testing HK Sina...")
try:
    df_hk = ak.stock_hk_daily(symbol="00700")
    print(df_hk.tail(3))
except Exception as e:
    print("Error Sina:", e)
