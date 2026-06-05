import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from brain_nlp import NLPBrain
from falsification_filter import FalsificationFilter
from capital_flow_voter import CapitalFlowVoter
from execution_engine import ExecutionEngine

def run_pipeline():
    print("==================================================")
    print("🌊 ALPHATIDE V4.0 - PIPELINE INITIATED")
    print("==================================================")
    
    # 1. AI Brain (Idea Generation)
    brain = NLPBrain()
    ideas = brain.update_watchlist()
    
    # 2. Truth Filter (Alternative Data)
    filter_engine = FalsificationFilter()
    survivors = filter_engine.filter_watchlist()
    
    if not survivors:
        print("\\n[Pipeline] 🛑 All ideas killed by Truth Filter. Macro environment hostile. Aborting day.")
        return
        
    # 3. Capital Flow Voter (Smart Money Confirmation)
    voter = CapitalFlowVoter()
    final_targets = voter.vote(survivors)
    
    # 4. Execution (Buy/Sell/Stop-loss)
    execution = ExecutionEngine()
    execution.execute_trades(final_targets)
    
    print("==================================================")
    print("🏁 ALPHATIDE V4.0 - PIPELINE COMPLETE")
    print("==================================================")

if __name__ == "__main__":
    run_pipeline()
