from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from config import TICKER, INTERVAL, MODEL_PATH, BASE_KRW, TAKER_FEE, SLIPPAGE, TARGET_RISK
from data import load_ohlcv, make_features
from env_trading import SimpleTradingEnv

def main(timesteps=100_000, count=200):
    raw = load_ohlcv(TICKER, INTERVAL, count=count)
    feats = make_features(raw)
    env_fn = lambda: SimpleTradingEnv(feats, fee=TAKER_FEE, slippage=SLIPPAGE,
                                      base_krw=BASE_KRW, target_risk=TARGET_RISK)
    env = DummyVecEnv([env_fn])
    model = PPO("MlpPolicy", env, verbose=1, device="cpu", tensorboard_log="tb/")
    model.learn(total_timesteps=timesteps)
    from model_io import save_model
    save_model(model, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")

if __name__ == "__main__":
    main()
