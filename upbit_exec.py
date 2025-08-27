import os, math, time
from datetime import datetime
from pathlib import Path

# DRYRUN 모드에서는 실제 체결 대신 시뮬레이션 처리
MODE = os.getenv("MODE", "DRYRUN").upper()

# 주문 하한(원)
MIN_ORDER_KRW = int(os.getenv("MIN_ORDER_KRW", "5000"))
MIN_ORDER_BUFFER = int(os.getenv("MIN_ORDER_BUFFER", "300"))  # 수수료/호가/슬리피지 버퍼

LOG_DIR = Path(os.getenv("LOG_DIR", Path(__file__).parent / "logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
EXEC_LOG = LOG_DIR / "exec.log"

def _log(*args):
    msg = " ".join(map(str, args))
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with EXEC_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

class UpbitExec:
    def __init__(self, ticker="KRW-BTC"):
        self.ticker = ticker
        # 실제 구현에서는 upbit api client 세팅
        self._krw = 100000 if MODE == "DRYRUN" else None  # 예시: DRYRUN 시 가상 KRW
        self._coin = 0.0

    # ----- 잔고 -----
    def balances(self):
        # 실제는 API 조회
        krw = float(self._krw if self._krw is not None else 0.0)
        coin = float(self._coin)
        return krw, coin

    def portfolio_value(self, price: float):
        krw, coin = self.balances()
        return krw + coin * price

    # ----- 내부 보조 -----
    def _can_buy(self, price: float, krw_to_use: float):
        # 수수료/슬리피지 감안 버퍼 제거 후도 업비트 하한 이상인지 체크
        effective = krw_to_use - MIN_ORDER_BUFFER
        return effective >= MIN_ORDER_KRW

    def _krw_to_buy_fraction(self, fraction=0.1):
        krw, _ = self.balances()
        use = krw * fraction
        # 하한 미만이면 하한 맞춰줌 (가능하면)
        if use < (MIN_ORDER_KRW + MIN_ORDER_BUFFER) and krw >= (MIN_ORDER_KRW + MIN_ORDER_BUFFER):
            use = MIN_ORDER_KRW + MIN_ORDER_BUFFER
        return max(0.0, math.floor(use))  # 정수 KRW

    # ----- 주문 -----
    def buy_fraction(self, price=None, fraction=0.1):
        # 실제는 시세 조회
        price = float(price or 0.0)
        krw_to_use = self._krw_to_buy_fraction(fraction)
        if not self._can_buy(price, krw_to_use):
            _log("BUY blocked: KRW 부족/최소주문 미만", f"krw_to_use={krw_to_use}", f"min={MIN_ORDER_KRW}+buf{MIN_ORDER_BUFFER}")
            return False, "KRW 부족/최소주문 미만"

        # 체결 수량(수수료 보수적으로 제외)
        fee_rate = 0.0005  # 예: 0.05%
        qty = (krw_to_use * (1 - fee_rate)) / price
        qty = max(0.0, qty)

        if MODE == "DRYRUN":
            self._krw -= krw_to_use
            self._coin += qty
            _log("DRYRUN BUY", f"krw={krw_to_use}", f"qty={qty:.8f}", f"price={price}")
            return True, {"krw": krw_to_use, "qty": qty, "price": price}
        else:
            # TODO: 실거래 API 연동
            _log("LIVE BUY (stub)", f"krw={krw_to_use}", f"qty~{qty:.8f}", f"price={price}")
            return True, {"krw": krw_to_use, "qty": qty, "price": price}

    def sell_all(self, price=None):
        price = float(price or 0.0)
        _, coin = self.balances()
        if coin <= 0:
            return False, "보유코인 없음"
        fee_rate = 0.0005
        krw_gain = coin * price * (1 - fee_rate)

        if MODE == "DRYRUN":
            self._coin = 0.0
            self._krw += krw_gain
            _log("DRYRUN SELL", f"coin->0", f"+krw~{int(krw_gain)}", f"price={price}")
            return True, {"krw": int(krw_gain), "price": price}
        else:
            # TODO: 실거래 API 연동
            _log("LIVE SELL (stub)", f"qty={coin:.8f}", f"price={price}")
            return True, {"krw": int(krw_gain), "price": price}
