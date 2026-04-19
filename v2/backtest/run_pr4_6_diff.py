from __future__ import annotations

import argparse
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


REPORT_PATH = Path("v2/reports/pr4_6_rerun_diff.md")
PR3_OLD = Path("v2/reports/pr3_sue_baseline_report_v1.md")
PR3_NEW = Path("v2/reports/pr3_sue_baseline_report.md")
PR4_OLD = Path("v2/reports/pr4_proximity_report_v1.md")
PR4_NEW = Path("v2/reports/pr4_proximity_report.md")


@dataclass(frozen=True)
class MetricDiff:
    scope: str
    metric: str
    old: float | int | str
    new: float | int | str
    abs_diff: float
    verdict: str


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "(empty)"
    rendered = frame.copy()
    for column in rendered.columns:
        if pd.api.types.is_float_dtype(rendered[column]):
            rendered[column] = rendered[column].map(lambda value: "" if pd.isna(value) else f"{value:.4f}")
    lines = ["| " + " | ".join(rendered.columns) + " |"]
    lines.append("| " + " | ".join(["---"] * len(rendered.columns)) + " |")
    for _, row in rendered.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in rendered.columns) + " |")
    return "\n".join(lines)


def _tables(path: Path) -> list[pd.DataFrame]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    tables: list[pd.DataFrame] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.startswith("| "):
            index += 1
            continue
        block = []
        while index < len(lines) and lines[index].startswith("| "):
            block.append(lines[index])
            index += 1
        if len(block) < 2:
            continue
        header = [part.strip() for part in block[0].strip("|").split("|")]
        rows = [
            [part.strip() for part in row.strip("|").split("|")]
            for row in block[2:]
        ]
        tables.append(pd.DataFrame(rows, columns=header))
    return tables


def _to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _to_int(value: object) -> int:
    return int(float(value))


def _pr3_metrics(path: Path) -> dict[str, float | int]:
    tables = _tables(path)
    measurement = tables[0]
    folds = tables[1]
    summary = tables[2]
    common = tables[3]
    test_70 = measurement.loc[
        measurement["period"].eq("test") & measurement["scenario"].eq("round_trip_70bps")
    ].iloc[0]
    result: dict[str, float | int] = {
        "Test trades": _to_int(test_70["trades"]),
        "Test PF (70bps)": _to_float(test_70["PF"]),
        "WF median PF": _to_float(summary.iloc[0]["pf_median"]),
        "Common trade count": _to_int(common.iloc[0]["common_trade_count"]),
        "Common trade PF": _to_float(common.iloc[0]["common_trade_pf"]),
    }
    for _, row in folds.iterrows():
        fold_id = str(row["fold_id"]).replace("fold_", "Fold_")
        result[f"{fold_id} PF"] = _to_float(row["PF"])
    return result


def _pr4_metrics(path: Path) -> dict[str, dict[str, float | int]]:
    tables = _tables(path)
    summary = tables[0]
    regime = tables[2]
    metrics: dict[str, dict[str, float | int]] = {}
    for _, row in summary.iterrows():
        variant = str(row["Variant"]).split(".", 1)[0]
        metrics[variant] = {
            "Test trades": _to_int(row["Trades"]),
            "Test PF (70bps)": _to_float(row["Test PF"]),
            "WF median PF": _to_float(row["WF Median PF"]),
            "Common trade count": _to_int(row["Common Trades"]),
            "Common trade PF": _to_float(row["Common PF"]),
        }
    for _, row in regime.iterrows():
        variant = str(row["variant"]).split(".", 1)[0]
        fold_id = str(row["fold_id"]).replace("fold_", "Fold_")
        if variant in metrics:
            metrics[variant][f"{fold_id} PF"] = _to_float(row["strategy_pf"])
    return metrics


def _verdict(metric: str, old: float | int, new: float | int) -> tuple[float, str]:
    diff = abs(float(new) - float(old))
    if "trades" in metric.lower() or "count" in metric.lower():
        return diff, "OK" if diff == 0 else "CRITICAL"
    threshold = 0.10 if "Fold_" in metric else 0.05
    return diff, "OK" if diff <= threshold else "WARN"


def _diff_rows(scope: str, old: dict[str, float | int], new: dict[str, float | int]) -> list[MetricDiff]:
    rows = []
    for metric in old:
        diff, verdict = _verdict(metric, old[metric], new[metric])
        rows.append(MetricDiff(scope, metric, old[metric], new[metric], diff, verdict))
    return rows


def _diff_frame(rows: list[MetricDiff]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scope": row.scope,
                "metric": row.metric,
                "old_v1": row.old,
                "rerun": row.new,
                "abs_diff": row.abs_diff,
                "verdict": row.verdict,
            }
            for row in rows
        ]
    )


def _git_hash() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"unavailable ({type(exc).__name__})"
    return result.stdout.strip()


def build_diff_report() -> tuple[str, pd.DataFrame]:
    pr3_old = _pr3_metrics(PR3_OLD)
    pr3_new = _pr3_metrics(PR3_NEW)
    pr4_old = _pr4_metrics(PR4_OLD)
    pr4_new = _pr4_metrics(PR4_NEW)

    rows = _diff_rows("PR-3 A baseline", pr3_old, pr3_new)
    for variant in ("A", "B", "C", "D"):
        rows.extend(_diff_rows(f"PR-4 {variant}", pr4_old[variant], pr4_new[variant]))
    diff = _diff_frame(rows)
    counts = diff["verdict"].value_counts().rename_axis("verdict").reset_index(name="count")

    lines = [
        "# PR-4.6 Rerun Diff",
        "",
        "## 6.1 Execution Info",
        _markdown_table(
            pd.DataFrame(
                [
                    {"item": "rerun_timestamp", "value": datetime.now().isoformat(timespec="seconds")},
                    {"item": "git_rev_parse_HEAD", "value": _git_hash()},
                    {"item": "python_version", "value": sys.version.replace("\n", " ")},
                    {"item": "pandas_version", "value": pd.__version__},
                    {"item": "numpy_version", "value": np.__version__},
                ]
            )
        ),
        "",
        "## 6.2 PR-3 A Baseline Diff",
        _markdown_table(diff.loc[diff["scope"].eq("PR-3 A baseline")].drop(columns=["scope"])),
        "",
        "## 6.3 PR-4 Variant Diff",
        _markdown_table(diff.loc[~diff["scope"].eq("PR-3 A baseline")]),
        "",
        "## 6.4 Verdict Counts",
        _markdown_table(counts),
        "",
        "## 6.5 Notes",
        "- OK: trade counts match and PF deltas are within the requested thresholds.",
        "- WARN: threshold exceeded without a trade-count mismatch.",
        "- CRITICAL: any trade-count mismatch.",
        "",
    ]
    return "\n".join(lines), diff


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PR-4.6 rerun diff report.")
    parser.add_argument("--output", default=str(REPORT_PATH))
    args = parser.parse_args()
    report, diff = build_diff_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    if bool(diff["verdict"].eq("CRITICAL").any()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
