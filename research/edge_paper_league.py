"""Fixed-window, equal-capital paper league. No agents, orders or profit certificate."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from research.edge_forward_integrity_audit import audit
from research.edge_forward_paper import digest, parse_utc_timestamp
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS
from research.edge_session_calendar import next_session, session_bounds, PUBLICATION_BUFFER

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / 'research/edge_paper_league_rules.json'


def load_rules():
    rules=json.loads(RULES_PATH.read_text())
    if (rules['schema']!='oracle-q-paper-league-rules-v1'
            or sorted(rules['teams'])!=sorted(SYMBOLS)
            or sorted(rules['strategies'])!=sorted(IDS)
            or rules['sessions']!=60 or rules['capital_per_team_usd']!=10000
            or rules['cost_per_side_bps']!=25
            or rules['allocation']!='equal_weight_three_sleeves_daily'
            or rules['orders_enabled'] is not False):
        raise ValueError('unsupported league rules; register a new reviewed season')
    if next_session(rules['first_signal_session'])!=rules['first_entry_session']:
        raise ValueError('league start sessions inconsistent')
    if parse_utc_timestamp(rules['registered_at'])>=session_bounds(rules['first_signal_session'])[0]:
        raise ValueError('league rules were not registered before season')
    required={'research/edge_lab.py','research/edge_forward_paper.py','research/edge_session_calendar.json'}
    if set(rules['source_sha256'])!=required:
        raise ValueError('missing league implementation fingerprints')
    for name,expected in rules['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('league implementation changed; new reviewed season required: '+name)
    return rules


def season_windows(rules):
    windows=[]
    entry=rules['first_entry_session']
    for _ in range(rules['sessions']):
        exit_day=next_session(entry)
        windows.append((entry,exit_day))
        entry=exit_day
    return windows


def standings(ledger, *, as_of):
    rules=load_rules()
    integrity=audit(ledger)
    now=parse_utc_timestamp(as_of)
    if now<parse_utc_timestamp(rules['registered_at']):
        raise ValueError('league snapshot precedes rule registration')
    windows=season_windows(rules)
    final_eligible=session_bounds(windows[-1][1])[1]+PUBLICATION_BUFFER
    signals={}
    opens={}
    samples={}
    for event in ledger['events']:
        kind=event['type']
        if kind=='SOURCE_OPEN_CHECKPOINT':
            opens[event['symbol'],event['open_date']]=event['open_price']
        elif kind=='SIGNAL_REGISTERED':
            signals[event['symbol'],event['strategy_id'],event['signal_date']]=event
        elif kind=='PAPER_OUTCOME_OBSERVED':
            symbol,sid=event['symbol'],event['strategy_id']
            if symbol not in rules['teams'] or sid not in rules['strategies']:
                raise ValueError('unregistered league competitor')
            signal=signals[symbol,sid,event['signal_date']]
            window=event['entry_date'],event['exit_date']
            if event['signal_date']<rules['first_signal_session'] or window not in windows:
                continue
            if parse_utc_timestamp(signal['registered_at'])<parse_utc_timestamp(rules['registered_at']):
                raise ValueError('league signal predates rules')
            if now<session_bounds(window[1])[1]+PUBLICATION_BUFFER:
                raise ValueError('league outcome not yet eligible')
            key=symbol,sid,window
            if key in samples:
                raise ValueError('duplicate competitor window; cannot choose best observation')
            gross=opens[symbol,window[1]]/opens[symbol,window[0]]-1
            samples[key]=(signal['signal']*(gross-2*rules['cost_per_side_bps']/10000),gross)
    teams=[]
    for symbol in rules['teams']:
        complete=[w for w in windows if all((symbol,sid,w) in samples for sid in rules['strategies'])]
        missing=[list(w) for w in windows if w not in complete
                 and now>=session_bounds(w[1])[1]+PUBLICATION_BUFFER]
        row={'team':symbol,'completed_common_sessions':len(complete),
             'required_sessions':rules['sessions'],'missing_eligible_windows':missing,
             'status':'INCOMPLETE_EVIDENCE' if missing else 'ACCUMULATING_FORWARD_EVIDENCE',
             'net_return_pct':None,'max_drawdown_pct':None,'cost_free_market_return_pct':None,
             'excess_vs_cost_free_market_pct':None,'ending_hypothetical_capital_usd':None,
             'eligible_for_live_trading':False,'edge_proven':False}
        # No partial-period ranking: competitors must cover the identical window.
        if len(complete)==rules['sessions'] and now>=final_eligible:
            equity=peak=benchmark=1.0
            drawdown=0.0
            for window in windows:
                values=[samples[symbol,sid,window] for sid in rules['strategies']]
                daily=sum(v[0] for v in values)/len(values)
                if daily<=-1:
                    raise ValueError('paper capital exhausted; model cannot continue')
                equity*=1+daily
                benchmark*=1+values[0][1]
                peak=max(peak,equity)
                drawdown=min(drawdown,equity/peak-1)
            row.update(status='FIXED_WINDOW_DESCRIPTIVE_RESULT',
                       net_return_pct=round(100*(equity-1),6),
                       max_drawdown_pct=round(100*drawdown,6),
                       cost_free_market_return_pct=round(100*(benchmark-1),6),
                       excess_vs_cost_free_market_pct=round(100*(equity-benchmark),6),
                       ending_hypothetical_capital_usd=round(rules['capital_per_team_usd']*equity,2))
        teams.append(row)
    ranked=sorted((r for r in teams if r['status']=='FIXED_WINDOW_DESCRIPTIVE_RESULT'),
                  key=lambda r:(-r['net_return_pct'],r['team']))
    return {'schema':'oracle-q-paper-league-v1','season_id':rules['season_id'],
            'as_of':now.isoformat(),'rules_sha256':digest(rules),
            'ledger_head_sha256':ledger['head_sha256'],'integrity_audit':integrity,
            'first_entry_session':windows[0][0],'last_exit_session':windows[-1][1],
            'season_results_eligible_at':final_eligible.isoformat(),
            'hypothesis_family_size':len(rules['teams'])*len(rules['strategies']),
            'teams':teams,'descriptive_order_by_net_return':[r['team'] for r in ranked],
            'profitable_team_certified':None,'orders_enabled':False,'eligible_for_live_trading':False,
            'limitations':[
                'Teams are fixed strategy groups, not autonomous AI researchers. No adaptive selection or trading.',
                'Equal daily sleeve weights and fixed round-trip costs are hypothetical; dividends, interest, taxes, actual spreads and fills are not verified.',
                'Only complete identical windows enter descriptive ordering; absent teams remain explicitly incomplete. A positive return or first place does not certify an edge.',
                'Hashes and semantic audits detect inconsistencies, not coordinated rewriting of code and evidence or false provider data. External attestation is not provided.',
                'New strategies, parameters or repaired source history require separate prospective versions; no retroactive replacement of results.',
                'Individual candidate review continues independently; this league does not authorize capital or reduce multiple-testing obligations.']}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--ledger',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    result=standings(json.loads(Path(args.ledger).read_text()),as_of=datetime.now(timezone.utc).isoformat())
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('Paper league:',len(result['teams']),'teams;',len(result['descriptive_order_by_net_return']),
          'complete teams; certified profitable: none')


if __name__=='__main__':
    main()
