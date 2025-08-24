from __future__ import annotations

import csv
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

def log_decision(path: str, row: Dict[str, Any]):
    """
    의사결정(관측, 확률, V값, 행동, 이유) 로그를 CSV로 남긴다.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    file_exists = os.path.exists(path)
    header = [
        "ts", "mode", "ticker", "interval",
        "price", "krw", "coin", "portfolio_value",
        "action", "reason",
        "v_pred", "p_sell", "p_hold", "p_buy",
        "ret1", "ret3", "ret6", "vol_z", "ma_diff",
        "cash_ratio", "coin_ratio",
    ]
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in header})
