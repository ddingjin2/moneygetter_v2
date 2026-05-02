from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.scripts.signal_catalog import SIGNAL_CATALOG  # noqa: E402


SIGNALS_DIR = ROOT / "v2/data/cache/signals_batch"
IC_FULL_PATH = ROOT / "v2/data/cache/ic/ic_batch_full.parquet"
IC_SUMMARY_PATH = ROOT / "v2/data/cache/ic/ic_batch_summary.parquet"
OUTPUT_DIR = ROOT / "v2/data/cache/correlation"
CS_CORR_PATH = OUTPUT_DIR / "signal_cs_correlation.parquet"
IC_CORR_PATH = OUTPUT_DIR / "signal_ic_correlation.parquet"
CLUSTERS_PATH = OUTPUT_DIR / "signal_clusters.parquet"
REPORT_PATH = ROOT / "v2/reports/pr7_a_X_step8_3_correlation.md"

THRESHOLDS = [0.3, 0.5, 0.7]


def atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    frame.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def signal_ids() -> list[str]:
    return [spec.signal_id for spec in SIGNAL_CATALOG]


def load_signal(signal_id: str) -> pd.DataFrame:
    path = SIGNALS_DIR / f"{signal_id}_cs_zscore.parquet"
    if not path.exists():
        raise RuntimeError(f"Missing signal z-score file: {path}")
    frame = pd.read_parquet(path)
    frame["code"] = frame["code"].astype(str).str.zfill(6)
    frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
    return frame[["code", "date", "signal_cs_z"]].rename(columns={"signal_cs_z": signal_id})


def cross_sectional_corr_pair(left: pd.DataFrame, right: pd.DataFrame, left_id: str, right_id: str) -> dict[str, object]:
    if left_id == right_id:
        valid_dates = left.loc[left[left_id].notna()].groupby("date", sort=False).size()
        n_days = int(valid_dates.ge(30).sum())
        return {
            "signal_i": left_id,
            "signal_j": right_id,
            "mean_corr_signal": 1.0,
            "std_corr_signal": 0.0,
            "n_days_common": n_days,
        }
    merged = left.merge(right, on=["code", "date"], how="inner")
    valid = merged[left_id].notna() & merged[right_id].notna()
    daily: list[float] = []
    for _, group in merged.loc[valid, ["date", left_id, right_id]].groupby("date", sort=True):
        if len(group) < 30:
            continue
        corr = group[left_id].rank().corr(group[right_id].rank())
        if pd.notna(corr):
            daily.append(float(corr))
    return {
        "signal_i": left_id,
        "signal_j": right_id,
        "mean_corr_signal": float(np.mean(daily)) if daily else math.nan,
        "std_corr_signal": float(np.std(daily, ddof=1)) if len(daily) > 1 else math.nan,
        "n_days_common": int(len(daily)),
    }


def compute_cross_sectional_correlations(ids: list[str]) -> pd.DataFrame:
    signals = {signal_id: load_signal(signal_id) for signal_id in ids}
    rows: list[dict[str, object]] = []
    for left_id in ids:
        for right_id in ids:
            rows.append(cross_sectional_corr_pair(signals[left_id], signals[right_id], left_id, right_id))
    return pd.DataFrame(rows)


def compute_ic_correlations(ids: list[str]) -> pd.DataFrame:
    ic = pd.read_parquet(IC_FULL_PATH)
    ic["date"] = pd.to_datetime(ic["date"]).dt.normalize()
    ic_5d = ic.loc[ic["horizon"].eq("5d"), ["signal_id", "date", "ic"]]
    by_signal = {
        signal_id: frame[["date", "ic"]].rename(columns={"ic": signal_id})
        for signal_id, frame in ic_5d.groupby("signal_id", sort=False)
    }
    rows: list[dict[str, object]] = []
    for left_id in ids:
        for right_id in ids:
            if left_id == right_id:
                series = by_signal[left_id][left_id].dropna()
                n = int(len(series))
                corr = 1.0 if n >= 2 else math.nan
            else:
                merged = by_signal[left_id].merge(by_signal[right_id], on="date", how="inner")
                valid = merged[left_id].notna() & merged[right_id].notna()
                n = int(valid.sum())
                left_values = merged.loc[valid, left_id]
                right_values = merged.loc[valid, right_id]
                if n >= 2 and left_values.std(ddof=0) > 0 and right_values.std(ddof=0) > 0:
                    corr = float(left_values.corr(right_values))
                else:
                    corr = math.nan
            rows.append(
                {
                    "signal_i": left_id,
                    "signal_j": right_id,
                    "horizon": "5d",
                    "ic_corr": corr,
                    "n_days_common_ic": n,
                }
            )
    return pd.DataFrame(rows)


