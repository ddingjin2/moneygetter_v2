from __future__ import annotations

import pandas as pd

from v2.data.us_fundamentals import (
    align_fundamentals_asof,
    extract_sec_companyfacts_fundamentals,
    quality_score,
)


def test_align_fundamentals_asof_uses_filing_date_not_period_end() -> None:
    fundamentals = pd.DataFrame(
        {
            "symbol": ["AAA", "AAA", "BBB"],
            "fiscal_period_end": ["2023-12-31", "2024-03-31", "2023-12-31"],
            "filing_date": ["2024-02-15", "2024-05-10", "2024-02-20"],
            "gross_profit": [30.0, 40.0, 10.0],
            "net_income": [12.0, 15.0, 2.0],
            "total_assets": [100.0, 100.0, 100.0],
            "total_liabilities": [20.0, 18.0, 80.0],
        }
    )
    dates = pd.DatetimeIndex(["2024-02-14", "2024-02-16", "2024-05-09", "2024-05-13"])

    aligned = align_fundamentals_asof(fundamentals, dates, ["AAA", "BBB"])

    aaa = aligned.loc[(slice(None), "AAA"), :].droplevel("symbol")
    assert pd.isna(aaa.loc[pd.Timestamp("2024-02-14"), "gross_profit"])
    assert aaa.loc[pd.Timestamp("2024-02-16"), "gross_profit"] == 30.0
    assert aaa.loc[pd.Timestamp("2024-05-09"), "gross_profit"] == 30.0
    assert aaa.loc[pd.Timestamp("2024-05-13"), "gross_profit"] == 40.0


def test_quality_score_prefers_profitability_and_penalizes_leverage() -> None:
    aligned = pd.DataFrame(
        {
            "gross_profit": [30.0, 10.0, 20.0],
            "net_income": [12.0, 2.0, 8.0],
            "total_assets": [100.0, 100.0, 100.0],
            "total_liabilities": [20.0, 80.0, 50.0],
        },
        index=pd.MultiIndex.from_product(
            [[pd.Timestamp("2024-03-01")], ["HIGH", "LOW", "MID"]],
            names=["date", "symbol"],
        ),
    )

    scores = quality_score(aligned)

    day = scores.loc[pd.Timestamp("2024-03-01")]
    assert day["HIGH"] > day["MID"] > day["LOW"]


def test_extract_sec_companyfacts_fundamentals_prefers_filed_period_rows() -> None:
    payload = {
        "facts": {
            "us-gaap": {
                "GrossProfit": {
                    "units": {
                        "USD": [
                            {"end": "2024-03-31", "filed": "2024-05-01", "form": "10-Q", "val": 30.0},
                            {"end": "2024-06-30", "filed": "2024-08-01", "form": "10-Q", "val": 40.0},
                        ]
                    }
                },
                "NetIncomeLoss": {"units": {"USD": [{"end": "2024-03-31", "filed": "2024-05-01", "form": "10-Q", "val": 12.0}]}},
                "Assets": {"units": {"USD": [{"end": "2024-03-31", "filed": "2024-05-01", "form": "10-Q", "val": 100.0}]}},
                "Liabilities": {"units": {"USD": [{"end": "2024-03-31", "filed": "2024-05-01", "form": "10-Q", "val": 20.0}]}},
            }
        }
    }

    rows = extract_sec_companyfacts_fundamentals("AAA", payload)

    assert list(rows.columns) == [
        "symbol",
        "fiscal_period_end",
        "filing_date",
        "gross_profit",
        "net_income",
        "total_assets",
        "total_liabilities",
    ]
    first = rows.iloc[0]
    assert first["symbol"] == "AAA"
    assert first["fiscal_period_end"] == pd.Timestamp("2024-03-31")
    assert first["filing_date"] == pd.Timestamp("2024-05-01")
    assert first["gross_profit"] == 30.0
    assert first["net_income"] == 12.0
