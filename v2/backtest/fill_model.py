from __future__ import annotations

from dataclasses import dataclass
from math import isclose


DEFAULT_TRANSACTION_COST_BPS = 20.0
DEFAULT_SLIPPAGE_BPS = 15.0
KOREA_PRICE_LIMIT_PCT = 0.30


@dataclass(frozen=True)
class CostModel:
    transaction_cost_bps: float = DEFAULT_TRANSACTION_COST_BPS
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS

    @property
    def per_side_bps(self) -> float:
        return self.transaction_cost_bps + self.slippage_bps

    @property
    def round_trip_bps(self) -> float:
        return self.per_side_bps * 2


@dataclass(frozen=True)
class FillResult:
    filled: bool
    price: float | None
    reason: str


def is_limit_bar(
    *,
    high: float,
    low: float,
    previous_close: float | None,
    limit_pct: float = KOREA_PRICE_LIMIT_PCT,
) -> bool:
    """Return true when a Korean +/-30% limit bar blocks reliable fills."""

    if previous_close is None or previous_close <= 0:
        return False
    upper = previous_close * (1 + limit_pct)
    lower = previous_close * (1 - limit_pct)
    return high >= upper or isclose(high, upper) or low <= lower or isclose(low, lower)


def stop_exit_fill(
    *,
    open_price: float,
    low_price: float,
    stop_price: float,
    high_price: float | None = None,
    previous_close: float | None = None,
) -> FillResult:
    """Apply the Stage 2+5 long stop-fill rule for a single bar.

    For a long position, a gap below the stop fills at the open. Otherwise,
    intraday touch fills at the stop. Limit-up/down bars are treated as
    unfillable when previous_close is available.
    """

    if high_price is not None and is_limit_bar(
        high=high_price,
        low=low_price,
        previous_close=previous_close,
    ):
        return FillResult(filled=False, price=None, reason="limit_bar_unfillable")

    if open_price < stop_price:
        return FillResult(filled=True, price=float(open_price), reason="gap_below_stop")
    if low_price <= stop_price:
        return FillResult(filled=True, price=float(stop_price), reason="intraday_stop")
    return FillResult(filled=False, price=None, reason="not_touched")


def long_entry_cash_price(price: float, cost_model: CostModel = CostModel()) -> float:
    return float(price) * (1 + cost_model.per_side_bps / 10_000)


def long_exit_cash_price(price: float, cost_model: CostModel = CostModel()) -> float:
    return float(price) * (1 - cost_model.per_side_bps / 10_000)


def long_trade_pnl(
    *,
    entry_price: float,
    exit_price: float,
    quantity: float,
    cost_model: CostModel = CostModel(),
) -> float:
    cost_adjusted_entry = long_entry_cash_price(entry_price, cost_model)
    cost_adjusted_exit = long_exit_cash_price(exit_price, cost_model)
    return (cost_adjusted_exit - cost_adjusted_entry) * float(quantity)

