import pandas as pd
import pyupbit

def load_ohlcv(ticker: str, interval: str, count: int = 200):
    # Upbit OHLCV: index=datetime, columns=[open, high, low, close, volume, value]
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
    if df is None or len(df) < 50:
        raise RuntimeError("OHLCV 불러오기 실패 또는 데이터 부족")
    return df.dropna().copy()

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret1"] = out["close"].pct_change(1).fillna(0.0)
    out["ret3"] = out["close"].pct_change(3).fillna(0.0)
    out["ret6"] = out["close"].pct_change(6).fillna(0.0)
    out["vol_z"] = (out["volume"] - out["volume"].rolling(20).mean()) / (out["volume"].rolling(20).std() + 1e-9)
    out["ma_fast"] = out["close"].rolling(5).mean()
    out["ma_slow"] = out["close"].rolling(20).mean()
    out["ma_diff"] = (out["ma_fast"] - out["ma_slow"]) / (out["ma_slow"] + 1e-9)
    return out.dropna().copy()
