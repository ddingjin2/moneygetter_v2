from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CONFIG_TEMPLATE = CONFIG_DIR / "toss_invest_config.example.json"
DEFAULT_DOCS_URL = "https://developers.tossinvest.com/docs"
DEFAULT_OPENAPI_DOCUMENT_URL = "https://openapi.tossinvest.com/openapi-docs/latest/openapi.json"
DEFAULT_OVERVIEW_URL = "https://openapi.tossinvest.com/openapi-docs/overview.md"
DEFAULT_ORDERS_STATE = ROOT / "data/cache/paper_trading/a4_20d_top10/latest_state.json"

ORDER_KEYWORDS = (
    "order",
    "trading",
    "trade",
    "account",
    "balance",
    "portfolio",
    "주문",
    "매수",
    "매도",
    "계좌",
    "잔고",
    "체결",
)


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    raw = env(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class TossInvestConfig:
    """Conservative Toss Securities Open API configuration.

    The public developer page is available, but live order details must be
    verified against the official OpenAPI spec and an approved API key before
    any real order submission is implemented.
    """

    mode: str
    app_key: str
    app_secret: str
    account_no: str
    openapi_document_url: str
    overview_url: str
    docs_url: str
    enable_live_orders: bool

    @classmethod
    def from_env(cls) -> "TossInvestConfig":
        return cls(
            mode=env("TOSS_INVEST_MODE", "disabled") or "disabled",
            app_key=env("TOSS_INVEST_APP_KEY", "") or "",
            app_secret=env("TOSS_INVEST_APP_SECRET", "") or "",
            account_no=env("TOSS_INVEST_ACCOUNT_NO", "") or "",
            openapi_document_url=env("TOSS_INVEST_OPENAPI_DOCUMENT_URL", DEFAULT_OPENAPI_DOCUMENT_URL)
            or DEFAULT_OPENAPI_DOCUMENT_URL,
            overview_url=env("TOSS_INVEST_OVERVIEW_URL", DEFAULT_OVERVIEW_URL) or DEFAULT_OVERVIEW_URL,
            docs_url=env("TOSS_INVEST_DOCS_URL", DEFAULT_DOCS_URL) or DEFAULT_DOCS_URL,
            enable_live_orders=env_bool("TOSS_INVEST_ENABLE_LIVE_ORDERS", False),
        )

    def masked(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "docs_url": self.docs_url,
            "openapi_document_url": self.openapi_document_url,
            "overview_url": self.overview_url,
            "has_app_key": bool(self.app_key),
            "has_app_secret": bool(self.app_secret),
            "has_account_no": bool(self.account_no),
            "enable_live_orders": self.enable_live_orders,
        }


class TossInvestClient:
    def __init__(self, config: TossInvestConfig) -> None:
        self.config = config

    @classmethod
    def from_env(cls) -> "TossInvestClient":
        return cls(TossInvestConfig.from_env())

    def request_json(self, url: str, *, timeout: int = 20) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={
                "accept": "application/json",
                "user-agent": "Mozilla/5.0 moneygetter-v2 research integration",
                "referer": self.config.docs_url,
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def fetch_openapi_spec(self, url: str | None = None) -> dict[str, Any]:
        return self.request_json(url or self.config.openapi_document_url)

    def preview_orders(self, orders_path: Path) -> dict[str, Any]:
        try:
            orders = load_orders(orders_path)
        except FileNotFoundError as exc:
            return {
                "orders_path": str(orders_path),
                "rows": 0,
                "buy_rows": 0,
                "sell_rows": 0,
                "gross_buy": 0.0,
                "gross_sell": 0.0,
                "order_shares_total": 0.0,
                "liquidity_warnings": 0,
                "ok": False,
                "error": str(exc),
                "note": "Preview only. Order file was not found and no broker request was sent.",
            }
        return summarize_orders(orders, orders_path)

    def submit_orders(self, orders_path: Path, *, confirm_live_order: bool = False) -> None:
        _ = orders_path
        _ = confirm_live_order
        raise SystemExit(
            "Toss Invest live order submission is intentionally not implemented. "
            "First fetch and review the official OpenAPI spec, verify auth/account reads, "
            "then add broker-specific submit code behind a separate safety review."
        )


def resolve_order_path(path: str | Path) -> Path:
    raw = str(path).replace("\\", "/")
    if raw.startswith("/mnt/") and len(raw) > 6 and raw[5].isalpha() and raw[6] == "/":
        return Path(f"{raw[5].upper()}:" + raw[6:])
    return Path(path)


def load_orders(path: Path) -> pd.DataFrame:
    path = resolve_order_path(path)
    if path.suffix.lower() == ".json":
        state = json.loads(path.read_text(encoding="utf-8"))
        path = resolve_order_path(state["orders_path"])
    orders = pd.read_csv(path, dtype={"code": str, "symbol": str})
    if "code" in orders:
        orders["code"] = orders["code"].astype(str).str.zfill(6)
    return orders


def summarize_orders(orders: pd.DataFrame, orders_path: Path) -> dict[str, Any]:
    side = orders["side"] if "side" in orders else pd.Series(dtype=str)
    gross = pd.to_numeric(orders.get("gross_amount_est", pd.Series(dtype=float)), errors="coerce").fillna(0)
    order_shares = pd.to_numeric(orders.get("order_shares", pd.Series(dtype=float)), errors="coerce").fillna(0)
    return {
        "orders_path": str(orders_path),
        "rows": int(len(orders)),
        "buy_rows": int(side.eq("BUY").sum()) if len(side) else 0,
        "sell_rows": int(side.eq("SELL").sum()) if len(side) else 0,
        "gross_buy": float(gross[side.eq("BUY")].sum()) if len(side) else 0.0,
        "gross_sell": float(gross[side.eq("SELL")].sum()) if len(side) else 0.0,
        "order_shares_total": float(order_shares.sum()),
        "liquidity_warnings": int(orders.get("liquidity_warning", pd.Series(dtype=bool)).fillna(False).astype(bool).sum())
        if len(orders)
        else 0,
        "note": "Preview only. Toss Invest live order submission is blocked.",
    }


def summarize_openapi_spec(spec: dict[str, Any]) -> dict[str, Any]:
    paths = spec.get("paths", {})
    matching: list[dict[str, Any]] = []
    for path, operations in paths.items():
        if not isinstance(operations, dict):
            continue
        for method, operation in operations.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue
            haystack = " ".join(
                str(operation.get(name, ""))
                for name in ["operationId", "summary", "description"]
            )
            haystack = f"{path} {haystack} {' '.join(operation.get('tags', []) or [])}".lower()
            if any(keyword.lower() in haystack for keyword in ORDER_KEYWORDS):
                matching.append(
                    {
                        "method": method.upper(),
                        "path": path,
                        "summary": operation.get("summary", ""),
                        "operation_id": operation.get("operationId", ""),
                        "tags": operation.get("tags", []),
                    }
                )
    return {
        "openapi": spec.get("openapi"),
        "title": spec.get("info", {}).get("title"),
        "version": spec.get("info", {}).get("version"),
        "servers": spec.get("servers", []),
        "path_count": len(paths),
        "order_related_path_count": len(matching),
        "order_related_paths": matching[:80],
    }


def write_template() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    example = {
        "env": {
            "TOSS_INVEST_MODE": "disabled",
            "TOSS_INVEST_APP_KEY": "<issued app key>",
            "TOSS_INVEST_APP_SECRET": "<issued app secret>",
            "TOSS_INVEST_ACCOUNT_NO": "<account identifier if required by official docs>",
            "TOSS_INVEST_OPENAPI_DOCUMENT_URL": DEFAULT_OPENAPI_DOCUMENT_URL,
            "TOSS_INVEST_ENABLE_LIVE_ORDERS": "false",
        },
        "notes": [
            "Prefer env vars or a local untracked .env file; do not commit secrets.",
            "Live order submission is intentionally blocked in scripts/toss_invest_client.py.",
            "Fetch and review the official OpenAPI spec before adding any submit endpoint.",
        ],
    }
    CONFIG_TEMPLATE.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(CONFIG_TEMPLATE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Toss Invest Open API safe integration skeleton.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("write-template")
    sub.add_parser("check-env")
    p = sub.add_parser("fetch-openapi")
    p.add_argument("--url", default=None)
    p = sub.add_parser("preview-orders")
    p.add_argument("--orders", type=Path, default=DEFAULT_ORDERS_STATE)
    p = sub.add_parser("submit-orders")
    p.add_argument("--orders", type=Path, default=DEFAULT_ORDERS_STATE)
    p.add_argument("--confirm-live-order", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = TossInvestClient.from_env()
    if args.cmd == "write-template":
        write_template()
    elif args.cmd == "check-env":
        print(json.dumps(client.config.masked(), ensure_ascii=False, indent=2))
    elif args.cmd == "fetch-openapi":
        try:
            summary = summarize_openapi_spec(client.fetch_openapi_spec(args.url))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            summary = {
                "ok": False,
                "error": str(exc),
                "docs_url": client.config.docs_url,
                "openapi_document_url": args.url or client.config.openapi_document_url,
                "note": "The public docs endpoint may require browser/approved access before CLI fetching works.",
            }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.cmd == "preview-orders":
        print(json.dumps(client.preview_orders(args.orders), ensure_ascii=False, indent=2))
    elif args.cmd == "submit-orders":
        time.sleep(0.1)
        client.submit_orders(args.orders, confirm_live_order=args.confirm_live_order)


if __name__ == "__main__":
    main()
