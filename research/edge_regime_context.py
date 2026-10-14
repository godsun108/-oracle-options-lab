"""Fixed descriptive price regimes, recorded prospectively; never a trade filter."""
import hashlib
import json
import math
import statistics
from research.edge_session_calendar import validate_sequence

METHOD = 'open-trend63-vol20-v1'
VOL_THRESHOLD_PCT = 20.0  # Fixed exploratory cutoff, not fitted or optimal.


def labels(momentum, volatility):
    return ('UP_OR_FLAT' if momentum >= 0 else 'DOWN') + '/' + ('HIGH_VOL' if volatility >= VOL_THRESHOLD_PCT else 'LOW_VOL')


def describe(bars):
    if not isinstance(bars, list) or len(bars) < 64:
        raise ValueError('regime requires 64 completed sessions')
    window = bars[-64:]
    validate_sequence([b['time'] for b in window])
    prices = [b['open'] for b in window]
    if any(not isinstance(p, (int, float)) or isinstance(p, bool) or not math.isfinite(p) or p <= 0 for p in prices):
        raise ValueError('invalid regime opening price')
    momentum = round(100 * (prices[-1] / prices[0] - 1), 12)
    returns = [math.log(prices[i] / prices[i-1]) for i in range(len(prices)-20, len(prices))]
    volatility = round(100 * statistics.stdev(returns) * math.sqrt(252), 12)
    result = {'method': METHOD, 'as_of_session': window[-1]['time'],
              'momentum_63_pct': momentum, 'annualized_volatility_20_pct': volatility,
              'volatility_threshold_pct': VOL_THRESHOLD_PCT, 'label': labels(momentum, volatility),
              'source_window_sha256': hashlib.sha256(json.dumps(window, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest(),
              'purpose': 'DESCRIPTIVE_CONTEXT_ONLY'}
    validate(result, window[-1]['time'])
    return result


def validate(context, signal_date):
    if not isinstance(context, dict) or context.get('method') != METHOD or context.get('as_of_session') != signal_date:
        raise ValueError('invalid regime method or cutoff')
    momentum = context.get('momentum_63_pct')
    volatility = context.get('annualized_volatility_20_pct')
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) for v in (momentum, volatility)) or momentum <= -100 or volatility < 0:
        raise ValueError('invalid regime statistics')
    digest = context.get('source_window_sha256')
    if (context.get('label') != labels(momentum, volatility)
            or context.get('volatility_threshold_pct') != VOL_THRESHOLD_PCT
            or context.get('purpose') != 'DESCRIPTIVE_CONTEXT_ONLY'
            or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('invalid regime classification')
