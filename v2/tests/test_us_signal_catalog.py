from __future__ import annotations

import pandas as pd

from v2.scripts.us_signal_catalog import cs_zscore, signal_1m_reversal


def test_cs_zscore_is_cross_sectional_by_date() -> None:
    frame = pd.DataFrame({"date": ["2024-01-02"] * 3, "symbol": ["A", "B", "C"], "signal_value": [1.0, 2.0, 3.0]})

    out = cs_zscore(frame)

    assert round(float(out["signal_cs_z"].mean()), 12) == 0.0


def test_signal_1m_reversal_is_negative_lookback_return() -> None:
    close = pd.Series([100.0] * 21 + [110.0])
    frame = pd.DataFrame({"adj_close": close})

    out = signal_1m_reversal(frame)

    assert round(float(out.iloc[-1]), 6) == -0.1
