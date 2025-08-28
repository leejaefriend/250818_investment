# bot.py
import os
import sys
import time
import logging
from datetime import datetime

# ---- 0) 안전한 작업폴더 설정: exe가 있는 곳으로 이동 ----
def _base_dir():
    if getattr(sys, "frozen", False):  # PyInstaller onefile
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base_dir()
os.makedirs(BASE_DIR, exist_ok=True)
os.chdir(BASE_DIR)

# ---- 1) .env 로드 (없어도 진행) ----
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    print("[WARN] dotenv load skipped")

# ---- 2) 필수 디렉터리 보장 ----
LOG_DIR = os.path.join(BASE_DIR, "logs")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
TB_DIR = os.path.join(BASE_DIR, "tb")
for d in (LOG_DIR, MODEL_DIR, DATA_DIR, TB_DIR):
    os.makedirs(d, exist_ok=True)

# 경로를 모듈들이 참조할 수 있게 환경변수로도 노출
os.environ.setdefault("LOG_DIR", LOG_DIR)
os.environ.setdefault("MODEL_DIR", MODEL_DIR)
os.environ.setdefault("DATA_DIR", DATA_DIR)
os.environ.setdefault("TENSORBOARD_DIR", TB_DIR)

# ---- 3) 로깅 ----
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "bot.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
_console = logging.StreamHandler()
_console.setLevel(logging.INFO)
_console.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logging.getLogger().addHandler(_console)

def _log(msg): print(msg); logging.info(msg)

def _fix_and_retry(fn, desc):
    """FileNotFoundError가 나면 경로를 만들어 주고 1회 재시도"""
    try:
        return fn()
    except FileNotFoundError as e:
        missing = e.filename or str(e)
        _log(f"[WARN] {desc} FileNotFoundError: {missing}")
        # 흔한 누락 경로들 자동 생성
        for d in (LOG_DIR, MODEL_DIR, DATA_DIR, TB_DIR):
            os.makedirs(d, exist_ok=True)
        time.sleep(1)
        try:
            return fn()
        except Exception as e2:
            _log(f"[ERROR] {desc} 재시도 실패: {repr(e2)}")
            raise

def run_train():
    _log("=== TRAIN START ===")
    def _inner():
        import train
        if hasattr(train, "main"):
            train.main()
        else:
            # 스크립트형 대비
            import runpy
            runpy.run_module("train", run_name="__main__")
    try:
        _fix_and_retry(_inner, "TRAIN")
    except Exception as e:
        _log(f"[ERROR] TRAIN FAILED: {repr(e)}")
    _log("=== TRAIN END ===")

def run_trade():
    _log("=== TRADE START ===")
    def _inner():
        import trade_hourly as trader
        if hasattr(trader, "main"):
            trader.main(loop=True)
        else:
            import runpy
            runpy.run_module("trade_hourly", run_name="__main__")
    try:
        _fix_and_retry(_inner, "TRADE")
    except Exception as e:
        _log(f"[ERROR] TRADE CRASH: {repr(e)}")
        _log("=== TRADE END ===")
        time.sleep(10)
        run_trade()  # 무한 재시도

def main():
    _log(f"BOT START (pid={os.getpid()})")
    _log(f"cwd={os.getcwd()}  py={sys.version.split()[0]}")
    mode = os.getenv("MODE", "LIVE")
    ticker = os.getenv("TICKER", "KRW-BTC")
    interval = os.getenv("INTERVAL", "minute1")
    _log(f"ENV MODE={mode}  TICKER={ticker}  INTERVAL={interval}")

    # 업비트 최소주문 보호 기본값(필요시 .env에서 오버라이드)
    os.environ.setdefault("MIN_ORDER_KRW", "5000")

    # 1회 학습 후
    run_train()
    # 거래 루프 진입
    run_trade()

if __name__ == "__main__":
    main()
