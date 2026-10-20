import unittest
from gba_pulse.services.fetch_script import build_fetch_script


class FetchScriptTests(unittest.TestCase):
    def test_uses_only_user_supplied_official_endpoints(self):
        script = build_fetch_script()
        self.assertIn("https://www.gamerz.ba/api/poruke/broj/", script)
        self.assertIn("https://www.gamerz.ba/api/bodovi/promjena/", script)
        self.assertIn("https://www.gamerz.ba/rss", script)
        self.assertIn("credentials: 'include'", script)
        self.assertIn("window.__gbaPulseResponse", script)
        self.assertIn("window.__gbaPulseBatchId", script)
        self.assertIn("window.__gbaPulseDone", script)
        self.assertIn("Promise.race", script)
        self.assertIn("return batchId", script)


if __name__ == "__main__":
    unittest.main()
