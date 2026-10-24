"""Reconcile closed simulated trades to prospective signals and source marks.

This report is accounting evidence, never broker-fill or profitability certification.
"""
import argparse
import json
import math
from pathlib import Path
from research.edge_forward_integrity_audit import audit
from research.agent_forward_replay import replay
from research.edge_forward_paper import parse_utc_timestamp
from research.edge_session_calendar import next_session, session_bounds
from research.edge_lab import IDS
from research.multi_market_observer import SYMBOLS


def build(ledger):
    integrity = audit(ledger)
    signals, marks = {}, {}
    for event in ledger['events']:
        if event['symbol'] not in SYMBOLS:
            raise ValueError('unknown market')
        if 'strategy_id' in event and event['strategy_id'] not in IDS:
            raise ValueError('unknown strategy')
        if event['type'] == 'SOURCE_OPEN_CHECKPOINT':
            marks[event['symbol'], event['open_date']] = event
        elif event['type'] == 'SIGNAL_REGISTERED' and event.get('registered_at'):
            day = next_session(event['signal_date'])
            if parse_utc_timestamp(event['registered_at']) < session_bounds(day)[0]:
                signals[event['symbol'], event['strategy_id'], day] = event
    portfolios = replay(ledger)['portfolios']
    agents = []
    for agent_id, state in sorted(portfolios.items()):
        symbol, strategy = agent_id.split('::')
        entry = None
        closed = []
        fees = 0.0
        for event in state['events']:
            if event['action'] == 'HOLD':
                continue
            day = event['observed_at'][:10]
            decision = signals[symbol, strategy, day]
            evidence = {'observed_at': event['observed_at'], 'price': event['price'],
                        'signal_sha256': decision['event_sha256'],
                        'registered_at': decision['registered_at'],
                        'source_checkpoint_sha256': marks[symbol, day]['event_sha256'],
                        'portfolio_event_sha256': event['event_sha256']}
            if event['action'] == 'SIMULATED_BUY':
                if entry is not None:
                    raise ValueError('overlapping simulated entries')
                qty = event['quantity_after']
                entry_fee = qty * event['price'] * event['cost_bps'] / 10000
                fees += entry_fee
                entry = dict(evidence, quantity=qty, entry_cost=entry_fee,
                             entry_notional=qty * event['price'])
            else:
                if entry is None:
                    raise ValueError('exit without entry')
                qty = entry['quantity']
                exit_fee = qty * event['price'] * event['cost_bps'] / 10000
                fees += exit_fee
                gross = qty * (event['price'] - entry['price'])
                costs = entry['entry_cost'] + exit_fee
                closed.append({'entry': entry, 'exit': evidence,
                               'gross_pnl': gross, 'assumed_costs': costs,
                               'net_pnl': gross - costs})
                entry = None
        realized = sum(t['net_pnl'] for t in closed)
        if not math.isclose(realized, state['realized_pnl'], abs_tol=1e-7):
            raise ValueError('round-trip realized P&L does not reconcile')
        mark = state['last_mark']
        unrealized = (state['quantity'] * (mark['price'] - state['average_entry'])
                      if state['quantity'] else 0.0)
        equity = state['cash'] + (state['quantity'] * mark['price'] if mark else 0.0)
        if not math.isclose(equity - state['starting_cash'], realized + unrealized, abs_tol=1e-7):
            raise ValueError('equity does not reconcile')
        agents.append({'agent_id': agent_id, 'closed_trades': closed,
                       'closed_trade_count': len(closed), 'open_trade': entry,
                       'last_mark': mark, 'equity': equity, 'realized_pnl': realized,
                       'unrealized_pnl': unrealized, 'assumed_costs_paid': fees,
                       'accounting_reconciled': True})
    return {'schema': 'oracle-q-agent-trade-cycles-v1',
            'status': 'SIMULATED_CYCLES_RECONCILED',
            'ledger_head_sha256': ledger['head_sha256'],
            'settled_observations': integrity['forward_outcomes'],
            'closed_trade_count': sum(a['closed_trade_count'] for a in agents),
            'open_trade_count': sum(a['open_trade'] is not None for a in agents),
            'agents': agents, 'orders_enabled': False, 'broker_fills_verified': False,
            'edge_proven': False,
            'warning': 'Prospective signals with delayed historical opening-price simulation. Closed trades differ from one-session settled observations. Costs are assumptions; no broker execution or independent source attestation.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = build(json.loads(Path(args.ledger).read_text()))
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n')
    print('Reconciled simulated trades:', result['closed_trade_count'], 'closed;', result['open_trade_count'], 'open')


if __name__ == '__main__':
    main()
