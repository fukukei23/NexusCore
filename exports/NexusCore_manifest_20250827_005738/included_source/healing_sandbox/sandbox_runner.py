
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

log_level_str = "DEBUG"
log_level = logging.getLevelName(log_level_str)
log_format = "%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s"
logging.basicConfig(level=log_level, format=log_format)

from src.agents.orchestrator import Orchestrator
from src.agents.debugger_agent import DebuggerAgent
from src.agents.patch_applier import PatchApplier

def run():
    logging.info(">> Starting Self-Healing Cycle for CRM App...")
    
    debugger = DebuggerAgent(api_key="dummy_key", model="dummy_model", knowledge_base_path="fkb_local.json")
    patcher = PatchApplier()
    
    # Orchestratorにログ保存先のパスを渡す
    orchestrator = Orchestrator(
        debugger_agent=debugger,
        patch_applier=patcher,
        log_dir="logs", # サンドボックス内のlogsディレクトリを指定
        max_retries=3
    )
    
    orchestrator.self_healing_cycle(
        test_file_path="tests/test_main.py",
        source_file_path="app/main.py"
    )

if __name__ == '__main__':
    run()
