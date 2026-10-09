import json
import unittest
from pathlib import Path

from engine.schema import TABLES, parse
from engine.secrets_check import find_secrets

ROOT = Path(__file__).resolve().parent.parent


class SecretsCheck(unittest.TestCase):
    def test_catches_fake_keys(self):
        # Built at runtime so this file doesn't trip its own hook.
        fakes = ["sk-" + "ant-" + "a" * 30,
                 "pat" + "A" * 14 + "." + "f" * 64,
                 "ANTHROPIC_API_" + "KEY=" + "x" * 24]
        for fake in fakes:
            self.assertTrue(find_secrets(fake), fake)

    def test_env_example_is_clean(self):
        self.assertEqual(find_secrets((ROOT / ".env.example").read_text()), [])


class Schema(unittest.TestCase):
    def test_every_table_has_client_id(self):
        for name, specs in TABLES.items():
            self.assertIn("client_id", [parse(s)[0] for s in specs], name)

    def test_primary_is_text_and_links_resolve(self):
        for name, specs in TABLES.items():
            self.assertEqual(parse(specs[0])[1]["type"], "singleLineText", name)
            for s in specs:
                target = parse(s)[2]
                if target:
                    self.assertIn(target, TABLES, s)

    def test_client_file_matches_schema(self):
        c = json.loads((ROOT / "clients" / "example.json").read_text(encoding="utf-8"))
        self.assertLessEqual(len(c["segments"]), 3)
        self.assertLessEqual(len(c["senders"]), 5)
        fields = {t: {parse(s)[0] for s in specs} for t, specs in TABLES.items()}
        for key, table in [("client", "Clients"), ("icp", "ICP")]:
            self.assertLessEqual(set(c[key]), fields[table], table)
        for s in c["senders"]:
            self.assertLessEqual(set(s), fields["Senders"])
        for e in c["examples"]:
            self.assertLessEqual(set(e), fields["Examples"])


if __name__ == "__main__":
    unittest.main()
