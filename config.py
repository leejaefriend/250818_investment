import os
from dotenv import load_dotenv

load_dotenv()

# --- Keys ---
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")

# --- Trading target ---
TICKER = os.getenv("TICKER", "KRW-BTC")
INTERVAL = os.getenv("INTERVAL", "minute1")  # 기본값을 minute1로
BASE_KRW = int(os.getenv("BASE_KRW", "1000000"))
MIN_ORDER_KRW = int(os.getenv("MIN_ORDER_KRW", "5000"))

# --- Execution toggle ---
LIVE_TRADE = os.getenv("LIVE_TRADE", "0") == "1"
UNLOCK_PHRASE = os.getenv("UNLOCK_PHRASE", "")

# MODEL_PATH 자동화: "AUTO"면 인터벌별로 파일명 분리
_MODEL_PATH_ENV = os.getenv("MODEL_PATH", "AUTO")
if _MODEL_PATH_ENV.strip().upper() == "AUTO" or _MODEL_PATH_ENV.strip() == "":
    MODEL_PATH = f"models/ppo_{INTERVAL}.zip"
else:
    MODEL_PATH = _MODEL_PATH_ENV

LOG_PATH = os.getenv("LOG_PATH", "logs/trades.csv")

# --- Fees & risk ---
TAKER_FEE = float(os.getenv("TAKER_FEE", "0.0005"))
SLIPPAGE = float(os.getenv("SLIPPAGE", "0.0005"))
TARGET_RISK = float(os.getenv("TARGET_RISK", "0.25"))

# --- Timezone / legacy scheduler param ---
TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")
TRADE_AT_MINUTE = int(os.getenv("TRADE_AT_MINUTE", "0"))

def live_unlocked() -> bool:
    # 실거래 잠금 2중 해제 조건
    return LIVE_TRADE and (UNLOCK_PHRASE.strip() == "I-UNDERSTAND-RISKS")
