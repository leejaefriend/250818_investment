# bot.py
import os
import sys
import time
import logging
from datetime import datetime

# .env 사용(없어도 동작)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    print("[WARN] dotenv load skipped")

# 로그 준비
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "bot.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
logging.getLogger().addHandler(console)

def _log(msg):
    print(msg)
    logging.info(msg)

def run_train():
    _log("=== TRAIN START ===")
    try:
        # 모듈 임포트 방식: PyInstaller에서 누락 방지 위해 hidden-import로 포함(빌드 스크립트에 설정)
        import train
        if hasattr(train, "main"):
            train.main()
        else:
            # train.py가 스크립트형이면 실행 경로 직접 호출
            import runpy, pathlib
            runpy.run_path(str(pathlib.Path(__file__).with_name("train.py")), run_name="__main__")
        _log("=== TRAIN END ===")
    except Exception as e:
        _log(f"[ERROR] TRAIN FAILED: {repr(e)}")
        _log("=== TRAIN END ===")

def run_trade():
    _log("=== TRADE START ===")
    try:
        import trade_hourly as trader  # 파일명은 trade_hourly.py (분봉도 여기서 처리하도록 만든 상태)
        if hasattr(trader, "main"):
            # loop=True로 계속 실행
            trader.main(loop=True)
        else:
            import runpy, pathlib
            runpy.run_path(str(pathlib.Path(__file__).with_name("trade_hourly.py")), run_name="__main__")
    except Exception as e:
        _log(f"[ERROR] TRADE CRASH: {repr(e)}")
        _log("=== TRADE END ===")
        # 무한 재시도(재부팅 자동 환경 대비)
        time.sleep(10)
        run_trade()

def main():
    _log(f"BOT START (pid={os.getpid()})")
    _log(f"cwd={os.getcwd()}  py={sys.version.split()[0]}")
    _log(f"ENV MODE={os.getenv('MODE','LIVE')}  TICKER={os.getenv('TICKER','KRW-BTC')}  INTERVAL={os.getenv('INTERVAL','minute1')}")

    # 1) 부팅 시 1회 학습
    run_train()

    # 2) 곧바로 거래 루프 진입 (분봉은 trade_hourly.py 내부에서 INTERVAL 읽어 사용)
    run_trade()

if __name__ == "__main__":
    main()
