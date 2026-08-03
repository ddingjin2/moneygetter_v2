from __future__ import annotations

import math, os, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('/mnt/c/dev/moneygetter_v2/v2')
PRICE_DIR=ROOT/'data/cache/price_market_cap_full'
OUT=ROOT/'data/cache/lit_factor_explore'
REPORT=ROOT/'reports/lit_factor_exploration.md'
KOSPI_PATH=ROOT/'data/cache/benchmarks/kospi_daily_returns.parquet'
IS=(pd.Timestamp('2020-03-27'),pd.Timestamp('2024-12-31'))
OOS=(pd.Timestamp('2025-01-01'),pd.Timestamp('2026-04-17'))
FULL=(pd.Timestamp('2020-03-27'),pd.Timestamp('2026-04-17'))
SUBS={'sub1':(pd.Timestamp('2020-03-27'),pd.Timestamp('2021-12-31')),'sub2':(pd.Timestamp('2022-01-01'),pd.Timestamp('2022-12-31')),'sub3':(pd.Timestamp('2023-01-01'),pd.Timestamp('2024-12-31')),'sub4':OOS}

PAPERS=[
 ('Low-volatility / betting-against-beta anomaly','Frazzini & Pedersen BAB; Blitz & van Vliet volatility effect','Prefer low beta/low idiosyncratic volatility, avoid high beta lottery stocks'),
 ('Idiosyncratic volatility puzzle','Ang, Hodrick, Xing & Zhang; Bali & Cakici','Low IVOL tends to outperform high IVOL in many markets'),
 ('Lottery demand / MAX anomaly','Bali, Cakici & Whitelaw, Maxing out','Stocks with extreme max daily returns subsequently underperform'),
 ('Residual momentum','Blitz, Huij & Martens','Momentum after removing market exposure is cleaner than raw momentum'),
 ('Short-term reversal and liquidity','Jegadeesh; Heston/Korajczyk/Sadka intraday reversal/continuation literature','Recent loser reversal conditional on liquidity/volume can work but turnover/cost sensitive'),
]

def atomic_parquet(df,path):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(f'.{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}'); df.to_parquet(tmp,index=False); os.replace(tmp,path)
def atomic_text(txt,path):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(f'.{path.stem}.{os.getpid()}.{time.time_ns()}.tmp{path.suffix}'); tmp.write_text(txt,encoding='utf-8'); os.replace(tmp,path)

def stock_codes(): return sorted(p.stem for p in PRICE_DIR.glob('*.parquet') if p.stem.isdigit() and len(p.stem)==6)

def load_panel():
 frames=[]
 for code in stock_codes():
  f=pd.read_parquet(PRICE_DIR/f'{code}.parquet', columns=['date','open','high','low','close','volume'])
  f['code']=code; frames.append(f)
 p=pd.concat(frames,ignore_index=True)
 p['date']=pd.to_datetime(p.date).dt.normalize()
 for c in ['open','high','low','close','volume']: p[c]=pd.to_numeric(p[c],errors='coerce').astype('float64')
 p['dvol']=p['close']*p['volume']
 piv={c:p.pivot(index='date',columns='code',values=c).sort_index() for c in ['open','high','low','close','volume','dvol']}
 halt=(piv['open'].eq(0)&piv['volume'].eq(0))|piv['open'].isna()
 nxt=halt.shift(-1).fillna(True).astype(bool)
 ret_o2o=piv['open'].shift(-1)/piv['open']-1
 ret_o2o=ret_o2o.where((~halt)&(~nxt)&piv['open'].gt(0)&piv['open'].shift(-1).gt(0))
 return piv, ret_o2o

def cs_z(df):
 mean=df.mean(axis=1,skipna=True); std=df.std(axis=1,ddof=0,skipna=True).replace(0,np.nan)
 return df.sub(mean,axis=0).div(std,axis=0)

