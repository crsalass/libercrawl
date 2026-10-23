"""Offline, dependency-free tests for the public engine patcher."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from patch_engine import PatchError, patch_compose  # noqa: E402

OLD_PROBE = 'test: ["CMD", "rabbitmq-diagnostics", "-q", "check_running"]'
NEW_PROBE = 'test: ["CMD", "gosu", "rabbitmq", "rabbitmq-diagnostics", "-q", "check_running"]'


def make_compose(probe: str = OLD_PROBE, *, eol: str = "\n") -> str:
    return eol.join([
        "services:",
        "  api:",
        "    healthcheck:",
        '      test: ["CMD", "true"]',
        "      interval: 5s",
        "      timeout: 5s",
        "      retries: 3",
        "      start_period: 5s",
        "  rabbitmq:",
        "    command: rabbitmq-server",
        "    healthcheck:",
        "      " + probe,
        "      interval: 5s",
        "      timeout: 5s",
        "      retries: 3",
        "      start_period: 5s",
        "    logging:",
        '      driver: "json-file"',
        "  redis:",
        "    image: redis",
        "",
    ])


class PatchEngineTests(unittest.TestCase):
    def test_updates_only_rabbitmq(self):
        actual = patch_compose(make_compose())
        self.assertIn("      " + NEW_PROBE, actual)
        self.assertIn("      start_period: 120s", actual)
        self.assertIn("      retries: 10", actual)
        self.assertIn("      timeout: 10s", actual)
        self.assertIn("      interval: 10s", actual)
        self.assertIn('      test: ["CMD", "true"]\n      interval: 5s', actual)
        self.assertIn('    logging:\n      driver: "json-file"', actual)

    def test_already_patched_probe_gets_updated_timing(self):
        updated = patch_compose(make_compose(NEW_PROBE))
        self.assertIn("      start_period: 120s", updated)
        self.assertIn("      " + NEW_PROBE, updated)

    def test_idempotent(self):
        once = patch_compose(make_compose())
        self.assertEqual(once, patch_compose(once))

    def test_preserves_windows_newlines(self):
        updated = patch_compose(make_compose(eol="\r\n"))
        self.assertEqual(updated.count("\n"), updated.count("\r\n"))

    def test_rejects_unknown_probe(self):
        with self.assertRaises(PatchError):
            patch_compose(make_compose('test: ["CMD", "true"]'))

    def test_rejects_unsupported_timing(self):
        with self.assertRaises(PatchError):
            patch_compose(make_compose().replace("      start_period: 5s\n    logging:", "      start_period: 44s\n    logging:"))

    def test_rejects_wrong_service(self):
        with self.assertRaises(PatchError):
            patch_compose(make_compose().replace("  rabbitmq:\n", "  other:\n"))

    def test_rejects_duplicate_probe(self):
        with self.assertRaises(PatchError):
            patch_compose(make_compose() + "  another:\n    healthcheck:\n      " + OLD_PROBE + "\n")


if __name__ == "__main__":
    unittest.main()
