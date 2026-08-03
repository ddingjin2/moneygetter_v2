from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"data/cache/paper_trading/a4_20d_top10"
REPORT=ROOT/"reports/paper_trading_performance.md"

def atomic_text(text,path):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(f'.{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}'); tmp.write_text(text,encoding='utf-8'); os.replace(tmp,path)

def fmt(x):
 return 'NA' if pd.isna(x) else (f'{x:,.0f}' if abs(x)>10 else f'{x:.4f}')

def maxdd(eq):
 return float((eq/eq.cummax()-1).min()) if len(eq) else float('nan')

def main():
 eq=pd.read_csv(BASE/'equity_curve.csv') if (BASE/'equity_curve.csv').exists() else pd.DataFrame()
 trades=pd.read_csv(BASE/'trades.csv',dtype={'code':str}) if (BASE/'trades.csv').exists() else pd.DataFrame()
 pos=pd.read_csv(BASE/'positions_mtm.csv',dtype={'code':str}) if (BASE/'positions_mtm.csv').exists() else pd.DataFrame()
 lines=['# A4 paper trading performance','']
 if eq.empty:
  lines.append('No equity curve yet.')
 else:
  eq['date']=pd.to_datetime(eq.date); eq=eq.sort_values('date'); eq['daily_return']=eq.equity.pct_change().fillna(0)
  latest=eq.iloc[-1]
  lines += [
   '## Account summary',
   f'- Date: {latest.date:%Y-%m-%d}',
   f'- Cash: {latest.cash:,.0f} KRW',
   f'- Market value: {latest.market_value:,.0f} KRW',
   f'- Equity: {latest.equity:,.0f} KRW',
   f'- Cumulative return: {latest.cum_return:.4%}',
   f'- Max drawdown: {maxdd(eq.equity):.4%}',
   f'- Recorded days: {len(eq)}',
   ''
  ]
 if not trades.empty:
  lines += ['## Trades', f'- Rows: {len(trades)}', f'- Gross traded: {pd.to_numeric(trades.gross,errors="coerce").sum():,.0f} KRW', f'- Fees: {pd.to_numeric(trades.fee,errors="coerce").sum():,.0f} KRW', '']
 if not pos.empty:
  pos['market_value']=pd.to_numeric(pos.market_value,errors='coerce'); pos['unrealized_pnl']=pd.to_numeric(pos.unrealized_pnl,errors='coerce')
  top=pos.sort_values('market_value',ascending=False).head(20)
  lines += ['## Current positions top 20 by value','| code | name | shares | market_value | unrealized_pnl |','| --- | --- | ---: | ---: | ---: |']
  for r in top.itertuples(index=False): lines.append(f'| {r.code} | {r.name} | {int(r.shares)} | {r.market_value:,.0f} | {r.unrealized_pnl:,.0f} |')
 atomic_text('\n'.join(lines)+'\n',REPORT)
 print(REPORT)
if __name__=='__main__': main()
