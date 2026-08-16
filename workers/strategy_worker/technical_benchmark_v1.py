"""Baseline technical-strategy benchmark for Leverage."""
from __future__ import annotations
import argparse, json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import numpy as np
import pandas as pd

ANNUAL_DAYS = 365
DEFAULT_FEE_BPS = 4.0
DEFAULT_SLIPPAGE_BPS = 2.0

@dataclass(frozen=True)
class StrategySpec:
    name: str
    signal_fn: Callable[[pd.DataFrame], pd.Series]

def sma_trend(df):
    fast=df.close.rolling(20).mean(); slow=df.close.rolling(50).mean()
    return (fast>slow).astype(int)-(fast<slow).astype(int)

def rsi_momentum(df):
    delta=df.close.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); rsi=100-(100/(1+(gain/loss.replace(0,np.nan))))
    s=pd.Series(0,index=df.index,dtype=int); s[rsi>55]=1; s[rsi<45]=-1; return s

def donchian_breakout(df):
    hi=df.high.rolling(20).max().shift(1); lo=df.low.rolling(20).min().shift(1); s=pd.Series(0,index=df.index,dtype=int); s[df.close>hi]=1; s[df.close<lo]=-1; return s

def bollinger_reversion(df):
    mid=df.close.rolling(20).mean(); sd=df.close.rolling(20).std(ddof=0); up=mid+2*sd; lo=mid-2*sd; s=pd.Series(0,index=df.index,dtype=int); s[df.close<lo]=1; s[df.close>up]=-1; return s

STRATEGIES=[StrategySpec('Trend Following',sma_trend),StrategySpec('Momentum',rsi_momentum),StrategySpec('Breakout',donchian_breakout),StrategySpec('Mean Reversion',bollinger_reversion)]

def load_data(path):
    df=pd.read_csv(path); required=['timestamp','open','high','low','close','volume']; missing=[c for c in required if c not in df.columns]
    if missing: raise ValueError(f'Missing columns: {missing}')
    df.timestamp=pd.to_datetime(df.timestamp,utc=True)
    for c in required[1:]: df[c]=pd.to_numeric(df[c],errors='raise')
    return df.sort_values('timestamp').reset_index(drop=True)

def backtest(df, signal, fee_bps, slippage_bps):
    signal=signal.fillna(0).clip(-1,1).astype(int); position=signal.shift(1).fillna(0); asset_ret=df.close.pct_change().fillna(0); gross=position*asset_ret; turnover=position.diff().abs().fillna(position.abs()); costs=turnover*((fee_bps+slippage_bps)/10000.0); net=gross-costs; equity=(1+net).cumprod(); peak=equity.cummax(); dd=equity/peak-1; vol=float(net.std(ddof=1)); sharpe=float(net.mean()/vol*np.sqrt(ANNUAL_DAYS)) if vol>0 else 0.0; active=position!=0; trades=int(((position!=position.shift(1))&active).sum()); wins=int((net[active]>0).sum()); active_rows=int(active.sum()); return {'total_return':float(equity.iloc[-1]-1),'max_drawdown':float(dd.min()),'sharpe':sharpe,'trade_count':trades,'win_rate':float(wins/active_rows) if active_rows else 0.0}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--instrument',required=True); p.add_argument('--split',type=float,default=.70); p.add_argument('--fee-bps',type=float,default=DEFAULT_FEE_BPS); p.add_argument('--slippage-bps',type=float,default=DEFAULT_SLIPPAGE_BPS); p.add_argument('--output',default='dashboard/strategy_results.json'); a=p.parse_args()
    df=load_data(a.input); split=int(len(df)*a.split)
    if split<100 or len(df)-split<50: raise ValueError(f'Insufficient history: {len(df)} rows')
    is_df=df.iloc[:split].copy(); oos_df=df.iloc[split:].copy(); results={'version':'technical-benchmark-v1','instrument':a.instrument,'rows':len(df),'split':{'in_sample_rows':len(is_df),'out_of_sample_rows':len(oos_df),'ratio':a.split},'cost_model':{'fee_bps':a.fee_bps,'slippage_bps':a.slippage_bps},'strategies':[]}
    for spec in STRATEGIES:
        sig=spec.signal_fn(df); ir=backtest(is_df,sig.iloc[:split],a.fee_bps,a.slippage_bps); orr=backtest(oos_df,sig.iloc[split:].reset_index(drop=True),a.fee_bps,a.slippage_bps); results['strategies'].append({'strategy':spec.name,'in_sample':ir,'out_of_sample':orr,'robust':bool(orr['total_return']>0 and orr['max_drawdown']>-0.35)})
    results['honesty_rule']='Fixed baseline rules only; no parameter optimization; research evidence, not a trading recommendation.'
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(results,indent=2),encoding='utf-8'); print(json.dumps(results,indent=2))

if __name__=='__main__': main()
