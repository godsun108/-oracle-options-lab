from oracle_q.self_repair import classify, patch_is_mechanical

def test_known_parser_failure_is_safe():
    r=classify("Traceback\nStopIteration:")
    assert r.safe is True
    assert r.kind=="schema_parse"
    assert r.action=="inspect_source_schema"

def test_unknown_failure_halts():
    r=classify("mysterious catastrophe")
    assert r.safe is False
    assert r.action=="halt_and_report"

def test_semantic_changes_blocked():
    assert not patch_is_mechanical("change signal threshold")
    assert not patch_is_mechanical("alter target label")
    assert not patch_is_mechanical("change execution assumptions")

def test_mechanical_patch_allowed():
    assert patch_is_mechanical("fix csv date parser and artifact path")
