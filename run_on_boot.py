# run_on_boot.py
import os, sys, time, argparse, runpy
from datetime import datetime, timezone, timedelta

# === 실행 경로 고정 ===
EXEC_DIR = os.path.dirname(getattr(sys, "_MEIPASS", os.path.abspath(__file__)))
os.chdir(EXEC_DIR)

def resource_path(relpath: str) -> str:
    """PyInstaller onefile/onedir 모두에서 동작하는 리소스 경로 헬퍼"""
    base = getattr(sys, "_MEIPASS", EXEC_DIR)
    return os.path.join(base, relpath)

def _simple_load_dotenv(dotenv_path):
    """python-dotenv이 없을 때를 위한 초간단 .env 로더 (key=value 형식만)"""
    if not os.path.exists(dotenv_path):
        return
    try:
        with open(dotenv_path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                os.environ.setdefault(k, v)
    except Exception as e:
        print("[WARN] fallback dotenv parse failed:", e)

def _load_dotenv():
    # 1) python-dotenv가 있으면 사용
    try:
        from dotenv import load_dotenv  # type: ignore
        # exe 옆의 .env 우선
        env_path = os.path.join(EXEC_DIR, ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)
        else:
            load_dotenv(override=False)
    except Exception as e:
        print("[WARN] dotenv load skipped:", e)
        # 2) 없으면 간이 로더
        _simple_load_dotenv(os.path.join(EXEC_DIR, ".env"))

_load_dotenv()

def kst_now():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S%z")

def wait_network(max_wait_s=60):
    # pyupbit 사용하여 간단 체크(없으면 그냥 진행)
    try:
        import pyupbit  # noqa
    except Exception:
        return
    import pyupbit
    start = time.time()
    while True:
        try:
            df = pyupbit.get_ohlcv(os.getenv("TICKER", "KRW-BTC"),
                                   interval=os.getenv("INTERVAL", "minute1"),
                                   count=2)
            if df is not None and len(df) > 0:
                print(f"[{kst_now()}] 네트워크 OK")
                return
        except Exception:
            pass
        if time.time() - start > max_wait_s:
            print(f"[{kst_now()}] 네트워크 대기 타임아웃, 계속 진행")
            return
        time.sleep(3)

def run_training():
    """
    train.py를 직접 import하지 않고, 번들/외부 경로에서 run_path로 실행.
    - PyInstaller --add-data로 묶인 train.py 또는 exe 옆에 있는 train.py 모두 지원
    """
    print(f"[{kst_now()}] === TRAIN START ===")
    try:
        tpath = resource_path("train.py")
        if not os.path.exists(tpath):
            # exe 옆 로컬 파일 시도(개발 중 배포 혼용 지원)
            tpath = os.path.join(EXEC_DIR, "train.py")
        if not os.path.exists(tpath):
            raise FileNotFoundError("train.py not found in bundle or beside exe")

        # train.py 내에서 if __name__ == "__main__": main() 패턴이어도 잘 돈다
        runpy.run_path(tpath, run_name="__main__")
    except Exception as e:
        print(f"[{kst_now()}] [ERROR] TRAIN FAILED:", repr(e))
        if os.getenv("FAIL_ON_TRAIN", "0") == "1":
            raise
    print(f"[{kst_now()}] === TRAIN END ===")

def run_trader_forever():
    """
    trade_hourly.py를 run_path로 호출해 메인 루프로 진입.
    크래시 시 백오프로 재시작.
    """
    backoff = 5
    while True:
        try:
            print(f"[{kst_now()}] === TRADE START ===")
            tpath = resource_path("trade_hourly.py")
            if not os.path.exists(tpath):
                tpath = os.path.join(EXEC_DIR, "trade_hourly.py")
            if not os.path.exists(tpath):
                raise FileNotFoundError("trade_hourly.py not found in bundle or beside exe")

            # trade_hourly.py 안에서 main(loop=True) 호출이 있으면 그 코드가 실행됨
            runpy.run_path(tpath, run_name="__main__")
        except Exception as e:
            print(f"[{kst_now()}] [ERROR] TRADE CRASH:", repr(e))
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue
        # 정상 종료되면 바로 재시작
        time.sleep(2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-train", action="store_true", help="부팅시 학습 건너뛰기")
    args = parser.parse_args()

    wait_network(max_wait_s=int(os.getenv("BOOT_WAIT_NETWORK", "60")))

    train_on_boot = os.getenv("TRAIN_ON_BOOT", "1") == "1"
    if not args.skip_train and train_on_boot:
        run_training()
    else:
        print(f"[{kst_now()}] 부팅시 학습 생략 (TRAIN_ON_BOOT={train_on_boot}, --skip-train={args.skip_train})")

    run_trader_forever()

if __name__ == "__main__":
    main()
