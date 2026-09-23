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

def walk_forward_predict(df, feature_cols, target_col, date_col="date",
                         min_train=100,l2=1.0):
    d=df.sort_values(date_col).copy()
    out=[]
    for i in range(len(d)):
        train=d.iloc[:i].dropna(subset=feature_cols+[target_col])
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
    return pd.DataFrame(out)

def brier(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    return float(np.mean((p-y)**2))
