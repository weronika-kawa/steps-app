import unittest
from app import DAILY_STEP_LIMIT, clamp_steps, compute_winner, day_of_week_filter, parse_sync_entries


class TestLogic(unittest.TestCase):

    def test_winner_a(self):
        w, diff = compute_winner(10000, 8000, "A", "B")
        self.assertEqual(w, "A")
        self.assertEqual(diff, 2000)

    def test_winner_b(self):
        w, diff = compute_winner(5000, 9000, "A", "B")
        self.assertEqual(w, "B")
        self.assertEqual(diff, 4000)

    def test_draw(self):
        w, diff = compute_winner(7000, 7000, "A", "B")
        self.assertIsNone(w)
        self.assertEqual(diff, 0)

    def test_limit(self):
        self.assertTrue(DAILY_STEP_LIMIT == 11000)

    def test_clamp_steps(self):
        self.assertEqual(clamp_steps(-5), 0)
        self.assertEqual(clamp_steps(100), 100)
        self.assertEqual(clamp_steps(20000), DAILY_STEP_LIMIT)

    def test_parse_sync_entries(self):
        entries = [{"user_id": 1, "step_count": 100, "log_date": "2026-06-18"}]
        self.assertEqual(parse_sync_entries(entries), entries)
        self.assertEqual(parse_sync_entries({"entries": entries}), entries)
        self.assertEqual(parse_sync_entries({"unsynced_entries": entries}), entries)
        self.assertEqual(parse_sync_entries("wrong"), [])

    def test_day_of_week_filter_for_iso_date(self):
        self.assertEqual(day_of_week_filter("2026-06-15"), "Poniedziałek")


if __name__ == '__main__':
    unittest.main()
