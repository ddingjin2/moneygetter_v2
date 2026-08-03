from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRICE_DIR = ROOT / "data/cache/price_market_cap_full"
ACCOUNT_DIR = ROOT / "data/cache/paper_trading/a4_20d_top10"
REPORT_PATH = ROOT / "reports/paper_trading_quality_gate.md"


def atomic_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def latest_panel() -> tuple[pd.Timestamp, pd.DataFrame]:
    frames=[]
    for p in PRICE_DIR.glob("[0-9][0-9][0-9][0-9][0-9][0-9].parquet"):
        f=pd.read_parquet(p, columns=["date","symbol","name","open","high","low","close","volume","trading_value"])
        f["code"]=p.stem; frames.append(f)
    panel=pd.concat(frames,ignore_index=True)
    panel["date"]=pd.to_datetime(panel.date).dt.normalize()
    for c in ["open","high","low","close","volume","trading_value"]: panel[c]=pd.to_numeric(panel[c],errors="coerce")
    latest=panel.date.max()
    return pd.Timestamp(latest), panel[panel.date.eq(latest)].copy()


def run_gate(max_bad_price_ratio: float, min_universe: int) -> dict:
    latest, d = latest_panel()
    universe_count=int(len(d))
    bad_price=d[["open","high","low","close"]].isna().any(axis=1) | d["close"].le(0)
    zero_vol=d["volume"].fillna(0).le(0)
    bad_ratio=float(bad_price.mean()) if universe_count else 1.0
    zero_vol_ratio=float(zero_vol.mean()) if universe_count else 1.0
    account_exists=(ACCOUNT_DIR/"account.json").exists()
    state={}
    if (ACCOUNT_DIR/"latest_state.json").exists():
        state=json.loads((ACCOUNT_DIR/"latest_state.json").read_text(encoding="utf-8"))
    checks={
        "latest_price_date": latest.strftime("%Y-%m-%d"),
        "universe_count": universe_count,
        "bad_price_count": int(bad_price.sum()),
        "bad_price_ratio": bad_ratio,
        "zero_volume_count": int(zero_vol.sum()),
        "zero_volume_ratio": zero_vol_ratio,
        "account_exists": account_exists,
        "last_order_asof": state.get("asof_date"),
    }
    failures=[]
    if universe_count < min_universe: failures.append(f"universe_count<{min_universe}")
    if bad_ratio > max_bad_price_ratio: failures.append(f"bad_price_ratio>{max_bad_price_ratio}")
    if not account_exists: failures.append("missing_paper_account")
    checks["pass"] = not failures
    checks["failures"] = failures
    return checks


def main() -> None:
    parser=argparse.ArgumentParser(description="Quality gate for A4 paper/live operation.")
    parser.add_argument("--max-bad-price-ratio",type=float,default=0.02)
    parser.add_argument("--min-universe",type=int,default=700)
    parser.add_argument("--strict",action="store_true",help="Exit non-zero if gate fails")
    args=parser.parse_args()
    result=run_gate(args.max_bad_price_ratio,args.min_universe)
    text="# Paper trading quality gate\n\n```json\n"+json.dumps(result,ensure_ascii=False,indent=2)+"\n```\n"
    atomic_text(text,REPORT_PATH)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.strict and not result["pass"]:
        raise SystemExit(2)

if __name__=="__main__": main()
