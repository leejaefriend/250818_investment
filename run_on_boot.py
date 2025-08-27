# -*- coding: utf-8 -*-
from __future__ import annotations
import os, sys, time, subprocess, traceback, importlib.util, importlib.machinery, types

# ---------------- Logging (console + file) ----------------
def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _base_dir()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "bot.log")

def _now():
    import datetime as _dt
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z")

def _tee(msg: str):
    line = f"[{_now()}] {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

log = _tee

# ---------------- Env helpers ----------------
def _load_env():
    env_path = os.path.join(BASE_DIR, ".env")
    try:
        from dotenv import load_dotenv  # optional
        load_dotenv(env_path, override=False)
        log(f"dotenv loaded: {env_path}")
    except Exception as e:
        log(f"[WARN] dotenv load skipped: {e}")
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#") or "=" not in s:
                            continue
                        k, v = s.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        os.environ.setdefault(k, v)
                log(f"dotenv manually parsed: {env_path}")
            except Exception as e2:
                log(f"[WARN] dotenv manual parse failed: {e2}")

def ENV(key, default=None, cast=str):
    v = os.environ.get(key, default)
    if v is None: return None
    try: return cast(v)
    except Exception: return v

def _try_git_pull(repo_path: str):
    if not os.path.isdir(os.path.join(repo_path, ".git")):
        return
    try:
        r = subprocess.run(["git", "-C", repo_path, "pull", "--ff-only"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, check=False, timeout=30)
        log(f"git pull in {repo_path} -> rc={r.returncode}")
        if r.stdout: log("git stdout: " + r.stdout.strip())
        if r.stderr: log("git stderr: " + r.stderr.strip())
    except Exception as e:
        log(f"[WARN] git pull skipped: {e}")

def _load_external(mod_name: str, py_path: str) -> types.ModuleType | None:
    if not os.path.isfile(py_path):
        return None
    try:
        loader = importlib.machinery.SourceFileLoader(mod_name, py_path)
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        sys.modules[mod_name] = module
        log(f"loaded external {mod_name} from {py_path}")
        return module
    except Exception as e:
        log(f"[ERROR] load_external({mod_name}) failed: {repr(e)}")
        traceback.print_exc()
        return None

# fallback (빌드에 포함되어 있으면 사용)
try:
    import train as _builtin_train
except Exception:
    _builtin_train = None
try:
    import trade_hourly as _builtin_trade
except Exception:
    _builtin_trade = None

def _resolve_external_dir() -> str:
    repo_dir = ENV("REPO_DIR", BASE_DIR, str)
    ext_dir = ENV("EXTERNAL_DIR", repo_dir, str)
    return ext_dir

def _get_modules_once():
    ext_dir = _resolve_external_dir()
    if ENV("REPO_AUTO_PULL", "1", str) in ("1", "true", "True", "TRUE"):
        _try_git_pull(ext_dir)

    train_path = os.path.join(ext_dir, "train.py")
    trade_path = os.path.join(ext_dir, "trade_hourly.py")

    train_mod = _load_external("train", train_path)
    trade_mod = _load_external("trade_hourly", trade_path)

    if train_mod is None and _builtin_train is not None:
        log("fallback to builtin train")
        train_mod = _builtin_train
    if trade_mod is None and _builtin_trade is not None:
        log("fallback to builtin trade_hourly")
        trade_mod = _builtin_trade

    return train_mod, trade_mod, ext_dir, train_path, trade_path

def _wait_modules():
    backoff = 10
    while True:
        train_mod, trade_mod, ext_dir, train_path, trade_path = _get_modules_once()
        log(f"resolved external_dir={ext_dir}")
        log(f"exists(train.py)={os.path.isfile(train_path)} path={train_path}")
        log(f"exists(trade_hourly.py)={os.path.isfile(trade_path)} path={trade_path}")

        if trade_mod is not None:
            return train_mod, trade_mod

        log("[WAIT] trade_hourly.py가 없어 거래를 시작할 수 없습니다. 위 경로를 확인하세요. 10초 후 재시도.")
        time.sleep(backoff)

def _run_train(train_mod):
    if train_mod is None:
        log("[ERROR] TRAIN FAILED: ModuleNotFoundError('train')")
        return
    try:
        log("=== TRAIN START ===")
        if hasattr(train_mod, "main"):
            train_mod.main()
        else:
            log("[ERROR] TRAIN FAILED: no main() in train")
        log("=== TRAIN END ===")
    except Exception as e:
        log(f"[ERROR] TRAIN FAILED: {repr(e)}")
        traceback.print_exc()

def _run_trade_loop(trade_mod):
    backoff = 5
    while True:
        try:
            log("=== TRADE START ===")
            if hasattr(trade_mod, "main"):
                trade_mod.main(loop=True)
            else:
                log("[ERROR] TRADE CRASH: no main() in trade_hourly")
                time.sleep(10)
        except Exception as e:
            log(f"[ERROR] TRADE CRASH: {repr(e)}")
            traceback.print_exc()
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            # 외부 파일 갱신 가능성 → 재로딩
            _, trade_mod2, _, _, _ = _get_modules_once()
            if trade_mod2 is not None:
                trade_mod = trade_mod2

def main():
    # 배너
    log("===================================================")
    log("Upbit RL Bot (launcher) starting...")
    log(f"BASE_DIR={BASE_DIR}")
    log(f"LOG_FILE={LOG_FILE}")
    log("===================================================")

    sys.path.insert(0, BASE_DIR)
    _load_env()

    mode = ENV("MODE", "DRYRUN", str).upper()
    ticker = ENV("TICKER", "KRW-BTC", str)
    interval = ENV("INTERVAL", "minute1", str)
    boot_wait = ENV("BOOT_WAIT_NETWORK", 5, int)
    do_train = ENV("TRAIN_ON_BOOT", "1", str) in ("1", "true", "True", "TRUE")

    log(f"MODE={mode}  TICKER={ticker}  INTERVAL={interval}")
    if boot_wait > 0:
        log(f"boot wait {boot_wait}s...")
        time.sleep(boot_wait)

    # 모듈 준비(없으면 계속 대기하며 사용자에게 경로 안내)
    train_mod, trade_mod = _wait_modules()

    if do_train:
        _run_train(train_mod)
    else:
        log("=== TRAIN SKIPPED ===")

    _run_trade_loop(trade_mod)

if __name__ == "__main__":
    main()