def average_distance(cluster_a: set[str], cluster_b: set[str], distance: dict[tuple[str, str], float]) -> float:
    values = [distance[(a, b)] for a in cluster_a for b in cluster_b if a != b]
    return float(np.mean(values)) if values else 0.0


def average_linkage_groups(ids: list[str], cs_corr: pd.DataFrame, threshold: float) -> dict[str, int]:
    distance_threshold = 1.0 - threshold
    distance: dict[tuple[str, str], float] = {}
    for row in cs_corr.itertuples(index=False):
        corr = 0.0 if pd.isna(row.mean_corr_signal) else abs(float(row.mean_corr_signal))
        distance[(row.signal_i, row.signal_j)] = 1.0 - corr
    clusters: list[set[str]] = [{signal_id} for signal_id in ids]
    while True:
        best_pair: tuple[int, int] | None = None
        best_distance = math.inf
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                dist = average_distance(clusters[i], clusters[j], distance)
                if dist < best_distance:
                    best_distance = dist
                    best_pair = (i, j)
        if best_pair is None or best_distance > distance_threshold:
            break
        i, j = best_pair
        clusters[i] = clusters[i] | clusters[j]
        del clusters[j]
    clusters = sorted(clusters, key=lambda members: sorted(members)[0])
    group_map: dict[str, int] = {}
    for idx, members in enumerate(clusters, start=1):
        for signal_id in sorted(members):
            group_map[signal_id] = idx
    return group_map


