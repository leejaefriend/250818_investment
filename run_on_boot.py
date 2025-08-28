# run_on_boot.py
import os, sys, time, subprocess, importlib.util, traceback

def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")

def _log_setup(base_dir):
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "bot.log")

def _print(msg, log_file=None):
    line = f"[{_now()}] {msg}"
    print(line, flush=True)
    if log_file:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

def _is_frozen():
    return getattr(sys, "frozen", False)

def _base_dir():
    # PyInstaller EXE ⇒ dist 폴더, 스크립트 실행 ⇒ 파일 위치
    return os.path.dirname(sys.executable) if _is_frozen() \
        else os.path.dirname(os.path.abspath(__file__))

def _load_env(base_dir, log_file):
    """
    .env 탐색 순서:
    1) BASE_DIR/.env (dist/.env 또는 run_on_boot.py와 같은 폴더)
    2) BASE_DIR의 부모/.env (⇒ 리포지토리 루트)
    3) 현재 작업 디렉토리/.env
    """
    candidates = [
        os.path.join(base_dir, ".env"),
        os.path.join(os.path.dirname(base_dir), ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]
    loaded = False
    try:
        from dotenv import load_dotenv  # 표준 로더
        for p in candidates:
            if os.path.exists(p):
                load_dotenv(p, override=True)
                _print(f"dotenv loaded: {p}", log_file)
                loaded = True
                break
        if not loaded:
            _print(f"[WARN] .env not found in: " + " | ".join(candidates), log_file)
    except Exception as e:
        # dotenv 미설치 등일 때 수동 파서
        for p in candidates:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        for line in f:
                            s = line.strip()
                            if not s or s.startswith("#"):
                                continue
                            if "=" in s:
                                k, v = s.split("=", 1)
                                os.environ.setdefault(k.strip(), v.strip())
                    _print(f"[WARN] dotenv load skipped: {e}. manual parsed: {p}", log_file)
                    loaded = True
                    break
                except Exception:
                    pass
        if not loaded:
            _print("[WARN] dotenv load failed and no .env found.", log_file)

def _git_pull(repo_dir, log_file):
    want = os.getenv("GIT_PULL", "0").lower() in ("1", "true", "yes", "y")
    if not want:
        return
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "pull", "--ff-only"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        _print(f"git pull in {repo_dir} -> rc={proc.returncode}", log_file)
        _print("git stdout: " + (proc.stdout or "").strip(), log_file)
    except Exception as e:
        _print(f"[WARN] git pull failed: {e}", log_file)

def _spec_from_file(module_name, py_path):
    spec = importlib.util.spec_from_file_location(module_name, py_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _load_external(module_name, repo_dir, log_file):
    py_path = os.path.join(repo_dir, f"{module_name}.py")
    if not os.path.exists(py_path):
        _print(f"[ERROR] {module_name}.py not found at: {py_path}", log_file)
        return None
    try:
        return _spec_from_file(module_name, py_path)
    except Exception as e:
        _print(f"[ERROR] load_external({module_name}) failed: {repr(e)}", log_file)
        traceback.print_exc()
        return None

def main():
    base_dir = _base_dir()
    log_file = _log_setup(base_dir)

    _print("=" * 58, log_file)
    _print("Upbit RL Bot (launcher) starting...", log_file)
    _print(f"BASE_DIR={base_dir}", log_file)
    _print(f"LOG_FILE={log_file}", log_file)
    _print("=" * 58, log_file)

    # 1) .env 로드: dist/.env → (fallback) 리포지토리 루트/.env
    _load_env(base_dir, log_file)

    # 2) 환경 파라미터 확인
    mode     = os.getenv("MODE", "DRYRUN")
    ticker   = os.getenv("TICKER", "KRW-BTC")
    interval = os.getenv("INTERVAL", "minute1")
    _print(f"MODE={mode}  TICKER={ticker}  INTERVAL={interval}", log_file)

    # 3) 리포지토리 디렉터리 결정
    #    - REPO_DIR가 설정되어 있으면 우선
    #    - 아니면 dist일 때 부모 폴더를 리포지토리로 간주
    #    - 그 외에는 현재 base_dir 자체를 사용
    repo_dir = os.getenv("REPO_DIR")
    if not repo_dir or not os.path.isdir(repo_dir):
        repo_dir = os.path.dirname(base_dir) if os.path.basename(base_dir).lower() == "dist" else base_dir

    wait_secs = int(os.getenv("BOOT_WAIT_SECS", "5"))
    _print(f"boot wait {wait_secs}s...", log_file)
    time.sleep(wait_secs)

    # 4) (옵션) git pull
    _git_pull(repo_dir, log_file)

    # 경로 존재 확인
    train_path = os.path.join(repo_dir, "train.py")
    trade_path = os.path.join(repo_dir, "trade_hourly.py")
    _print(f"resolved external_dir={repo_dir}", log_file)
    _print(f"exists(train.py)={os.path.exists(train_path)} path={train_path}", log_file)
    _print(f"exists(trade_hourly.py)={os.path.exists(trade_path)} path={trade_path}", log_file)

    # 5) 학습
    _print("=== TRAIN START ===", log_file)
    train_mod = _load_external("train", repo_dir, log_file)
    if train_mod and hasattr(train_mod, "main"):
        try:
            train_mod.main()
        except Exception as e:
            _print(f"[ERROR] TRAIN FAILED: {repr(e)}", log_file)
    else:
        _print("[WARN] train.py not executed (module missing or no main())", log_file)
    _print("=== TRAIN END ===", log_file)

    # 6) 거래
    _print("=== TRADE START ===", log_file)
    trade_mod = _load_external("trade_hourly", repo_dir, log_file)
    if trade_mod and hasattr(trade_mod, "main"):
        try:
            trade_mod.main(loop=True)   # 거래 루프 내부에서 주기 실행
        except Exception as e:
            _print(f"[ERROR] TRADE CRASH: {repr(e)}", log_file)
    else:
        _print("[WAIT] trade_hourly.py가 없어 거래를 시작할 수 없습니다. 10초 후 재시도.", log_file)
        time.sleep(10)

if __name__ == "__main__":
    main()
