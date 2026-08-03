from __future__ import annotations

import pandas as pd

from v2.scripts.signal_catalog import compute_a4


def test_a4_falls_back_to_close_times_volume_when_trading_value_is_missing() -> None:
    ohlcv = pd.DataFrame(
        {
            "close": [100.0] * 60,
            "volume": [10.0] * 60,
            "trading_value": [1000.0] * 59 + [float("nan")],
        }
    )

    signal = compute_a4(ohlcv, None, None)

    assert pd.notna(signal.iloc[-1])
