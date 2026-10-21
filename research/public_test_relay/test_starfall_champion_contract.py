"""Public synthetic Starfall champion contract; NO private source or secrets.
Passing this does not verify Sovereign-Core settlement or production.
"""
import hashlib
import json
import re
import unittest

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def synthetic_champion(season, sequence):
    if not re.fullmatch(r"[a-z0-9-]{1,32}", season):
        raise ValueError("invalid season")
    if not isinstance(sequence, int) or not 1 <= sequence <= 999999999999:
        raise ValueError("invalid sequence")
    token = f"starfall-champion-{season}-{sequence}"
    metadata = dict(schema="earthchain.game-collectible.v1", gameId="starfall",
                    skinId="starfall-celestial-crown", tokenId=token,
                    testOnly=True, achievement="world-record-legacy",
                    season=season, recordSequence=sequence)
    return token, hashlib.sha256(canonical(metadata).encode()).hexdigest()

class ChampionPublicContract(unittest.TestCase):
    def test_deterministic_metadata(self):
        token, digest = synthetic_champion("pilot-1", 42)
        self.assertEqual(token, "starfall-champion-pilot-1-42")
        self.assertRegex(digest, r"^[a-f0-9]{64}$")
        self.assertEqual(digest, synthetic_champion("pilot-1", 42)[1])

    def test_distinct_records_have_distinct_hashes(self):
        self.assertNotEqual(synthetic_champion("pilot-1", 42)[1],
                            synthetic_champion("pilot-1", 43)[1])

    def test_reject_invalid_identifiers(self):
        for season, sequence in [("../private", 42), ("pilot-1", 0),
                                 ("pilot-1", -1), ("pilot-1", 10**12)]:
            with self.subTest(season=season, sequence=sequence):
                with self.assertRaises(ValueError):
                    synthetic_champion(season, sequence)

if __name__ == "__main__":
    unittest.main()
