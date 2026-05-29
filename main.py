import argparse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.data_fetcher import fetch_a_stock_financials, fetch_hk_stock_financials
from src.screener import Screener
from src.ai_analyst import AIAnalyst

def main():
    parser = argparse.ArgumentParser(description="AlphaTide: AI Investment Pipeline")
    parser.add_argument("--market", type=str, default="A", choices=["A", "HK"], help="Market to screen (A or HK)")
    parser.add_argument("--symbol", type=str, help="Specific stock symbol to analyze")
    parser.add_argument("--auto", action="store_true", help="Run the full automated daily monitoring pipeline")
    parser.add_argument("--date", type=str, help="Target date for historical backtesting (e.g., '2024-03-01')")
    args = parser.parse_args()

    if args.auto:
        from src.market_monitor import MarketMonitor
        monitor = MarketMonitor()
        monitor.run_daily_scan(target_date=args.date, market=args.market)
        return

    market = args.market
    symbol = args.symbol
    
    # Default symbols for testing if none provided
    if not symbol:
        symbol = "600519" if market == "A" else "00700"

    print(f"🚀 Starting analysis for {symbol} in {market} market...")

    # 1. Fetch Data
    if market == "A":
        data = fetch_a_stock_financials(symbol)
    else:
        data = fetch_hk_stock_financials(symbol)

    if data is None or data.empty:
        print("❌ Error: Could not fetch data.")
        return

    # 2. Screen
    screener = Screener()
    if market == "A":
        pass_status = screener.screen_a_share(data)
    else:
        pass_status = screener.screen_hk_share(data)

    print(f"📊 Screening Result: {pass_status}")

    # 3. AI Summary
    analyst = AIAnalyst()
    report_prompt = analyst.generate_report_prompt(symbol, market, data, pass_status)
    
    print("\n--- AI Analysis Prompt Generated ---")
    print(report_prompt)
    print("-------------------------------------")
    print("✅ Pipeline complete. You can now feed the above prompt to your preferred AI.")

if __name__ == "__main__":
    main()
