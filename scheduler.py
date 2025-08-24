from datetime import datetime, timedelta
import time
import pytz
from config import TIMEZONE, TRADE_AT_MINUTE

def sleep_until_next_minute(target_minute: int = None):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    minute = TRADE_AT_MINUTE if target_minute is None else int(target_minute)
    # 다음 target_minute 시각 계산
    base = now.replace(second=0, microsecond=0)
    if now.minute >= minute:
        base = base + timedelta(hours=1)
    target = base.replace(minute=minute)
    # 대기
    sec = max((target - now).total_seconds(), 0)
    time.sleep(sec)
    return target
