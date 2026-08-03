from __future__ import annotations

import json

import pandas as pd

from scripts.toss_invest_client import env_bool, load_orders, resolve_order_path, summarize_openapi_spec, summarize_orders


def test_env_bool_parses_truthy_values(monkeypatch) -> None:
    monkeypatch.setenv("TOSS_TEST_BOOL", "true")
    assert env_bool("TOSS_TEST_BOOL") is True

    monkeypatch.setenv("TOSS_TEST_BOOL", "0")
    assert env_bool("TOSS_TEST_BOOL", True) is False


def test_load_orders_accepts_latest_state_json(tmp_path) -> None:
    orders_path = tmp_path / "orders.csv"
    orders_path.write_text(
        "code,side,order_shares,gross_amount_est,liquidity_warning\n005930,SELL,3,210000,false\n000660,BUY,2,320000,true\n",
        encoding="utf-8",
    )
    state_path = tmp_path / "latest_state.json"
    state_path.write_text(json.dumps({"orders_path": str(orders_path)}), encoding="utf-8")

    orders = load_orders(state_path)
    summary = summarize_orders(orders, state_path)

    assert orders["code"].tolist() == ["005930", "000660"]
    assert summary["buy_rows"] == 1
    assert summary["sell_rows"] == 1
    assert summary["gross_buy"] == 320000.0
    assert summary["gross_sell"] == 210000.0
    assert summary["liquidity_warnings"] == 1


def test_resolve_order_path_converts_wsl_mount_path() -> None:
    assert str(resolve_order_path("/mnt/c/dev/orders.csv")).replace("\\", "/") == "C:/dev/orders.csv"


def test_summarize_openapi_spec_finds_order_related_paths() -> None:
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "Example", "version": "1"},
        "paths": {
            "/v1/orders": {
                "post": {
                    "operationId": "createOrder",
                    "summary": "주문 접수",
                    "tags": ["Trading"],
                }
            },
            "/v1/market/quote": {
                "get": {
                    "operationId": "quote",
                    "summary": "시세 조회",
                    "tags": ["Market"],
                }
            },
        },
    }

    summary = summarize_openapi_spec(spec)

    assert summary["path_count"] == 2
    assert summary["order_related_path_count"] == 1
    assert summary["order_related_paths"][0]["path"] == "/v1/orders"


def test_summarize_orders_handles_empty_frame(tmp_path) -> None:
    summary = summarize_orders(pd.DataFrame(), tmp_path / "orders.csv")

    assert summary["rows"] == 0
    assert summary["gross_buy"] == 0.0
    assert "blocked" in summary["note"]