def build_signals(piv):
 close=piv['close']; high=piv['high']; dvol=piv['dvol'].replace(0,np.nan)
 ret=close.pct_change()
 kospi=pd.read_parquet(KOSPI_PATH); kospi['date']=pd.to_datetime(kospi.date).dt.normalize(); mkt=kospi.set_index('date').daily_return.reindex(close.index).astype('float64')
 # Beta and residuals
 beta=ret.rolling(252,min_periods=126).cov(mkt) / mkt.rolling(252,min_periods=126).var(ddof=0)
 resid=ret.sub(beta.mul(mkt,axis=0),axis=0)
 raw={}
 raw['LV_126']=-ret.rolling(126,min_periods=63).std(ddof=0)
 raw['IVOL_252']=-resid.rolling(252,min_periods=126).std(ddof=0)
 raw['BETA_252']=-beta
 raw['MAXRET_21']=-ret.rolling(21,min_periods=15).max()
 raw['MOM_126_21']=close.shift(21)/close.shift(126)-1
 raw['RESMOM_126_21']=(1+resid).rolling(126,min_periods=80).apply(np.prod,raw=True).shift(21)/((1+resid).rolling(21,min_periods=15).apply(np.prod,raw=True).shift(21).replace(0,np.nan))-1
 # above is awkward; alternative cumulative residual momentum excluding last 21d
 logres=np.log1p(resid.clip(lower=-0.95))
 raw['RESMOM_252_21']=logres.shift(21).rolling(231,min_periods=160).sum()
 raw['ILLIQ_60']=(ret.abs()/dvol).rolling(60,min_periods=40).mean()
 raw['A4_60']=-np.log(dvol.rolling(60,min_periods=60).mean())
 raw['A3_60']=-ret.rolling(60,min_periods=60).std(ddof=0)
 raw['Q_LV_IVOL_MAX']=raw['LV_126']+raw['IVOL_252']+raw['MAXRET_21']
 raw['Q_A4_LV_MAX']=raw['A4_60']+raw['LV_126']+raw['MAXRET_21']
 raw['Q_A4_A3_MAX']=raw['A4_60']+raw['A3_60']+raw['MAXRET_21']
 raw['Q_A4_A3_IVOL_MAX']=raw['A4_60']+raw['A3_60']+raw['IVOL_252']+raw['MAXRET_21']
 raw['Q_DEFENSIVE']=raw['A4_60']+raw['A3_60']+raw['IVOL_252']+raw['MAXRET_21']+raw['BETA_252']
 return {k:cs_z(v.replace([np.inf,-np.inf],np.nan)) for k,v in raw.items()}

def maxdd(r):
 eq=(1+r.fillna(0)).cumprod(); return float((eq/eq.cummax()-1).min()) if len(eq) else math.nan

def metr(r):
 r=r.dropna().astype('float64')
 if r.empty: return dict(sharpe=np.nan,ann_return=np.nan,ann_vol=np.nan,max_dd=np.nan,hit_ratio=np.nan)
 ar=float(r.mean()*252); av=float(r.std(ddof=1)*math.sqrt(252)) if len(r)>1 else np.nan
 return dict(sharpe=ar/av if av and not math.isnan(av) else np.nan,ann_return=ar,ann_vol=av,max_dd=maxdd(r),hit_ratio=float((r>0).mean()))

def bt(sig,ret,reb,q,cost_bps=30):
 dates=list(ret.index); codes=list(ret.columns); prev=pd.Series(0.0,index=codes); cur=prev.copy(); rows=[]
 for i,d in enumerate(dates):
  if i==0: target=pd.Series(0.0,index=codes)
  else:
   sd=dates[i-1]
   if ((i-1)%reb)==0:
    vals=sig.loc[sd].dropna().sort_values(); target=pd.Series(0.0,index=codes)
    if len(vals)>=30:
     n=max(int(math.floor(len(vals)*q)),1); target.loc[vals.tail(n).index]=1.0/n
    cur=target.copy()
   else: target=cur.copy()
  turnover=float((target-prev).abs().sum()/2.0); dr=ret.loc[d]; valid=dr.notna()
  gross=float((target.loc[valid]*dr.loc[valid]).sum()) if valid.any() else 0.0
  net=gross-turnover*(cost_bps/10000.0)*2.0
  rows.append({'date':d,'net_return':net,'turnover':turnover,'n_long':int((target>0).sum())}); prev=target.copy()
 return pd.DataFrame(rows)

def eval_strategy(name,sig,ret,reb,q):
 pnl=bt(sig,ret,reb,q); rows=[]
 periods={'IS':IS,'OOS':OOS,'FULL':FULL,**SUBS}
 for per,(s,e) in periods.items():
  sub=pnl[pnl.date.between(s,e)]; rows.append({'strategy':name,'rebalance':f'{reb}d','q':q,'period':per,**metr(sub.net_return),'avg_turnover':float(sub.turnover.mean()) if len(sub) else np.nan})
 pnl.insert(0,'strategy',name); pnl.insert(1,'rebalance',f'{reb}d'); pnl.insert(2,'q',q); return rows,pnl

