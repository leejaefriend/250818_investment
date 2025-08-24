import os
from dotenv import load_dotenv

load_dotenv()

UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "")
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "")

TICKER = os.getenv("TICKER", "KRW-BTC")
INTERVAL = os.getenv("INTERVAL", "minute60")
BASE_KRW = int(os.getenv("BASE_KRW", "1000000"))
MIN_ORDER_KRW = int(os.getenv("MIN_ORDER_KRW", "5000"))

LIVE_TRADE = os.getenv("LIVE_TRADE", "0") == "1"
UNLOCK_PHRASE = os.getenv("UNLOCK_PHRASE", "")
MODEL_PATH = os.getenv("MODEL_PATH", "models/ppo.zip")
LOG_PATH = os.getenv("LOG_PATH", "logs/trades.csv")

TAKER_FEE = float(os.getenv("TAKER_FEE", "0.0005"))
SLIPPAGE = float(os.getenv("SLIPPAGE", "0.0005"))
TARGET_RISK = float(os.getenv("TARGET_RISK", "0.25"))

TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")
TRADE_AT_MINUTE = int(os.getenv("TRADE_AT_MINUTE", "0"))

def live_unlocked() -> bool:
    return LIVE_TRADE and (UNLOCK_PHRASE.strip() == "I-UNDERSTAND-RISKS")
