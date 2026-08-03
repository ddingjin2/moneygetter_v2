from __future__ import annotations

import pandas as pd

from v2.scripts.us_run_backtest_batch import korean_tax_policy_lines, weights_from_signal


def test_weights_from_signal_long_only_decile_uses_top_names() -> None:
    values = pd.Series(range(100), index=[f"S{i:03d}" for i in range(100)], dtype="float64")

    weights = weights_from_signal(values, "LO_decile")

    assert weights.gt(0).sum() == 10
    assert weights.loc["S099"] == 0.1
    assert weights.loc["S000"] == 0.0


def test_weights_from_signal_long_short_decile_is_dollar_neutral() -> None:
    values = pd.Series(range(100), index=[f"S{i:03d}" for i in range(100)], dtype="float64")

    weights = weights_from_signal(values, "LS_decile")

    assert round(float(weights.sum()), 12) == 0.0
    assert weights.gt(0).sum() == 10
    assert weights.lt(0).sum() == 10


def test_korean_tax_policy_lines_require_realistic_us_sale_tax_model() -> None:
    lines = korean_tax_policy_lines()

    joined = "\n".join(lines)
    assert "2,500,000 KRW" in joined
    assert "22%" in joined
    assert "trade-date USD/KRW FX" in joined
