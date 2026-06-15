import unittest
from app import compute_winner, DAILY_STEP_LIMIT


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


if __name__ == '__main__':
    unittest.main()
