"""Sample during the cash session; scheduled launch time is not quote freshness."""
import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from research.edge_session_calendar import EASTERN, is_session, session_bounds
from research.paco_snapshot_collector import collect


def session_status(now):
    if now.tzinfo is None:raise ValueError('timezone-aware clock required')
    day=now.astimezone(EASTERN).date()
    if not is_session(day):return 'NON_SESSION'
    opening,closing=session_bounds(day)
    return 'OPEN' if opening+timedelta(minutes=2)<=now<closing-timedelta(minutes=2) else 'OUTSIDE_COLLECTION_WINDOW'


def sample(token, *, now=None, collector=collect):
    now=now or datetime.now(timezone.utc)
    status=session_status(now)
    result={'schema':'paco-session-collection-v1','observed_at':now.isoformat(),
            'session_status':status,'orders_enabled':False,'broker_fills_verified':False}
    if status!='OPEN':return {**result,'status':'SKIPPED'}
    snapshot=collector(token,today=now.astimezone(EASTERN).date())
    contracts=[c for s in snapshot['snapshots'] for c in s['contracts']]
    recent=sum(c.get('provider_quote_timing',{}).get('both_sides_within_2_seconds') is True for c in contracts)
    return {**result,'status':'COLLECTED','collection':snapshot,'contracts':len(contracts),
            'provider_recent_contracts':recent,'independent_quote_freshness_verified':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    try:r=sample(os.getenv('TRADIER_TOKEN',''))
    except (ValueError,KeyError,TypeError,OSError) as e:
        r={'schema':'paco-session-collection-v1','status':'FAILED','error_type':type(e).__name__,'orders_enabled':False}
    Path(a.output).write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('Session collection:',r['status'])
    if r['status']=='FAILED':raise SystemExit(1)
if __name__=='__main__':main()
