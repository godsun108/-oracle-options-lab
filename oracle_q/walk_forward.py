"""Walk-forward probability baseline for Oracle Quant Lab.

Fits only on observations strictly earlier than each prediction date. No
third-party ML dependency: regularized logistic regression via Newton updates.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def _sigmoid(z):
    return 1/(1+np.exp(-np.clip(z,-35,35)))

def _fit_logit(X,y,l2=1.0,steps=30):
    X=np.c_[np.ones(len(X)),X]
    b=np.zeros(X.shape[1])
    pen=np.eye(X.shape[1])*l2; pen[0,0]=0
    for _ in range(steps):
        p=_sigmoid(X@b); w=np.maximum(p*(1-p),1e-6)
        h=X.T@(X*w[:,None])+pen
        g=X.T@(p-y)+pen@b
        b-=np.linalg.solve(h,g)
    return b

def available_training_rows(df, decision_time, date_col="date",
                            label_available_col="exit_date"):
    """Purge same-time signals and labels not known strictly before a decision.

    Date-only exit inputs are conservatively excluded for the entire exit date.
    This checks label chronology, not feature publication/vintage provenance.
    """
    if label_available_col not in df:
        raise ValueError("label availability column required: " + label_available_col)
    decisions = pd.to_datetime(df[date_col], utc=True, errors="raise")
    available = pd.to_datetime(df[label_available_col], utc=True, errors="raise")
    cutoff = pd.to_datetime(decision_time, utc=True, errors="raise")
    if decisions.isna().any() or available.isna().any() or pd.isna(cutoff):
        raise ValueError("missing training chronology")
    if (available < decisions).any():
        raise ValueError("label availability precedes signal")
    # Midnight dates carry no intraday publication evidence: wait through that
    # calendar date instead of treating them as known at its opening midnight.
    midnight = available == available.dt.normalize()
    available = available.where(~midnight, available + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1))
    return df.loc[(decisions < cutoff) & (available < cutoff)].copy()


def walk_forward_predict(df, feature_cols, target_col, date_col="date",
                         min_train=100,l2=1.0,label_available_col="exit_date"):
    d=df.sort_values(date_col).copy()
    out=[]
    for i in range(len(d)):
        train=available_training_rows(d, d.iloc[i][date_col], date_col,
                                      label_available_col).dropna(subset=feature_cols+[target_col])
        row=d.iloc[[i]].dropna(subset=feature_cols)
        if len(train)<min_train or row.empty:
            continue
        mu=train[feature_cols].mean(); sd=train[feature_cols].std().replace(0,1)
        X=((train[feature_cols]-mu)/sd).to_numpy(float)
        y=train[target_col].to_numpy(float)
        b=_fit_logit(X,y,l2=l2)
        x=((row[feature_cols]-mu)/sd).to_numpy(float)
        p=float(_sigmoid(np.c_[np.ones(len(x)),x]@b)[0])
        base=float(y.mean())
        out.append({date_col:row.iloc[0][date_col],"p_model":p,
                    "p_unconditional":base,"n_train":len(train)})
    return pd.DataFrame(out, columns=[date_col,"p_model","p_unconditional","n_train"])

def brier(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    return float(np.mean((p-y)**2))