def monthly_spread(pnl):
 kospi=pd.read_parquet(KOSPI_PATH); kospi['date']=pd.to_datetime(kospi.date).dt.normalize()
 x=pnl.merge(kospi[['date','daily_return']],on='date',how='left'); x['month']=x.date.dt.to_period('M')
 m=x.groupby('month').agg(lo=('net_return',lambda s:float((1+s).prod()-1)),kospi=('daily_return',lambda s:float((1+s).prod()-1))).reset_index()
 m['spread']=m.lo-m.kospi; m['month_ts']=m.month.dt.to_timestamp(); out={}
 for label,(s,e) in {'IS':IS,'OOS':OOS}.items():
  sub=m[m.month_ts.between(s.replace(day=1),e)]
  out[f'{label}_monthly_spread']=float(sub.spread.mean()) if len(sub) else np.nan; out[f'{label}_spread_win']=float((sub.spread>0).mean()) if len(sub) else np.nan
 return out

def table(df,cols,n=None):
 o=df[cols].head(n) if n else df[cols]
 lines=['| '+' | '.join(cols)+' |','| '+' | '.join(['---']*len(cols))+' |']
 for row in o.itertuples(index=False):
  vals=[]
  for v in row: vals.append('NA' if isinstance(v,float) and math.isnan(v) else (f'{v:.4f}' if isinstance(v,float) else str(v)))
  lines.append('| '+' | '.join(vals)+' |')
 return '\n'.join(lines)

def run():
 OUT.mkdir(parents=True,exist_ok=True); piv,ret=load_panel(); sigs=build_signals(piv)
 rows=[]; pnls=[]
 for name,sig in sigs.items():
  for reb in [5,20]:
   for q in [0.1,0.15,0.2]:
    r,p=eval_strategy(name,sig,ret,reb,q); rows+=r; pnls.append(p)
 metrics=pd.DataFrame(rows); pnl_all=pd.concat(pnls,ignore_index=True)
 atomic_parquet(metrics,OUT/'metrics.parquet'); atomic_parquet(pnl_all,OUT/'pnl_daily.parquet')
 wide=metrics.pivot_table(index=['strategy','rebalance','q'],columns='period',values=['sharpe','ann_return','ann_vol','max_dd','avg_turnover'],aggfunc='first'); wide.columns=[f'{a}_{b}' for a,b in wide.columns]; wide=wide.reset_index()
 subs=metrics[metrics.period.str.startswith('sub')].groupby(['strategy','rebalance','q']).sharpe.min().reset_index(name='min_sub_sharpe'); wide=wide.merge(subs,on=['strategy','rebalance','q'])
 # add monthly spread for top and A4/A3 baselines
 top=wide.sort_values(['sharpe_OOS','sharpe_IS'],ascending=False).head(20)
 mrows=[]
 for _,r in top.iterrows():
  p=pnl_all[(pnl_all.strategy==r.strategy)&(pnl_all.rebalance==r.rebalance)&(pnl_all.q==r.q)]
  mrows.append({'strategy':r.strategy,'rebalance':r.rebalance,'q':r.q,**monthly_spread(p)})
 mdf=pd.DataFrame(mrows); atomic_parquet(wide,OUT/'summary_wide.parquet'); atomic_parquet(mdf,OUT/'monthly_spread_summary.parquet')
 top=wide.merge(mdf,on=['strategy','rebalance','q'],how='left').sort_values(['sharpe_OOS','sharpe_IS'],ascending=False)
 txt='# Literature-inspired factor exploration\n\n'
 txt+='## Paper themes used\n'+'\n'.join(f'- {a}: {b}. Impl: {c}' for a,b,c in PAPERS)+'\n\n'
 txt+='## Top by OOS Sharpe\n'+table(top,['strategy','rebalance','q','sharpe_IS','sharpe_OOS','ann_return_OOS','ann_vol_OOS','max_dd_OOS','avg_turnover_OOS','min_sub_sharpe','OOS_monthly_spread','OOS_spread_win'],30)+'\n\n'
 txt+='## Robust rows: IS>1, OOS>3, min_sub>-0.3\n'
 rob=top[(top.sharpe_IS>1)&(top.sharpe_OOS>3)&(top.min_sub_sharpe>-0.3)]
 txt+=('None\n' if rob.empty else table(rob,['strategy','rebalance','q','sharpe_IS','sharpe_OOS','ann_return_OOS','ann_vol_OOS','max_dd_OOS','avg_turnover_OOS','min_sub_sharpe','OOS_monthly_spread','OOS_spread_win']))
 txt+='\n\nArtifacts: data/cache/lit_factor_explore/*.parquet\n'
 atomic_text(txt,REPORT); print({'strategies':len(sigs),'metric_rows':len(metrics),'report':str(REPORT)})
if __name__=='__main__': run()
