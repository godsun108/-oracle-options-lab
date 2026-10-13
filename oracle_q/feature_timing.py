"""Fail-closed checks for declared feature availability, not provider attestation."""
from datetime import date, datetime, timezone


class FeatureTimingError(ValueError):
    """A feature lacks sufficient decision-time availability evidence."""


def _timestamp(value, field):
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("an explicit timezone is required")
        result = value.astimezone(timezone.utc)
        if result != result:  # pandas NaT
            raise ValueError("missing timestamp")
        return result
    except (ValueError, TypeError, OverflowError) as exc:
        raise FeatureTimingError(f"invalid timestamp: {field}") from exc


def validate_feature_timing(frame, features, signal_date_col=None):
    """Require publication <= receipt < decision for every selected feature.

    Derived features must inherit the latest dependency publication/receipt times.
    Timestamp columns are supplied by the evidence producer, never synthesized here.
    This validates declared chronology only; source authenticity, revisions, and
    feature values require separate provenance checks. It grants no trading access.
    """
    if not features or len(set(features)) != len(features):
        raise FeatureTimingError("features must be nonempty and unique")
    required = ["decision_at"]
    if signal_date_col is not None:
        required.append(signal_date_col)
    for feature in features:
        required += [feature, feature + "__published_at", feature + "__observed_at"]
    missing = [name for name in required if name not in frame]
    if missing:
        raise FeatureTimingError("missing feature timing evidence: " + ", ".join(missing))
    for index, row in frame.iterrows():
        decision = _timestamp(row["decision_at"], "decision_at")
        if signal_date_col is not None:
            try:
                signal = date.fromisoformat(str(row[signal_date_col])[:10])
            except (ValueError, TypeError) as exc:
                raise FeatureTimingError("invalid signal date") from exc
            if decision.date() != signal:
                raise FeatureTimingError("decision UTC date must match historical signal date")
        for feature in features:
            published = _timestamp(row[feature + "__published_at"], feature + "__published_at")
            observed = _timestamp(row[feature + "__observed_at"], feature + "__observed_at")
            if not published <= observed < decision:
                raise FeatureTimingError(f"feature unavailable before decision: {feature} at row {index}")
