from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd


TRADE_CACHE_DIR = Path("v2/data/cache/trades")
LEDGER_COLUMNS = [
    "trade_id",
    "variant",
    "fold",
    "stock_code",
    "entry_date",
    "exit_date",
    "holding_days",
    "entry_price",
    "exit_price",
    "raw_return",
    "net_return",
    "pnl_krw",
    "sue_value",
    "proximity_value",
    "exit_reason",
    "position_size",
]


@dataclass(frozen=True)
class LedgerWriteResult:
    timestamped_path: Path
    latest_path: Path
    rows: int


def run_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _feature_lookup(signals: pd.DataFrame | None) -> pd.DataFrame:
    if signals is None or signals.empty:
        return pd.DataFrame(columns=["stock_code", "entry_date", "sue_value", "proximity_value"])

    frame = signals.copy()
    frame["stock_code"] = frame["symbol"].astype(str).str.zfill(6)
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.normalize()
    if "sue_score" in frame.columns:
        frame["sue_value"] = pd.to_numeric(frame["sue_score"], errors="coerce")
    elif "signal_score" in frame.columns:
        frame["sue_value"] = pd.to_numeric(frame["signal_score"], errors="coerce")
    else:
        frame["sue_value"] = pd.NA
    if "proximity" in frame.columns:
        frame["proximity_value"] = pd.to_numeric(frame["proximity"], errors="coerce")
    else:
        frame["proximity_value"] = pd.NA
    return frame[["stock_code", "entry_date", "sue_value", "proximity_value"]].drop_duplicates(
        ["stock_code", "entry_date"],
        keep="first",
    )


def _normalize_ledger(
    ledger: pd.DataFrame,
    *,
    variant: str,
    fold: int,
    initial_cash: float,
    signals: pd.DataFrame | None,
) -> pd.DataFrame:
    if ledger.empty:
        return pd.DataFrame(columns=LEDGER_COLUMNS)

    frame = ledger.copy()
    frame["stock_code"] = frame["symbol"].astype(str).str.zfill(6)
    frame["entry_date"] = pd.to_datetime(frame["entry_date"]).dt.normalize()
    frame["exit_date"] = pd.to_datetime(frame["exit_date"]).dt.normalize()
    frame = frame.sort_values(["entry_date", "stock_code", "exit_date"]).reset_index(drop=True)
    frame = frame.merge(_feature_lookup(signals), on=["stock_code", "entry_date"], how="left")
    if "sue_value" not in frame.columns:
        frame["sue_value"] = pd.to_numeric(frame.get("signal_score"), errors="coerce")
    frame["proximity_value"] = pd.to_numeric(frame.get("proximity_value"), errors="coerce")

    entry_price = pd.to_numeric(frame["entry_price"], errors="coerce")
    exit_price = pd.to_numeric(frame["exit_price"], errors="coerce")
    quantity = pd.to_numeric(frame["quantity"], errors="coerce")
    gross_notional = entry_price * quantity

    normalized = pd.DataFrame(
        {
            "trade_id": [
                f"{variant}|{fold}|{row.stock_code}|{row.entry_date:%Y-%m-%d}|{row.exit_date:%Y-%m-%d}|{index:05d}"
                for index, row in frame.iterrows()
            ],
            "variant": variant,
            "fold": int(fold),
            "stock_code": frame["stock_code"],
            "entry_date": frame["entry_date"],
            "exit_date": frame["exit_date"],
            "holding_days": pd.to_numeric(frame["holding_trading_days"], errors="coerce").astype("Int64"),
            "entry_price": entry_price.astype("float64"),
            "exit_price": exit_price.astype("float64"),
            "raw_return": (exit_price / entry_price - 1.0).astype("float64"),
            "net_return": pd.to_numeric(frame["return_pct"], errors="coerce").astype("float64"),
            "pnl_krw": pd.to_numeric(frame["pnl"], errors="coerce").astype("float64"),
            "sue_value": pd.to_numeric(frame["sue_value"], errors="coerce").astype("float64"),
            "proximity_value": frame["proximity_value"].astype("float64"),
            "exit_reason": frame["exit_reason"].astype(str),
            "position_size": (gross_notional / float(initial_cash)).astype("float64"),
        }
    )
    return normalized[LEDGER_COLUMNS]


def write_trade_ledger(
    ledgers: Iterable[tuple[int, pd.DataFrame]],
    *,
    pr_tag: str,
    variant: str,
    run_ts: str,
    initial_cash: float,
    signals: pd.DataFrame | None = None,
    output_dir: Path = TRADE_CACHE_DIR,
) -> LedgerWriteResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = [
        _normalize_ledger(
            ledger,
            variant=variant,
            fold=fold,
            initial_cash=initial_cash,
            signals=signals,
        )
        for fold, ledger in ledgers
    ]
    data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=LEDGER_COLUMNS)
    data = data.sort_values(["fold", "entry_date", "stock_code", "exit_date", "trade_id"]).reset_index(drop=True)

    slug = variant.lower()
    timestamped_path = output_dir / f"{pr_tag}_{slug}_{run_ts}.parquet"
    latest_path = output_dir / f"{pr_tag}_{slug}_latest.parquet"
    data.to_parquet(timestamped_path, index=False)
    shutil.copyfile(timestamped_path, latest_path)
    return LedgerWriteResult(timestamped_path=timestamped_path, latest_path=latest_path, rows=len(data))
