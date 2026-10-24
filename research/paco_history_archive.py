"""Bounded five-year SPX requests; retain evidence without asserting full coverage."""
import argparse
import hashlib
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from research.multi_market_observer import request_history
from research.edge_session_calendar import eligible_cutoff


def windows(end):
    start=date(1928,1,3)
    if end<start or end.year>2100:raise ValueError('unsupported archive range')
    while start<=end:
        stop=min(date(start.year+5,1,1)-timedelta(days=1),end)
        yield start,stop
        start=stop+timedelta(days=1)


def archive(token, *, end=None, fetch=request_history):
    end=end or eligible_cutoff()
    result={'schema':'paco-spx-history-archive-v1','source':'tradier','symbol':'SPX',
            'requested_start':'1928-01-03','requested_end':end.isoformat(),'chunks':[],
            'history_coverage_complete_verified':False,'independent_price_series_verified':False,
            'orders_enabled':False,'warning':'Request coverage is not verified session or price coverage.'}
    if not token:return {**result,'status':'TOKEN_MISSING','bars':0}
    merged=[]
    for start,stop in windows(end):
        receipt={'start':start.isoformat(),'end':stop.isoformat(),'received_at':None}
        try:
            raw=fetch('SPX',token,start.isoformat(),stop.isoformat())
            receipt['received_at']=datetime.now(timezone.utc).isoformat()
            text=json.dumps(raw,sort_keys=True,separators=(',',':'),allow_nan=True)
            receipt['parsed_payload_text']=text
            receipt['sha256']=hashlib.sha256(text.encode()).hexdigest()
            if not isinstance(raw,list):raise ValueError('invalid rows')
            seen=set();clean=[]
            for row in raw:
                day=date.fromisoformat(row['date'][:10]);value=row['close']
                if isinstance(value,bool):raise ValueError('invalid close')
                close=float(value)
                if not start<=day<=stop or day.weekday()>=5 or day in seen or not math.isfinite(close) or close<=0:
                    raise ValueError('invalid or duplicate bar')
                seen.add(day);clean.append({'date':day.isoformat(),'close':close})
            receipt.update(status='RETURNED' if clean else 'EMPTY',bars=len(clean))
            merged.extend(clean)
        except (ValueError,KeyError,TypeError,OSError) as e:
            receipt.update(status='FAILED',error_type=type(e).__name__)
        result['chunks'].append(receipt)
    merged.sort(key=lambda r:r['date'])
    result.update(status='COLLECTED_UNVERIFIED' if merged else 'NO_HISTORY',bars=len(merged),
                  first_date=merged[0]['date'] if merged else None,last_date=merged[-1]['date'] if merged else None,
                  rows=merged,empty_or_failed_windows=sum(c['status']!='RETURNED' for c in result['chunks']))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    r=archive(os.getenv('TRADIER_TOKEN',''))
    Path(a.output).write_text(json.dumps(r,sort_keys=True,indent=2,allow_nan=False)+'\n')
    print('SPX archive:',r['status'],'bars:',r['bars'])
if __name__=='__main__':main()
