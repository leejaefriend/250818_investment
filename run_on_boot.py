import os, sys, time, traceback, importlib.util, logging
from datetime import datetime
from pathlib import Path

# -------- logging --------
BASE_DIR = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("boot")

log.info("="*50)
log.info("Upbit RL Bot (launcher) starting...")
log.info(f"BASE_DIR={BASE_DIR}")
log.info(f"LOG_FILE={LOG_FILE}")
log.info("="*50)

# -------- dotenv (optional) --------
def load_env(env_path: Path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        log.info(f"dotenv loaded: {env_path}")
    except Exception as e:
        log.warning(f"dotenv load skipped: {e}")

env_path = BASE_DIR / ".env"
load_env(env_path if env_path.exists() else BASE_DIR / ".env.sample")

# -------- envs --------
MODE = os.getenv("MODE", "DRYRUN").upper()
TICKER = os.getenv("TICKER", "KRW-BTC")
INTERVAL = os.getenv("INTERVAL", "minute1")
REPO_DIR = Path(os.getenv("REPO_DIR", str(BASE_DIR)))
BOOT_WAIT_SEC = int(os.getenv("BOOT_WAIT_SEC", "5"))
GIT_PULL_ON_START = os.getenv("GIT_PULL_ON_START", "true").lower() == "true"

log.info(f"MODE={MODE}  TICKER={TICKER}  INTERVAL={INTERVAL}")
log.info(f"boot wait {BOOT_WAIT_SEC}s...")
time.sleep(BOOT_WAIT_SEC)

# -------- optional git pull --------
def git_pull(repo_dir: Path):
    try:
        import subprocess
        rc = subprocess.call(["git", "-C", str(repo_dir), "pull"])
        log.info(f"git pull in {repo_dir} -> rc={rc}")
    except Exception as e:
        log.warning(f"git pull skipped: {e}")

if GIT_PULL_ON_START:
    git_pull(REPO_DIR)

# -------- dynamic loader (by file path) --------
def load_by_path(module_name: str, file_path: Path):
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(file_path))
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load spec for {module_name} at {file_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:
        log.error(f"[ERROR] load_external({module_name}) failed: {traceback.format_exc()}")
        return None

# ensure repo_dir on sys.path (so relative imports in external files work)
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))
log.info(f"resolved external_dir={REPO_DIR}")

train_py = REPO_DIR / "train.py"
trade_py = REPO_DIR / "trade_hourly.py"
log.info(f"exists(train.py)={train_py.exists()} path={train_py}")
log.info(f"exists(trade_hourly.py)={trade_py.exists()} path={trade_py}")

# -------- train (best-effort) --------
def run_train():
    if not train_py.exists():
        log.warning("[SKIP] train.py not found. skip training.")
        return
    mod = load_by_path("train", train_py)
    if mod is None:
        return
    log.info("=== TRAIN START ===")
    try:
        if hasattr(mod, "main"):
            mod.main()
        else:
            # allow "if __name__ == '__main__': main()" style fallback
            if hasattr(mod, "__dict__") and "main" in mod.__dict__:
                mod.__dict__["main"]()
    except Exception:
        log.error(f"[ERROR] TRAIN FAILED: {traceback.format_exc()}")
    finally:
        log.info("=== TRAIN END ===")

# -------- trade loop --------
def run_trade_loop():
    while True:
        try:
            if not trade_py.exists():
                log.info("[WAIT] trade_hourly.py가 없어 거래를 시작할 수 없습니다. 위 경로를 확인하세요. 10초 후 재시도.")
                time.sleep(10)
                git_pull(REPO_DIR)
                continue
            mod = load_by_path("trade_hourly", trade_py)
            if mod is None:
                time.sleep(10)
                continue
            log.info("=== TRADE START ===")
            if hasattr(mod, "main"):
                # trade_hourly.main(loop=True) 권장
                mod.main(loop=True)
            else:
                log.error("[ERROR] trade_hourly.py main()가 없습니다.")
                time.sleep(10)
        except Exception:
            log.error(f"[ERROR] TRADE CRASH: {traceback.format_exc()}")
            time.sleep(5)

if __name__ == "__main__":
    run_train()            # 실패해도 넘어감
    run_trade_loop()       # 영속 루프
