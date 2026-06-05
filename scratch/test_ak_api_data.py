import akshare as ak

print("Testing macro_shipping_bdi...")
try:
    df = ak.macro_shipping_bdi()
    print(df.tail(3))
except Exception as e:
    print("Error:", e)

print("\nTesting macro_china_freight_index...")
try:
    df = ak.macro_china_freight_index()
    print(df.tail(3))
except Exception as e:
    print("Error:", e)

print("\nTesting stock_profit_forecast_em...")
try:
    df = ak.stock_profit_forecast_em()
    print(df.head(3))
except Exception as e:
    print("Error:", e)
    
print("\nTesting stock_research_report_em...")
try:
    df = ak.stock_research_report_em()
    print(df.head(3))
except Exception as e:
    print("Error:", e)
