from __future__ import annotations

import math

import pandas as pd

from v2.data.earnings import (
    calculate_tradable_entry_date,
    compute_sue,
    order_earnings_columns,
    validate_earnings_point_in_time,
)


def _calendar() -> list[pd.Timestamp]:
    return [
        pd.Timestamp("2024-05-09"),
        pd.Timestamp("2024-05-10"),
        pd.Timestamp("2024-05-13"),
        pd.Timestamp("2024-05-14"),
        pd.Timestamp("2024-05-16"),
        pd.Timestamp("2024-05-17"),
        pd.Timestamp("2024-05-20"),
    ]


def test_tradable_entry_date_after_close_goes_to_next_trading_day() -> None:
    assert calculate_tradable_entry_date("2024-05-10", "16:10", _calendar()) == pd.Timestamp("2024-05-13")


def test_tradable_entry_date_before_close_still_uses_next_open() -> None:
    assert calculate_tradable_entry_date("2024-05-13", "15:29", _calendar()) == pd.Timestamp("2024-05-14")


def test_tradable_entry_date_weekend_disclosure_uses_next_business_day() -> None:
    assert calculate_tradable_entry_date("2024-05-11", "10:00", _calendar()) == pd.Timestamp("2024-05-13")


def test_tradable_entry_date_skips_missing_holiday_in_calendar() -> None:
    assert calculate_tradable_entry_date("2024-05-14", "16:00", _calendar()) == pd.Timestamp("2024-05-16")


def test_compute_sue_matches_manual_yoy_eps_formula() -> None:
    net_income = [100, 110, 120, 130, 140, 150, 160, 170, 230]
    events = pd.DataFrame(
        {
            "stock_code": ["000001"] * 9,
            "fiscal_quarter": [
                "2022Q1",
                "2022Q2",
                "2022Q3",
                "2022Q4",
                "2023Q1",
                "2023Q2",
                "2023Q3",
                "2023Q4",
                "2024Q1",
            ],
            "net_income": net_income,
            "shares_outstanding": [10] * 9,
        }
    )

    result = compute_sue(events)

    prior_eps = 140 / 10
    current_eps = 230 / 10
    past_8_eps = pd.Series([100, 110, 120, 130, 140, 150, 160, 170], dtype="float64") / 10
    expected = (current_eps - prior_eps) / past_8_eps.std(ddof=0)
    actual = float(result.loc[result["fiscal_quarter"].eq("2024Q1"), "sue"].iloc[0])
    assert math.isclose(actual, expected)


def test_earnings_point_in_time_validation_passes_clean_dataset() -> None:
    events = order_earnings_columns(
        pd.DataFrame(
            [
                {
                    "corp_code": "00126380",
                    "stock_code": "005930",
                    "report_type": "A003",
                    "fiscal_quarter": "2024Q1",
                    "rcept_dt": pd.Timestamp("2024-05-10"),
                    "rcept_time": "16:10",
                    "tradable_entry_date": pd.Timestamp("2024-05-13"),
                    "revenue": 1.0,
                    "operating_income": 1.0,
                    "net_income": 1.0,
                    "prev_revenue": 1.0,
                    "prev_operating_income": 1.0,
                    "prev_net_income": 1.0,
                    "data_source_timestamp": pd.Timestamp("2024-05-10"),
                }
            ]
        )
    )

    violations = validate_earnings_point_in_time(events)

    assert violations == {
        "data_source_after_receipt": [],
        "fiscal_quarter_after_receipt": [],
        "pr1_leakage": [],
    }


def test_earnings_point_in_time_validation_catches_future_quarter() -> None:
    events = pd.DataFrame(
        [
            {
                "stock_code": "005930",
                "fiscal_quarter": "2024Q3",
                "rcept_dt": pd.Timestamp("2024-05-10"),
                "rcept_time": "16:10",
                "tradable_entry_date": pd.Timestamp("2024-05-13"),
                "data_source_timestamp": pd.Timestamp("2024-05-10"),
            }
        ]
    )

    violations = validate_earnings_point_in_time(events)

    assert violations["fiscal_quarter_after_receipt"] == ["005930|2024-05-10|2024Q3"]

