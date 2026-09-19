from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts import signal_catalog as catalog  # noqa: E402


def refresh_a4_signal() -> dict[str, object]:
    warnings.filterwarnings(
        "ignore",
        message="Downcasting object dtype arrays on .fillna",
        category=FutureWarning,
        module="v2.scripts.signal_catalog",
    )
    spec = next(item for item in catalog.SIGNAL_CATALOG if item.signal_id == "A4")
    raw = catalog.compute_raw_signal(
        spec,
        catalog.load_code_list(),
        catalog.load_trading_status(),
        catalog.load_kospi(),
    )
    zscore, stats = catalog.write_signal_outputs(spec, raw)
    latest = pd.to_datetime(zscore["date"]).max().normalize()
    latest_non_nan = int(
        zscore.loc[pd.to_datetime(zscore["date"]).dt.normalize().eq(latest), "signal_cs_z"]
        .notna()
        .sum()
    )
    if latest_non_nan < 30:
        raise RuntimeError(
            f"A4 signal continuity failure: latest={latest.date()} latest_non_nan={latest_non_nan}"
        )
    return {
        **stats,
        "latest_date": latest.strftime("%Y-%m-%d"),
        "latest_non_nan": latest_non_nan,
    }


def main() -> None:
    print(json.dumps(refresh_a4_signal(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
