from __future__ import annotations

import argparse
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from config import (
    TICKER,
    INTERVAL,
    MODEL_PATH,
    BASE_KRW,
    TAKER_FEE,
    SLIPPAGE,
    TARGET_RISK,
)
from data import load_ohlcv, make_features
from env_trading import SimpleTradingEnv
from model_io import save_model


def _defaults_for_interval(interval: str) -> tuple[int, int]:
    """
    인터벌에 따라 기본 학습 길이(timesteps)와 데이터 길이(count)를 추천.
    - count는 pyupbit.get_ohlcv의 제약을 고려해 보수적으로 설정 (필요시 직접 늘려도 됨)
    """
    low = interval.lower()
    if low.startswith("minute1"):
        # 1분봉: 노이즈가 커서 스텝을 조금 더 확보
        return 300_000, 200  # (timesteps, count)
    if low.startswith("minute5"):
        return 250_000, 200
    if low.startswith("minute15"):
        return 200_000, 200
    if low.startswith("minute60") or low in ("hour", "hourly"):
        return 150_000, 200
    if low == "day":
        return 100_000, 200
    # 기본값
    return 200_000, 200


def main(timesteps: int | None = None, count: int | None = None):
    # 인터벌을 보고 기본값 결정
    d_timesteps, d_count = _defaults_for_interval(INTERVAL)
    timesteps = timesteps or d_timesteps
    count = count or d_count

    # 데이터 로드 & 피처 생성
    raw = load_ohlcv(TICKER, INTERVAL, count=count)
    feats = make_features(raw)

    # Gym 환경 래핑
    env_fn = lambda: SimpleTradingEnv(
        feats,
        fee=TAKER_FEE,
        slippage=SLIPPAGE,
        base_krw=BASE_KRW,
        target_risk=TARGET_RISK,
    )
    env = DummyVecEnv([env_fn])

    # PPO (CPU 전용)
    model = PPO("MlpPolicy", env, verbose=1, device="cpu")

    # 학습
    model.learn(total_timesteps=timesteps)

    # 저장 (인터벌별 파일명 자동)
    save_model(model, MODEL_PATH)
    print(f"[OK] Saved model to {MODEL_PATH} (interval={INTERVAL}, timesteps={timesteps}, count={count})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--timesteps", type=int, default=None, help="학습 총 스텝 수(미지정시 INTERVAL 기본값)")
    ap.add_argument("--count", type=int, default=None, help="OHLCV 길이(미지정시 INTERVAL 기본값)")
    args = ap.parse_args()
    main(args.timesteps, args.count)
