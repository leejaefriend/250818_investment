import os, csv, math
from datetime import datetime
import pyupbit
from config import (
    UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, TICKER, MIN_ORDER_KRW, TAKER_FEE,
    LIVE_TRADE, LOG_PATH, TARGET_RISK, SLIPPAGE, BASE_KRW, live_unlocked
)

def _ensure_dirs():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(os.path.dirname(LOG_PATH)), exist_ok=True)

def _log(action, price, krw, coin, value, mode):
    _ensure_dirs()
    header = ["ts","mode","action","price","krw","coin","value"]
    row = [datetime.now().isoformat(timespec="seconds"), mode, action, price, int(krw), float(coin), float(value)]
    exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists: w.writerow(header)
        w.writerow(row)

class PaperWallet:
    def __init__(self, base_krw=BASE_KRW): self.krw=float(base_krw); self.coin=0.0
    def value(self, price: float) -> float: return self.krw + self.coin*price

class UpbitExec:
    def __init__(self):
        self.mode = "LIVE" if live_unlocked() else "PAPER"
        self.upbit = pyupbit.Upbit(UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY) if self.mode=="LIVE" else None
        self.wallet = None if self.mode=="LIVE" else PaperWallet()

    def _current_price(self) -> float:
        p = pyupbit.get_current_price(TICKER)
        if p is None:
            ohlc = pyupbit.get_ohlcv(TICKER, interval="minute1", count=1)
            p = float(ohlc["close"].iloc[-1])
        return float(p)

    def balances(self):
        if self.mode=="LIVE":
            balances = self.upbit.get_balances()
            krw, coin = 0.0, 0.0
            for b in balances:
                if b["currency"]=="KRW": krw=float(b["balance"])
                if b["currency"]==TICKER.split("-")[1]: coin=float(b["balance"])
            return krw, coin
        return self.wallet.krw, self.wallet.coin

    def portfolio_value(self, price: float) -> float:
        krw, coin = self.balances()
        return krw + coin*price

    def buy_fraction(self, fraction: float = TARGET_RISK):
        price = self._current_price()
        if self.mode=="LIVE":
            krw, _ = self.balances()
            amt = int(krw * fraction)
            if amt < MIN_ORDER_KRW: return False, "KRW 부족/최소주문 미만"
            resp = self.upbit.buy_market_order(TICKER, amt)
            _log("BUY", price, *self.balances(), self.portfolio_value(price), self.mode)
            return True, resp
        else:
            amt = self.wallet.krw*fraction
            if amt < MIN_ORDER_KRW: return False, "KRW 부족"
            qty = (amt*(1-TAKER_FEE)) / (price*(1+SLIPPAGE))
            self.wallet.krw -= amt; self.wallet.coin += qty
            _log("BUY", price, self.wallet.krw, self.wallet.coin, self.wallet.value(price), self.mode)
            return True, {"status":"paper_ok"}

    def sell_fraction(self, fraction: float = TARGET_RISK):
        price = self._current_price()
        if self.mode=="LIVE":
            _, coin = self.balances()
            qty = max(0.0, coin*fraction)
            if qty <= 0: return False, "코인 부족"
            qty = float(f"{qty:.6f}")
            resp = self.upbit.sell_market_order(TICKER, qty)
            _log("SELL", price, *self.balances(), self.portfolio_value(price), self.mode)
            return True, resp
        else:
            qty = self.wallet.coin*fraction
            if qty <= 0: return False, "코인 부족"
            krw = qty * price * (1-SLIPPAGE) * (1-TAKER_FEE)
            self.wallet.coin -= qty; self.wallet.krw += krw
            _log("SELL", price, self.wallet.krw, self.wallet.coin, self.wallet.value(price), self.mode)
            return True, {"status":"paper_ok"}
