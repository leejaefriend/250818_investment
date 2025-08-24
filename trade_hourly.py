from __future__ import annotations

import numpy as np

from config import TICKER, INTERVAL, MODEL_PATH
from data import load_ohlcv, make_features
from model_io import load_model
from upbit_exec import UpbitExec
from scheduler import sleep_until_next_bar


def last_obs(exec_: UpbitExec):
    """
    최신 캔들로부터 상태 벡터 구성.
    minute1에서도 과거 데이터 창을 충분히 확보하도록 count를 넉넉히 요청.
    """
    # 분봉일 경우 최소 200~300개 캔들은 확보
    count = 180 if INTERVAL.lower().startswith("minute") else 120
    raw = load_ohlcv(TICKER, INTERVAL, count=count + 25)
    feats = make_features(raw)
    price = float(feats["close"].iloc[-1])

    krw, coin = exec_.balances()
    value = float(krw) + float(coin) * price + 1e-9
    cash_ratio = float(krw) / value

    x = feats[["ret1", "ret3", "ret6", "vol_z", "ma_diff"]].iloc[-1].values.astype(np.float32)
    obs = np.concatenate([x, np.array([cash_ratio, 1.0 - cash_ratio], dtype=np.float32)], axis=0).reshape(1, -1)
    return obs


def decide(model, obs):
    act, _ = model.predict(obs, deterministic=True)
    # SB3는 array([2]) 형태를 반환할 수 있으므로 스칼라 안전 변환
    return int(np.ravel(act)[0])


def fallback_rule(exec_: UpbitExec) -> int:
    """
    모델이 없을 때 안전장치 (간단한 추세 룰):
    - MA(5) > MA(20): Buy
    - MA(5) < MA(20): Sell
    - else: Hold
    """
    raw = load_ohlcv(TICKER, INTERVAL, count=25)
    df = make_features(raw)
    last = df.iloc[-1]
    if last["ma_fast"] > last["ma_slow"]:
        return 2
    if last["ma_fast"] < last["ma_slow"]:
        return 0
    return 1


def main(loop=True):
    model = load_model(MODEL_PATH)
    ex = UpbitExec()
    print(f"MODE={ex.mode}  TICKER={TICKER}  INTERVAL={INTERVAL}")
    while True:
        # INTERVAL에 따라 다음 캔들 시각까지 대기
        target = sleep_until_next_bar(INTERVAL)
        print(f"== {target.isoformat()} 캔들 시각 실행 ==")

        # 관측/의사결정
        try:
            obs = last_obs(ex)
        except Exception as e:
            print("데이터 준비 실패:", e)
            if not loop:
                break
            continue

        action = decide(model, obs) if model is not None else fallback_rule(ex)

        if action == 2:
            ok, resp = ex.buy_fraction()
            print("BUY:", ok, resp)
        elif action == 0:
            ok, resp = ex.sell_fraction()
            print("SELL:", ok, resp)
        else:
            print("HOLD")

        if not loop:
            break


if __name__ == "__main__":
    main(loop=True)
