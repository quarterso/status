import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import check  # noqa: E402

DAY = 86400


class Check(unittest.TestCase):
    def test_old_checks_are_dropped(self):
        now = 100 * DAY
        h = {"checks": [{"t": now - 31 * DAY, "ms": {}}, {"t": now - DAY, "ms": {}}]}
        self.assertEqual([c["t"] for c in check.add_check(h, now, {})["checks"]], [now - DAY, now])

    def test_daily_share_and_empty_days(self):
        now = 100 * DAY + 10
        checks = [
            {"t": now, "ms": {"A": 120}},
            {"t": now - 5, "ms": {"A": None}},
            {"t": now - 2 * DAY, "ms": {"A": 90}},
        ]
        days = check.daily(checks, "A", now)
        self.assertEqual(len(days), check.DAYS)
        self.assertEqual(days[-1], 0.5)
        self.assertIsNone(days[-2])
        self.assertEqual(days[-3], 1)

    def test_uptime_counts_only_checked(self):
        checks = [{"t": 1, "ms": {"A": 5}}, {"t": 2, "ms": {"A": None}}, {"t": 3, "ms": {"B": 1}}]
        self.assertEqual(check.uptime(checks, "A"), 50)
        self.assertIsNone(check.uptime(checks, "C"))

    def test_page_names_what_is_down_and_escapes(self):
        now = 100 * DAY
        h = {"checks": [{"t": now, "ms": {"Sandbox gateway": None, "Rulebook feed": 80, "Website": 50}}]}
        page = check.render(h, now)
        self.assertIn("Down: Sandbox gateway", page)
        self.assertNotIn("All systems operational", page)
        h["checks"][0]["ms"]["Sandbox gateway"] = 40
        self.assertIn("All systems operational", check.render(h, now))

    def test_empty_history_renders(self):
        self.assertIn("Quarter status", check.render({"checks": []}, 100 * DAY))


if __name__ == "__main__":
    unittest.main()
