"""시가 단일가 체결 가정: 비용 수준별 TA11 생존선."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\dev\projects\moneygetter_v2")
sys.path.insert(0, str(ROOT / "v2/scripts"))
sys.path.insert(0, str(ROOT))
from explore_ta_signals import build_signals, cs_zscore, eligibility, forward_returns, load_panel, TRAIN_END
from explore_ta_turnover import buffered_weights

panel = load_panel()
mask = eligibility(panel)
ret = forward_returns(panel, mask)
close = panel["close"]
dvol60 = panel["trading_value"].fillna(close * panel["volume"]).rolling(60, min_periods=40).mean()
raw = build_signals(panel)["TA11_intraday_close_pos"]
train = np.asarray(ret.index <= TRAIN_END)
rank = dvol60.where(mask).rank(axis=1, ascending=False)

rows = []
for top_n in [150, 300]:
    umask = mask & rank.le(top_n)
    z = -cs_zscore(raw, umask)
    for tail in [0.05, 0.10]:
        held = buffered_weights(z, tail, tail).shift(1).fillna(0.0)
        gross = (held * ret.fillna(0.0)).sum(axis=1)
        turn = held.diff().abs().sum(axis=1).fillna(0.0) / 2.0
        for cost in [0, 3, 5, 10, 15, 18]:
            for period, sel in [("train", train), ("test", ~train)]:
                g, t = gross[sel], turn[sel]
                net = g - t * (cost / 10000.0)
                eq = (1 + net).cumprod()
                rows.append(dict(
                    top_n=top_n, tail=tail, cost_bps=cost, period=period,
                    alpha_bps=g.mean() / t.mean() * 10000,
                    sharpe=net.mean() / net.std(ddof=1) * np.sqrt(252),
                    ann_ret=net.mean() * 252, win=(net > 0).mean(),
                    mdd=(eq / eq.cummax() - 1).min(), turnover=t.mean(),
                    names=held.ne(0).sum(axis=1)[sel].mean()))
out = pd.DataFrame(rows)
pd.set_option("display.width", 300)
print(out.round(3).to_string(index=False))
out.to_csv(ROOT / "v2/data/cache/ta_explore/ta11_cost_ladder.csv", index=False)

from explore_ta_signals import markdown_table  # noqa: E402

cols = ["top_n", "tail", "cost_bps", "period", "alpha_bps", "sharpe", "ann_ret", "win", "mdd", "turnover", "names"]
(ROOT / "v2/reports/ta11_cost_ladder.md").write_text(
    f"""# TA11 비용 사다리 (시가 단일가 체결 가정)

- 체결: t 종가 신호 -> t+1 시가 단일가 진입/청산. 동시호가는 단일가격 체결이라 호가 스프레드를 지불하지 않음.
- cost_bps = 회전율 1단위당 왕복 비용. 현물 = 농특세 15bp(매도) + 수수료 3bp = 18bp. 개별주식선물 = 거래세 0 + 수수료 2~3bp.
- alpha_bps = mean(gross)/mean(turnover) x 10000. 이 값 밑으로 비용을 내려야 생존.

{markdown_table(out.round(4), cols)}

## 결론
- 손익분기 왕복비용 ~= 18bp (top150 / tail 5% 기준, test alpha 17.9bp).
- 현물 실행 비용이 정확히 18bp -> 세후 기대수익 0. 현물로는 실행 불가.
- 거래세 없는 수단(개별주식선물 등, 왕복 3bp)에서만 test Sharpe 1.6 / 연 55% / 일간승률 55.7%.
- 미검증 리스크: 개별주식선물 시가 단일가 유동성. 얇으면 슬리피지가 알파를 다시 먹음.
""",
    encoding="utf-8",
)
