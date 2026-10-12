import copy
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from research.edge_evidence_restore import (
    WORKFLOW_PATH, decode_ledger, restore, select_artifact, select_previous,
    verify_extension,
)
from research.edge_forward_paper import advance
from tests.test_edge_forward_paper import report


def run(number, **changes):
    result = dict(id=number, run_number=number, workflow_id=1, path=WORKFLOW_PATH,
                  head_branch="main", head_sha="abc", event="push",
                  status="completed", conclusion="success")
    return dict(result, **changes)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.ledger = advance(None, report("2026-10-05", [("2026-10-05", 100.0)]))
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("edge_forward_ledger.json", json.dumps(self.ledger))
        self.archive = bundle.getvalue()
        self.artifact = dict(id=7, name="oracle-edge-lab-3", expired=False,
                             workflow_run=run(3),
                             digest="sha256:" + hashlib.sha256(self.archive).hexdigest())

    def test_latest_production_only_and_no_future_run_on_rerun(self):
        candidates = [run(8), run(7, event="pull_request"), run(6, conclusion="failure"),
                      run(5, head_branch="feature"), run(4, workflow_id=2), run(3), run(2)]
        self.assertEqual(select_previous(candidates, run(8))["id"], 3)
        with self.assertRaisesRegex(ValueError, "CONTINUITY_BLOCKED"):
            select_previous([], run(8))

    def test_missing_expired_duplicate_or_wrong_origin_fails(self):
        for artifacts in ([], [dict(self.artifact, expired=True)],
                          [self.artifact, self.artifact],
                          [dict(self.artifact, workflow_run=run(4))],
                          [dict(self.artifact, digest=None)]):
            with self.subTest(artifacts=artifacts):
                with self.assertRaises(ValueError):
                    select_artifact(artifacts, run(3))

    def test_verified_archive_and_transfer_corruption(self):
        self.assertEqual(decode_ledger(self.archive, self.artifact), self.ledger)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            decode_ledger(self.archive + b"corrupt", self.artifact)

    def test_archive_without_ledger_is_not_genesis(self):
        bundle = io.BytesIO()
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("edge_lab_report.json", "{}")
        data = bundle.getvalue()
        artifact = dict(self.artifact, digest="sha256:" + hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(ValueError, "ledger missing"):
            decode_ledger(data, artifact)

    def test_extension_preserves_history_and_rejects_valid_replacement(self):
        newer = advance(self.ledger, report("2026-10-06", [("2026-10-05", 100.0), ("2026-10-06", 101.0)]))
        self.assertEqual(verify_extension(self.ledger, newer)["status"], "PRIOR_EVENT_PREFIX_PRESERVED")
        replacement = advance(None, report("2026-10-06", [("2026-10-06", 101.0)]))
        with self.assertRaisesRegex(ValueError, "prefix changed"):
            verify_extension(self.ledger, replacement)

    def test_restore_does_not_search_older_run_when_latest_artifact_missing(self):
        replies = [run(8), {"workflow_runs": [run(3), run(2)]},
                   {"total_count": 0, "artifacts": []}]
        with tempfile.TemporaryDirectory() as folder, patch(
                "research.edge_evidence_restore.gh_json", side_effect=replies) as api:
            with self.assertRaisesRegex(ValueError, "artifact missing"):
                restore("owner/repo", 8, folder)
            self.assertEqual(api.call_count, 3)

    def test_full_restore_writes_verified_provenance(self):
        replies = [run(8), {"workflow_runs": [run(3)]},
                   {"total_count": 1, "artifacts": [self.artifact]}]
        with tempfile.TemporaryDirectory() as folder, patch(
                "research.edge_evidence_restore.gh_json", side_effect=replies), patch(
                "research.edge_evidence_restore.gh_bytes", return_value=self.archive):
            restore("owner/repo", 8, folder)
            from pathlib import Path
            manifest = json.loads((Path(folder) / "edge_restore_manifest.json").read_text())
            self.assertEqual(manifest["prior_head_sha256"], self.ledger["head_sha256"])
            self.assertEqual(manifest["previous_run_id"], 3)


if __name__ == "__main__":
    unittest.main()
