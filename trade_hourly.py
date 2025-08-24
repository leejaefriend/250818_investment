from __future__ import annotations

import numpy as np
import torch as th

from config import TICKER, INTERVAL, MODEL_PATH, DECISION_LOG_PATH
from data import load_ohlcv, make_features
from model_io import load_model
from upbit_exec import UpbitExec
from scheduler import sleep_until_next_bar
from decision_logger import log_decision


def last_obs(exec_: UpbitExec):
    """
    최신 캔들로부터 상태 벡터와 설명용 컨텍스트를 반환.
    minute1에서도 충분한 창을 확보하도록 count를 넉넉히 요청.
    """
    count = 180 if INTERVAL.lower().startswith("minute") else 120
    raw = load_ohlcv(TICKER, INTERVAL, count=count + 25)
    feats = make_features(raw)
    price = float(feats["close"].iloc[-1])

    krw, coin = exec_.balances()
    krw = float(krw)
    coin = float(coin)
    value = krw + coin * price + 1e-9
    cash_ratio = krw / value
    coin_ratio = 1.0 - cash_ratio

    ret1 = float(feats["ret1"].iloc[-1])
    ret3 = float(feats["ret3"].iloc[-1])
    ret6 = float(feats["ret6"].iloc[-1])
    vol_z = float(feats["vol_z"].iloc[-1])
    ma_diff = float(feats["ma_diff"].iloc[-1])

    x = np.array([ret1, ret3, ret6, vol_z, ma_diff], dtype=np.float32)
    obs = np.concatenate([x, np.array([cash_ratio, coin_ratio], dtype=np.float32)], axis=0).reshape(1, -1)

    ctx = {
        "price": price, "krw": krw, "coin": coin, "value": value,
        "ret1": ret1, "ret3": ret3, "ret6": ret6, "vol_z": vol_z, "ma_diff": ma_diff,
        "cash_ratio": cash_ratio, "coin_ratio": coin_ratio,
    }
    return obs, ctx


def explain_policy(model, obs):
    """
    PPO 정책에서 행동 확률과 V(s)를 추출.
    반환: (chosen_action, probs(np.array[3]), v_pred(float))
    """
    device = model.device
    obs_th = th.as_tensor(obs, dtype=th.float32, device=device)
    # 분포(Discrete: Categorical)와 V(s)
    dist = model.policy.get_distribution(obs_th)
    probs = dist.distribution.probs.detach().cpu().numpy().reshape(-1)  # [n_actions]
    v_pred = model.policy.predict_values(obs_th).detach().cpu().numpy().reshape(-1)[0]
    # deterministic=True와 일치하도록 최대확률 행동
    chosen = int(np.argmax(probs))
    return chosen, probs, float(v_pred)


def fallback_rule(exec_) -> tuple[int, str]:
    """
    모델이 없을 때 안전장치 (간단 추세 룰)와 이유 문자열.
    - MA(5) > MA(20): Buy
    - MA(5) < MA(20): Sell
    - else: Hold
    """
    raw = load_ohlcv(TICKER, INTERVAL, count=25)
    df = make_features(raw)
    last = df.iloc[-1]
    if last["ma_fast"] > last["ma_slow"]:
        return 2, "fallback: ma_fast > ma_slow → BUY"
    if last["ma_fast"] < last["ma_slow"]:
        return 0, "fallback: ma_fast < ma_slow → SELL"
    return 1, "fallback: ma_fast ≈ ma_slow → HOLD"


def main(loop=True):
    model = load_model(MODEL_PATH)
    ex = UpbitExec()
    print(f"MODE={ex.mode}  TICKER={TICKER}  INTERVAL={INTERVAL}")

    while True:
        # INTERVAL에 맞춰 다음 캔들 시각까지 대기
        target = sleep_until_next_bar(INTERVAL)
        print(f"== {target.isoformat()} 캔들 시각 실행 ==")

        # 관측/의사결정
        try:
            obs, ctx = last_obs(ex)
        except Exception as e:
            print("데이터 준비 실패:", e)
            if not loop:
                break
            continue

        if model is not None:
            action, probs, v_pred = explain_policy(model, obs)
            reason = f"π(a|s)=[sell:{probs[0]:.3f}, hold:{probs[1]:.3f}, buy:{probs[2]:.3f}], V(s)={v_pred:.6f}"
        else:
            action, reason = fallback_rule(ex)
            probs = np.array([np.nan, np.nan, np.nan], dtype=float)
            v_pred = np.nan

        # 콘솔에 근거 출력
        action_name = ["SELL(0)", "HOLD(1)", "BUY(2)"][action]
        print(
            f"ACTION={action_name} | {reason} | "
            f"price={ctx['price']:.0f}, value={ctx['value']:.0f}, "
            f"ret1={ctx['ret1']:.4f}, ma_diff={ctx['ma_diff']:.4f}, cash={ctx['cash_ratio']:.3f}"
        )

        # 의사결정 로그 남기기
        log_decision(
            DECISION_LOG_PATH,
            {
                "ts": target.isoformat(),
                "mode": ex.mode,
                "ticker": TICKER,
                "interval": INTERVAL,
                "price": ctx["price"],
                "krw": ctx["krw"],
                "coin": ctx["coin"],
                "portfolio_value": ctx["value"],
                "action": action,
                "reason": reason,
                "v_pred": v_pred,
                "p_sell": probs[0] if np.isfinite(probs[0]) else "",
                "p_hold": probs[1] if np.isfinite(probs[1]) else "",
                "p_buy": probs[2] if np.isfinite(probs[2]) else "",
                "ret1": ctx["ret1"],
                "ret3": ctx["ret3"],
                "ret6": ctx["ret6"],
                "vol_z": ctx["vol_z"],
                "ma_diff": ctx["ma_diff"],
                "cash_ratio": ctx["cash_ratio"],
                "coin_ratio": ctx["coin_ratio"],
            },
        )

        # 주문 실행
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
