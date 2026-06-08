import time
from .universe_screener import UniverseScreener
from .quant_radar import QuantRadar
from .brain_nlp import NLPBrain
from .capital_flow_voter import CapitalFlowVoter
from .execution_engine import ExecutionEngine

def run_pipeline():
    print("=======================================================")
    print("🌊 AlphaTide V5.0: The Dual-Brain Momentum Sniper")
    print("=======================================================")
    
    # 1. Universe Screener
    screener = UniverseScreener()
    core_symbols = screener.filter_universe()
    
    if not core_symbols:
        print("[System] 🛑 Universe empty. Aborting pipeline.")
        return
        
    # 2. Quant Radar (The Objective Brain)
    radar = QuantRadar()
    # We pass the cleaned core symbols to the radar
    accumulation_pool = radar.scan_accumulation(symbols=core_symbols)
    
    if not accumulation_pool:
        print("[System] 🛑 No institutional accumulation detected today. Cash is king.")
        return
        
    # 3. AI Auditor (The Subjective Brain)
    auditor = NLPBrain()
    # The AI reads the news and VETOS stocks in the pool that lack fundamental logic
    approved_pool = auditor.update_watchlist(quant_pool=accumulation_pool)
    
    if not approved_pool:
        print("[System] 🛑 AI vetoed all accumulation targets. Staying flat.")
        return
        
    # 4. Capital Flow Voter & Execution
    # Since V5 decoupling is purely at the generation layer, we pass the 
    # approved list to the legacy V4.5 voter and execution engine.
    voter = CapitalFlowVoter()
    voter.run()
    
    engine = ExecutionEngine()
    engine.execute_trades()
    
    print("\\n✅ V5.0 Pipeline Execution Complete.")

if __name__ == "__main__":
    run_pipeline()
