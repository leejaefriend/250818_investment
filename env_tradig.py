import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

class SimpleTradingEnv(gym.Env):
    """
    obs: [ret1, ret3, ret6, vol_z, ma_diff, cash_ratio, coin_ratio]
    act: 0=Sell, 1=Hold, 2=Buy  (각각 TARGET_RISK만큼 조절)
    reward: 포트폴리오 가치 수익률(수수료/슬리피지 반영)
    """
    metadata = {"render_modes": []}

    def __init__(self, feats: pd.DataFrame, fee=0.0005, slippage=0.0005, base_krw=1_000_000, target_risk=0.25):
        super().__init__()
        self.df = feats
        self.prices = feats["close"].values.astype(np.float64)
        self.X = feats[["ret1", "ret3", "ret6", "vol_z", "ma_diff"]].values.astype(np.float32)
        self.n = len(self.df)
        self.fee = fee; self.slippage = slippage
        self.base_krw = float(base_krw); self.target_risk = float(target_risk)
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32)
        self.reset_state(); self.i = 0

    def reset_state(self):
        self.cash = float(self.base_krw); self.coin = 0.0; self.prev_value = float(self.base_krw)

    def _obs(self):
        price = float(self.prices[self.i])
        value = self.cash + self.coin * price + 1e-9
        cash_ratio = self.cash / value
        return np.array([*self.X[self.i], cash_ratio, 1.0 - cash_ratio], dtype=np.float32)

    def step(self, action):
        price = float(self.prices[self.i]); done = False
        if action == 2:  # Buy
            amt = self.cash * self.target_risk
            if amt > 0:
                qty = (amt * (1 - self.fee)) / (price * (1 + self.slippage))
                self.cash -= amt; self.coin += qty
        elif action == 0:  # Sell
            qty = self.coin * self.target_risk
            if qty > 0:
                krw = qty * price * (1 - self.slippage) * (1 - self.fee)
                self.coin -= qty; self.cash += krw

        self.i += 1
        if self.i >= self.n - 1: done = True; self.i = self.n - 1
        value = self.cash + self.coin * float(self.prices[self.i])
        reward = (value - self.prev_value) / (self.prev_value + 1e-9)
        self.prev_value = value
        return self._obs(), float(reward), done, False, {"value": value}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed); self.reset_state(); self.i = 0; self.prev_value = self.base_krw
        return self._obs(), {}
