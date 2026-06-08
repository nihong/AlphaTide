import argparse
from scripts.evaluate_strategy import StrategyEvaluator
from src.market_monitor import MarketMonitor
from src.ai_analyst import AIAnalyst

# Mock LLM to avoid spamming the API and save money/time during batch backtest report generation
def mock_analyze(self, prompt): return "【Backtest Mock Analysis】AI 分析已跳过，主要依赖量价、基本面和相对强度指标选股。"
AIAnalyst.analyze_with_llm = mock_analyze

def generate_reports(market, start_idx, end_idx):
    evaluator = StrategyEvaluator()
    dates = evaluator.get_trade_dates(30)
    
    # Slice the dates based on indices
    chunk_dates = dates[start_idx:end_idx]
    print(f"Generating reports for {market} market for dates: {chunk_dates}")
    
    monitor = MarketMonitor()
    for d in chunk_dates:
        print(f"Generating for {market} on {d}...")
        monitor.run_daily_scan(target_date=d, market=market)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", type=str, choices=["A", "HK"], required=True)
    parser.add_argument("--start", type=int, required=True)
    parser.add_argument("--end", type=int, required=True)
    args = parser.parse_args()
    generate_reports(args.market, args.start, args.end)
