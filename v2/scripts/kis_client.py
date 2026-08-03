from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
CONFIG_TEMPLATE = CONFIG_DIR / "kis_config.example.json"


def env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


class KisClient:
    """Minimal KIS Open API skeleton.

    This is intentionally conservative: it can prepare auth headers and fetch an access
    token, but it does not submit real orders. Order submission should be added only
    after paper trading and account/quote reads are verified.
    """

    def __init__(self, *, app_key: str, app_secret: str, account_no: str, product_code: str, mode: str = "paper") -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.product_code = product_code
        self.mode = mode
        if mode == "live":
            self.base_url = "https://openapi.koreainvestment.com:9443"
        else:
            self.base_url = "https://openapivts.koreainvestment.com:29443"
        self._token: str | None = None

    @classmethod
    def from_env(cls) -> "KisClient":
        missing = [name for name in ["KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO"] if not env(name)]
        if missing:
            raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
        return cls(
            app_key=env("KIS_APP_KEY") or "",
            app_secret=env("KIS_APP_SECRET") or "",
            account_no=env("KIS_ACCOUNT_NO") or "",
            product_code=env("KIS_PRODUCT_CODE", "01") or "01",
            mode=env("KIS_MODE", "paper") or "paper",
        )

    def token(self) -> str:
        if self._token:
            return self._token
        url = self.base_url + "/oauth2/tokenP"
        payload = json.dumps({"grant_type": "client_credentials", "appkey": self.app_key, "appsecret": self.app_secret}).encode()
        req = urllib.request.Request(url, data=payload, headers={"content-type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        self._token = data["access_token"]
        return self._token

    def headers(self, tr_id: str) -> dict[str, str]:
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {self.token()}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def get_json(self, path: str, params: dict[str, Any], tr_id: str) -> dict[str, Any]:
        url = self.base_url + path + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self.headers(tr_id), method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())

    def quote(self, code: str) -> dict[str, Any]:
        return self.get_json(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code.zfill(6)},
            "FHKST01010100",
        )

    def balance(self) -> dict[str, Any]:
        # KIS TR IDs differ for paper/live and may change by account type. Verify in docs before live use.
        tr_id = "VTTC8434R" if self.mode != "live" else "TTTC8434R"
        return self.get_json(
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            {
                "CANO": self.account_no,
                "ACNT_PRDT_CD": self.product_code,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
            tr_id,
        )


def write_template() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    example = {
        "env": {
            "KIS_MODE": "paper",
            "KIS_APP_KEY": "<issued app key>",
            "KIS_APP_SECRET": "<issued app secret>",
            "KIS_ACCOUNT_NO": "<8 digit account number before dash>",
            "KIS_PRODUCT_CODE": "01"
        },
        "notes": [
            "Prefer env vars or a local untracked .env file; do not commit secrets.",
            "Order submission is intentionally not implemented yet.",
            "First verify token, quote, and balance against KIS paper account."
        ]
    }
    CONFIG_TEMPLATE.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(CONFIG_TEMPLATE)


def main() -> None:
    parser = argparse.ArgumentParser(description="KIS Open API skeleton for future broker integration.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("write-template")
    sub.add_parser("check-env")
    p = sub.add_parser("quote")
    p.add_argument("code")
    p = sub.add_parser("preview-orders")
    p.add_argument("--orders", default=str(ROOT / "data/cache/paper_trading/a4_20d_top10/latest_state.json"), help="orders CSV path or latest_state.json path")
    p.add_argument("--use-live-quotes", action="store_true", help="Fetch KIS quotes; otherwise use CSV estimated amounts only")
    sub.add_parser("balance")
    args = parser.parse_args()
    if args.cmd == "write-template":
        write_template()
    elif args.cmd == "check-env":
        c = KisClient.from_env()
        print(json.dumps({"mode": c.mode, "base_url": c.base_url, "account_no": c.account_no, "product_code": c.product_code}, ensure_ascii=False, indent=2))
    elif args.cmd == "quote":
        print(json.dumps(KisClient.from_env().quote(args.code), ensure_ascii=False, indent=2))
    elif args.cmd == "preview-orders":
        path = Path(args.orders)
        if path.suffix == ".json":
            state = json.loads(path.read_text(encoding="utf-8"))
            path = Path(state["orders_path"])
        orders = pd.read_csv(path, dtype={"code": str})
        if args.use_live_quotes:
            client = KisClient.from_env()
            prices = {}
            for code in orders["code"].astype(str).str.zfill(6).unique():
                q = client.quote(code)
                out = q.get("output", {})
                prices[code] = float(out.get("stck_prpr") or 0)
                time.sleep(0.15)
            orders["preview_price"] = orders["code"].astype(str).str.zfill(6).map(prices)
            orders["preview_gross"] = orders["order_shares"] * orders["preview_price"]
        else:
            orders["preview_price"] = orders.get("close", 0)
            orders["preview_gross"] = orders.get("gross_amount_est", 0)
        summary = {
            "orders_path": str(path),
            "rows": int(len(orders)),
            "buy_rows": int((orders["side"] == "BUY").sum()) if "side" in orders else 0,
            "sell_rows": int((orders["side"] == "SELL").sum()) if "side" in orders else 0,
            "gross_buy": float(orders.loc[orders["side"] == "BUY", "preview_gross"].sum()) if "side" in orders else 0.0,
            "gross_sell": float(orders.loc[orders["side"] == "SELL", "preview_gross"].sum()) if "side" in orders else 0.0,
            "liquidity_warnings": int(orders.get("liquidity_warning", pd.Series(dtype=bool)).fillna(False).astype(bool).sum()) if len(orders) else 0,
            "live_quotes_used": bool(args.use_live_quotes),
            "note": "Preview only. Order submission is not implemented."
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.cmd == "balance":
        print(json.dumps(KisClient.from_env().balance(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
