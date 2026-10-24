"""Execute the workflows' empty-evidence JSON writers without network access."""
import json
from pathlib import Path
import subprocess
import unittest


class ArenaWorkflowFallbackTests(unittest.TestCase):
    def test_every_empty_evidence_writer_emits_valid_disabled_json(self):
        count = 0
        for name in ('arena-evidence-review.yml', 'arena-pages.yml'):
            text = (Path('.github/workflows') / name).read_text()
            for line in text.splitlines():
                if "printf '%s" not in line or '{"schema":' not in line:
                    continue
                count += 1
                # Run only the literal printf, without its destination redirect.
                command = line.strip().rsplit(' > ', 1)[0]
                result = subprocess.run(['bash', '-c', command], check=True,
                                        capture_output=True, text=True)
                with self.subTest(workflow=name, command=command):
                    data = json.loads(result.stdout)
                    self.assertIs(data['orders_enabled'], False)
                    for flag in ('broker_fills_verified', 'edge_proven', 'published'):
                        if flag in data:
                            self.assertIs(data[flag], False)
        self.assertEqual(count, 5)


if __name__ == '__main__':
    unittest.main()
