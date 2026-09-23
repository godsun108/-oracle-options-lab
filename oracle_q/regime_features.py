"""Regime feature scaffold for Oracle AI / Oracle Q.

Features are computed using information available at or before the signal close.
This module deliberately does not optimize thresholds or inspect future returns.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

FEATURE_VERSION="regime_v1"

def build_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    d=df.copy().sort_values("date").reset_index(drop=True)
    c=d["close"].astype(float)
    r=c.pct_change()
    d["ret_1"]=r
    d["ret_5"]=c.pct_change(5)
    d["ret_20"]=c.pct_change(20)
    d["ma20"]=c.rolling(20).mean()
    d["ma50"]=c.rolling(50).mean()
    d["ma200"]=c.rolling(200).mean()
    d["dist_ma20"]=c/d["ma20"]-1
    d["dist_ma50"]=c/d["ma50"]-1
    d["dist_ma200"]=c/d["ma200"]-1
    d["rv10"]=r.rolling(10).std()*np.sqrt(252)
    d["rv20"]=r.rolling(20).std()*np.sqrt(252)
    d["rv60"]=r.rolling(60).std()*np.sqrt(252)
    d["vol_ratio_10_60"]=d["rv10"]/d["rv60"]
    if "volume" in d:
        v=d["volume"].astype(float)
        d["volume_ratio20"]=v/v.shift(1).rolling(20).mean()
    return d

def snapshot_on_signals(features: pd.DataFrame, signal_dates) -> pd.DataFrame:
    wanted=pd.to_datetime(pd.Series(signal_dates)).dt.normalize()
    f=features.copy()
    f["date"]=pd.to_datetime(f["date"]).dt.normalize()
    out=f[f["date"].isin(set(wanted))].copy()
    out["feature_version"]=FEATURE_VERSION
    return out
