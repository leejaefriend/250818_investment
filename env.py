import pyupbit
import pandas as pd

class Environment:
    PRICE_IDX = 4  # 종가 index

    def __init__(self, ticker="KRW-BTC", interval="minute1", count=10000):
        self.ticker = ticker
        self.interval = interval
        self.count = count
        self.chart_data = None
        self.observation = None
        self.idx = -1

        self._load_data()

    def _load_data(self):
        df = pyupbit.get_ohlcv(self.ticker, interval=self.interval, count=self.count)
        if df is None or len(df) == 0:
            raise ValueError("Failed to fetch OHLCV data")
        df.reset_index(inplace=True)
        self.chart_data = df

    def reset(self):
        self.idx = -1
        self.observation = None

    def observe(self):
        if len(self.chart_data) > self.idx + 1:
            self.idx += 1
            self.observation = self.chart_data.iloc[self.idx]
            return self.observation
        return None

    def get_price(self):
        if self.observation is not None:
            return self.observation["close"]
        return None

    def get_volume(self):
        if self.observation is not None:
            return self.observation["volume"]
        return None
