# upbit_exec.py
# CPU-only / DRYRUN-LIVE 토글 / 최소주문 보정 / 명확한 실패 사유 로깅

import os
import time
from dataclasses import dataclass
from typing import Tuple, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

MODE = os.getenv("MODE", "DRYRUN").upper()
TICKER = os.getenv("TICKER", "KRW-BTC")

BUY_FRAC = float(os.getenv("BUY_FRAC", "0.25"))      # 가용 KRW 중 매수 비율
SELL_FRAC = float(os.getenv("SELL_FRAC", "0.25"))    # 보유 코인 중 매도 비율

MIN_ORDER_KRW = int(float(os.getenv("MIN_ORDER_KRW", "5000")))  # 업비트 KRW 하한
MIN_ORDER_BUFFER = int(float(os.getenv("MIN_ORDER_BUFFER", "200")))  # 수수료/슬리피지 버퍼
FEE_RATE = float(os.getenv("FEE_RATE", "0.0005"))  # 왕복 수수료 가정치 보정용(대략)

ACCESS = os.getenv("UPBIT_ACCESS_KEY", "")
SECRET = os.getenv("UPBIT_SECRET_KEY", "")

LOG_PATH = os.path.join(os.getcwd(), "logs", "trade.log")

# pyupbit 사용 (설치: pip install pyupbit)
try:
    import pyupbit
except Exception as e:
    pyupbit = None


def _ensure_dirs():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def _log(*args):
    _ensure_dirs()
    msg = " ".join(str(a) for a in args)
    print(msg, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg + "\n")
    except Exception:
        pass


@dataclass
class Balances:
    krw: float
    coin: float


class UpbitExec:
    def __init__(self, ticker: str, mode: str = MODE):
        self.ticker = ticker
        self.mode = mode.upper()
        self.upbit = None
        if self.mode == "LIVE":
            if pyupbit is None:
                raise RuntimeError("pyupbit 미설치: pip install pyupbit")
            if not ACCESS or not SECRET:
                raise RuntimeError("LIVE 모드인데 UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY 누락")
            self.upbit = pyupbit.Upbit(ACCESS, SECRET)

    # ======== 기본 유틸 ========
    def get_price(self) -> float:
        """현재가(호가 우선). 실패 시 0"""
        try:
            ob = pyupbit.get_orderbook(self.ticker)
            if ob and "orderbook_units" in ob[0] and len(ob[0]["orderbook_units"]) > 0:
                return float(ob[0]["orderbook_units"][0]["ask_price"])
        except Exception:
            pass
        try:
            # fallback: 최근 체결가
            df = pyupbit.get_ohlcv(self.ticker, interval="minute1", count=1)
            if df is not None and len(df) > 0:
                return float(df["close"][-1])
        except Exception:
            pass
        return 0.0

    def balances(self) -> Balances:
        """KRW/코인 잔고 조회"""
        if self.mode == "DRYRUN" or self.upbit is None:
            # DRYRUN: 간단 캐시 파일(or 0) 사용할 수도 있음. 여기서는 0으로.
            return Balances(krw=0.0, coin=0.0)
        try:
            bals = self.upbit.get_balances()
            krw = 0.0
            coin = 0.0
            base = self.ticker.split("-")[1]
            for b in bals:
                c = b.get("currency")
                if c == "KRW":
                    krw = float(b.get("balance", 0)) + float(b.get("locked", 0))
                if c == base:
                    coin = float(b.get("balance", 0))
            return Balances(krw=krw, coin=coin)
        except Exception as e:
            _log("[WARN] balances() 실패:", e)
            return Balances(krw=0.0, coin=0.0)

    def portfolio_value(self, price: Optional[float] = None) -> float:
        if price is None:
            price = self.get_price()
        bal = self.balances()
        return bal.krw + bal.coin * price

    # ======== 주문 핵심 ========
    def _min_order_threshold(self) -> int:
        """최소주문 하한(KRW) + 버퍼 + 수수료 여유분"""
        # 수수료 여유는 대략 하한 * FEE_RATE 로 반영
        fee_pad = int(MIN_ORDER_KRW * FEE_RATE)
        return int(MIN_ORDER_KRW + MIN_ORDER_BUFFER + fee_pad)

    def buy_fraction(self, frac: float = None) -> Tuple[bool, str]:
        """가용 KRW의 frac만큼 시장가 매수. 하한 미만이면 거부."""
        frac = BUY_FRAC if frac is None else max(0.0, min(1.0, float(frac)))
        price = self.get_price()
        if price <= 0:
            return False, "가격 조회 실패"
        bal = self.balances()
        krw_avail = bal.krw  # upbit는 get_balances 기준 'balance+locked'를 포함했으니 실제 가용금액 보수적으로 frac사용

        order_min = self._min_order_threshold()
        if krw_avail < order_min:
            return False, f"가용 KRW({int(krw_avail)}) < 최소하한({order_min})"

        # 주문금액 산출(하한 이상, 가용 이내)
        target = int(krw_avail * frac)
        amount_krw = max(order_min, target)
        amount_krw = min(amount_krw, int(krw_avail) - MIN_ORDER_BUFFER)
        if amount_krw < order_min:
            return False, f"하한 충족 실패(계산후 {amount_krw} < {order_min})"

        if self.mode == "DRYRUN" or self.upbit is None:
            _log("DRYRUN BUY", f"KRW={amount_krw}")
            return True, f"DRYRUN 매수 가정({amount_krw} KRW)"

        try:
            # 업비트 시장가 매수: amount(원화)
            resp = self.upbit.buy_market_order(self.ticker, amount_krw)
            _log("LIVE BUY", resp)
            ok = isinstance(resp, dict) and resp.get("uuid") is not None
            return (True, "주문 접수") if ok else (False, f"주문 실패:{resp}")
        except Exception as e:
            return False, f"API 오류:{e}"

    def sell_fraction(self, frac: float = None) -> Tuple[bool, str]:
        """보유 코인의 frac만큼 시장가 매도. 하한 미만이면 거부."""
        frac = SELL_FRAC if frac is None else max(0.0, min(1.0, float(frac)))
        price = self.get_price()
        if price <= 0:
            return False, "가격 조회 실패"
        bal = self.balances()
        coin_bal = bal.coin
        if coin_bal <= 0:
            return False, "보유 코인 0"

        vol = coin_bal * frac
        est_krw = int(vol * price)
        order_min = self._min_order_threshold()
        if est_krw < order_min:
            return False, f"추정 체결 KRW({est_krw}) < 최소하한({order_min})"

        if self.mode == "DRYRUN" or self.upbit is None:
            _log("DRYRUN SELL", f"VOL={vol:.8f} (≈{est_krw} KRW)")
            return True, f"DRYRUN 매도 가정({est_krw} KRW)"

        try:
            # 업비트 시장가 매도: volume(코인수량)
            resp = self.upbit.sell_market_order(self.ticker, vol)
            _log("LIVE SELL", resp)
            ok = isinstance(resp, dict) and resp.get("uuid") is not None
            return (True, "주문 접수") if ok else (False, f"주문 실패:{resp}")
        except Exception as e:
            return False, f"API 오류:{e}
