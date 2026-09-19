from __future__ import annotations

import pandas as pd

from v2.spikes import a4_financial_multifactor as spike


def _events() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "stock_code": "A",
                "tradable_entry_date": "2024-01-03",
                "revenue": 200.0,
                "prev_revenue": 100.0,
                "operating_income": 40.0,
                "net_income": 20.0,
                "total_assets": 100.0,
                "total_equity": 50.0,
                "sue": 2.0,
            },
            {
                "stock_code": "B",
                "tradable_entry_date": "2024-01-03",
                "revenue": 90.0,
                "prev_revenue": 100.0,
                "operating_income": -5.0,
                "net_income": -10.0,
                "total_assets": 100.0,
                "total_equity": 50.0,
                "sue": -1.0,
            },
            {
                "stock_code": "A",
                "tradable_entry_date": "2024-01-06",
                "revenue": 50.0,
                "prev_revenue": 100.0,
                "operating_income": -20.0,
                "net_income": -30.0,
                "total_assets": 100.0,
                "total_equity": 50.0,
                "sue": -2.0,
            },
        ]
    )


def test_financial_score_is_point_in_time_and_missing_stays_neutral() -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-06"])

    score, loss = spike.build_point_in_time_financial_panels(
        _events(), dates, ["A", "B", "C"], min_cross_section=2
    )

    assert score.loc[pd.Timestamp("2024-01-02")].isna().all()
    assert score.loc[pd.Timestamp("2024-01-03"), "A"] > score.loc[pd.Timestamp("2024-01-03"), "B"]
    assert pd.isna(score.loc[pd.Timestamp("2024-01-03"), "C"])
    assert not bool(loss.loc[pd.Timestamp("2024-01-03"), "A"])
    assert bool(loss.loc[pd.Timestamp("2024-01-03"), "B"])
    assert bool(loss.loc[pd.Timestamp("2024-01-06"), "A"])
    assert not bool(loss.loc[pd.Timestamp("2024-01-06"), "C"])


def test_next_open_alignment_uses_entry_day_financials_with_prior_close_a4() -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-06"])
    score, _ = spike.build_point_in_time_financial_panels(
        _events(), dates, ["A", "B"], min_cross_section=2
    )
    a4 = pd.DataFrame(0.0, index=dates, columns=["A", "B"])

    combined = spike.combine_a4_with_next_open_financial(a4, score, a4_weight=0.5)

    assert combined.loc[pd.Timestamp("2024-01-02"), "A"] > combined.loc[pd.Timestamp("2024-01-02"), "B"]
    assert combined.loc[pd.Timestamp("2024-01-03"), "A"] < combined.loc[pd.Timestamp("2024-01-03"), "B"]
    assert combined.loc[pd.Timestamp("2024-01-06")].eq(0.0).all()


def test_bottom_financial_gate_excludes_only_known_bottom_names() -> None:
    financial = pd.DataFrame(
        [[-2.0, -1.0, 1.0, float("nan")]],
        index=pd.to_datetime(["2024-01-02"]),
        columns=["A", "B", "C", "D"],
    )

    excluded = spike.bottom_financial_exclusion(financial, bottom_fraction=1 / 3, min_cross_section=3)

    assert excluded.loc[pd.Timestamp("2024-01-02")].to_dict() == {
        "A": True,
        "B": False,
        "C": False,
        "D": False,
    }


def test_shadow_history_upserts_same_market_date_and_variant(tmp_path) -> None:
    path = tmp_path / "shadow_history.parquet"
    first = pd.DataFrame(
        {
            "market_date": pd.to_datetime(["2026-08-28", "2026-08-28"]),
            "variant": ["baseline_a4", "score75_gate_loss"],
            "forward_final_equity": [110_000_000.0, 112_000_000.0],
        }
    )
    revised = first.loc[first["variant"].eq("score75_gate_loss")].copy()
    revised["forward_final_equity"] = 113_000_000.0

    spike.persist_shadow_snapshot(first, path)
    spike.persist_shadow_snapshot(revised, path)

    history = pd.read_parquet(path).sort_values("variant").reset_index(drop=True)
    assert len(history) == 2
    assert history.loc[history["variant"].eq("score75_gate_loss"), "forward_final_equity"].item() == 113_000_000.0
