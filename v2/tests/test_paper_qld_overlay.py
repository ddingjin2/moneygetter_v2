import math

import numpy as np
import pandas as pd

from scripts.paper_qld_overlay import MA_WINDOW, VOL_TARGET, target_weight


def make_df(qqq_last: float, qld_daily_vol: float, n: int = 300) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=n)
    rng = np.random.default_rng(0)
    qld = 50.0 * np.cumprod(1.0 + rng.normal(0.0, qld_daily_vol, n))
    qqq = np.full(n, 500.0)
    qqq[-1] = qqq_last
    return pd.DataFrame({"qld_open": qld, "qld_close": qld, "qqq_close": qqq, "irx": 0.04}, index=idx)


def test_risk_off_when_below_ma():
    w, detail = target_weight(make_df(qqq_last=400.0, qld_daily_vol=0.01))
    assert w == 0.0 and not detail["risk_on"]


def test_risk_on_full_weight_when_low_vol():
    w, detail = target_weight(make_df(qqq_last=600.0, qld_daily_vol=0.005))
    assert detail["risk_on"] and w == 1.0


def test_vol_target_caps_weight():
    df = make_df(qqq_last=600.0, qld_daily_vol=0.04)  # ~63% ann vol > 45% target
    w, detail = target_weight(df)
    assert detail["risk_on"]
    assert 0.0 < w < 1.0
    assert math.isclose(w, min(1.0, VOL_TARGET / detail["vol20_ann"]), rel_tol=1e-9)


def test_ma_window_respected():
    df = make_df(qqq_last=600.0, qld_daily_vol=0.01)
    assert len(df) >= MA_WINDOW
