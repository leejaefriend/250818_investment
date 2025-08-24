from __future__ import annotations

import re
import time
from datetime import datetime, timedelta

import pytz
from config import TIMEZONE, INTERVAL

_MINUTE_RE = re.compile(r"^minute(\d+)$", re.IGNORECASE)


def _next_aligned_time(now: datetime, interval: str) -> datetime:
    """
    INTERVAL에 맞춰 '다음' 캔들 시각로 정렬한 datetime을 돌려준다.
    - minuteN: 다음 N분 배수의 00초
    - minute60: 다음 시의 00분 00초
    - day: 다음 날 00:00:00
    - week: 다음 주 월요일 00:00:00 (ISO 주 기준)
    - month: 다음 달 1일 00:00:00
    """
    tz = pytz.timezone(TIMEZONE)
    now = now.astimezone(tz)
    base = now.replace(second=0, microsecond=0)

    m = _MINUTE_RE.match(interval)
    if m:
        n = int(m.group(1))
        if n <= 0:
            n = 1
        # 다음 n분 배수의 시각
        minute_mod = base.minute % n
        if minute_mod == 0 and now.second == 0:
            # 막 정렬된 순간이면 다음 슬롯으로 넘김
            delta = timedelta(minutes=n)
            target = base + delta
        else:
            add = n - minute_mod if minute_mod > 0 else n
            target = base + timedelta(minutes=add)
        return target.replace(second=0, microsecond=0)

    # 특수 케이스
    if interval.lower() == "day":
        target = base.replace(hour=0, minute=0) + timedelta(days=1)
        return target
    if interval.lower() == "week":
        # 다음 주 월요일 00:00
        days_ahead = 7 - base.weekday()  # 월=0
        if days_ahead == 0:
            days_ahead = 7
        target = base.replace(hour=0, minute=0) + timedelta(days=days_ahead)
        return target
    if interval.lower() == "month":
        # 다음 달 1일 00:00
        y, mth = base.year, base.month
        if mth == 12:
            y += 1
            mth = 1
        else:
            mth += 1
        return base.replace(year=y, month=mth, day=1, hour=0, minute=0)

    # minute60 또는 비정규 입력은 '다음 정시'로
    if interval.lower() in ("minute60", "hour", "hourly"):
        base = base.replace(minute=0)
        if now.minute == 0 and now.second == 0:
            return base + timedelta(hours=1)
        return base + timedelta(hours=1)

    # 기본: 다음 1분
    if now.second == 0:
        return base + timedelta(minutes=1)
    return base + timedelta(minutes=1)


def sleep_until_next_bar(interval: str | None = None):
    """
    INTERVAL에 맞춰 '다음 캔들 시각'까지 슬립.
    config.INTERVAL을 기본값으로 사용.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    interval = (interval or INTERVAL)
    target = _next_aligned_time(now, interval)
    sec = max((target - now).total_seconds(), 0.0)
    time.sleep(sec)
    return target