def compute_clusters(ids: list[str], cs_corr: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for threshold in THRESHOLDS:
        groups = average_linkage_groups(ids, cs_corr, threshold)
        for signal_id in ids:
            rows.append({"signal_id": signal_id, "threshold": threshold, "group_id": int(groups[signal_id])})
    return pd.DataFrame(rows)


def matrix_table(frame: pd.DataFrame, value_col: str, ids: list[str]) -> pd.DataFrame:
    matrix = frame.pivot(index="signal_i", columns="signal_j", values=value_col).reindex(index=ids, columns=ids)
    matrix = matrix.reset_index().rename(columns={"signal_i": "signal_id"})
    return matrix


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, *, max_rows: int | None = None) -> str:
    out = frame.copy()
    if columns is not None:
        out = out.loc[:, columns]
    if max_rows is not None:
        out = out.head(max_rows)
    cols = list(out.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for row in out.itertuples(index=False):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("NA" if math.isnan(value) else f"{value:.4f}")
            elif pd.isna(value):
                values.append("NA")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def group_members_table(clusters: pd.DataFrame, threshold: float) -> str:
    frame = clusters.loc[clusters["threshold"].eq(threshold)].copy()
    rows = []
    for group_id, group in frame.groupby("group_id", sort=True):
        rows.append({"group_id": f"group_{group_id}", "members": ", ".join(group["signal_id"].tolist())})
    return markdown_table(pd.DataFrame(rows), ["group_id", "members"])


def group_ic_table(clusters: pd.DataFrame, summary: pd.DataFrame) -> str:
    summary_5d = summary.loc[summary["horizon"].eq("5d"), ["signal_id", "mean_ic", "t_stat"]]
    rows = []
    for threshold in THRESHOLDS:
        merged = clusters.loc[clusters["threshold"].eq(threshold)].merge(summary_5d, on="signal_id", how="left")
        for group_id, group in merged.groupby("group_id", sort=True):
            members = [
                f"{row.signal_id}(mean_ic={row.mean_ic:.4f}, t={row.t_stat:.2f})"
                for row in group.sort_values("signal_id").itertuples()
            ]
            rows.append({"threshold": threshold, "group_id": f"group_{group_id}", "members_5d_ic": ", ".join(members)})
    return markdown_table(pd.DataFrame(rows), ["threshold", "group_id", "members_5d_ic"])


def write_report(cs_corr: pd.DataFrame, ic_corr: pd.DataFrame, clusters: pd.DataFrame) -> None:
    ids = signal_ids()
    cs_matrix = matrix_table(cs_corr, "mean_corr_signal", ids)
    ic_matrix = matrix_table(ic_corr, "ic_corr", ids)
    high_pairs = cs_corr.loc[cs_corr["signal_i"].lt(cs_corr["signal_j"])].copy()
    high_pairs["abs_corr"] = high_pairs["mean_corr_signal"].abs()
    high_pairs = high_pairs.loc[high_pairs["abs_corr"].ge(0.5)].sort_values("abs_corr", ascending=False)
    summary = pd.read_parquet(IC_SUMMARY_PATH)
    text = f"""# PR-7.A.X Step 8.3 Signal Correlation & Grouping

## 1. Scope & Setup
- 21 signals x 21 signals cross-sectional rank correlation (Spearman) on cs_z.
- IC time-series correlation (Pearson) on 5d IC.
- Hierarchical clustering: average linkage, distance = 1 - |mean_corr|.
- Cut thresholds reported: 0.3, 0.5, 0.7. Cut decision is user-owned.

## 2. Cross-sectional Signal Correlation Matrix (21x21)
{markdown_table(cs_matrix)}

## 3. Notable High-correlation Pairs
{markdown_table(high_pairs, ["signal_i", "signal_j", "mean_corr_signal", "std_corr_signal", "n_days_common"])}

## 4. IC Time-series Correlation (5d)
{markdown_table(ic_matrix)}

## 5. Hierarchical Clustering Results

### 5.1 Cut at |corr| >= 0.3 (loose)
{group_members_table(clusters, 0.3)}

### 5.2 Cut at |corr| >= 0.5 (medium)
{group_members_table(clusters, 0.5)}

### 5.3 Cut at |corr| >= 0.7 (strict)
{group_members_table(clusters, 0.7)}

## 6. Cross-reference: Group vs 5d Mean IC
{group_ic_table(clusters, summary)}

## 7. Caveats
- Sparse signals such as C3, C2, and C5 use common valid dates only; `n_days_common` is reported.
- Raw cs_z is used with no post-hoc sign flip. Opposite-direction signals appear as negative correlations.
- Cross-sectional signal correlation and IC time-series correlation measure different relationships.
- Cluster cut decision is user-owned.
- scipy is unavailable in this environment, so average-linkage clustering is implemented directly with the same distance definition.

## 8. Artifacts
- `v2/data/cache/correlation/signal_cs_correlation.parquet`
- `v2/data/cache/correlation/signal_ic_correlation.parquet`
- `v2/data/cache/correlation/signal_clusters.parquet`

## Gate
Step 8.3 raw measurement complete. Group cut decision and representative signal selection are user-owned after reviewing these results.
"""
    atomic_write_text(text, REPORT_PATH)


def run() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ids = signal_ids()
    cs_corr = compute_cross_sectional_correlations(ids)
    ic_corr = compute_ic_correlations(ids)
    clusters = compute_clusters(ids, cs_corr)
    atomic_write_parquet(cs_corr, CS_CORR_PATH)
    atomic_write_parquet(ic_corr, IC_CORR_PATH)
    atomic_write_parquet(clusters, CLUSTERS_PATH)
    write_report(cs_corr, ic_corr, clusters)
    high_pairs = cs_corr.loc[cs_corr["signal_i"] < cs_corr["signal_j"], "mean_corr_signal"].abs()
    high_pair_count = int(high_pairs.ge(0.5).sum())
    return {
        "cs_corr_rows": int(len(cs_corr)),
        "ic_corr_rows": int(len(ic_corr)),
        "cluster_rows": int(len(clusters)),
        "high_pair_count_abs_ge_0_5": high_pair_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PR-7.A.X Step 8.3 signal correlation analysis.")
    parser.add_argument("--run", action="store_true", help="Write Step 8.3 correlation artifacts and report.")
    args = parser.parse_args()
    if not args.run:
        print("signals", len(signal_ids()))
        print("pair_rows", len(signal_ids()) * len(signal_ids()))
        print("thresholds", ",".join(str(x) for x in THRESHOLDS))
        return
    print(run())


if __name__ == "__main__":
    main()
