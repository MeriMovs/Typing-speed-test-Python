"""Tests for the game logic. Run them with:  python3 -m unittest"""

import tempfile
import unittest
from pathlib import Path

from typing_speed_test import (
    TEXTS,
    TypingTest,
    best_score,
    load_scores,
    save_score,
    top_scores,
    wrap_text,
)


class FakeClock:
    """A clock the tests control, so they do not have to really wait."""

    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def type_text(test, text):
    for char in text:
        test.type_char(char)


class TypingTestTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()

    def test_timer_starts_on_first_key(self):
        test = TypingTest("hello", self.clock)
        self.clock.now += 50
        self.assertEqual(test.elapsed, 0)
        test.type_char("h")
        self.clock.now += 2
        self.assertEqual(test.elapsed, 2)

    def test_wpm_for_perfect_round(self):
        test = TypingTest("a" * 50, self.clock)
        test.type_char("a")
        self.clock.now += 60
        type_text(test, "a" * 49)
        self.assertTrue(test.finished)
        self.assertAlmostEqual(test.wpm, 10)  # 50 chars = 10 words in 1 minute
        self.assertEqual(test.accuracy, 100)

    def test_wrong_characters_do_not_count_towards_wpm(self):
        test = TypingTest("aaaaaaaaaa", self.clock)
        test.type_char("a")
        self.clock.now += 60
        type_text(test, "aaaabbbbb")
        self.assertEqual(test.correct_chars, 5)
        self.assertAlmostEqual(test.wpm, 1)

    def test_fixed_mistake_still_lowers_accuracy(self):
        test = TypingTest("abc", self.clock)
        type_text(test, "ax")
        test.backspace()
        type_text(test, "bc")
        self.assertTrue(test.finished)
        self.assertEqual(test.correct_chars, 3)
        self.assertEqual(test.mistakes, 1)
        self.assertEqual(test.accuracy, 75)

    def test_backspace_with_nothing_typed_is_safe(self):
        test = TypingTest("abc", self.clock)
        test.backspace()
        self.assertEqual(test.typed, "")

    def test_clock_stops_when_finished(self):
        test = TypingTest("ab", self.clock)
        test.type_char("a")
        self.clock.now += 5
        test.type_char("b")
        self.clock.now += 100
        self.assertEqual(test.elapsed, 5)

    def test_typing_after_finish_is_ignored(self):
        test = TypingTest("a", self.clock)
        type_text(test, "ab")
        self.assertEqual(test.typed, "a")
        self.assertEqual(test.total_keys, 1)

    def test_no_typing_gives_safe_stats(self):
        test = TypingTest("abc", self.clock)
        self.assertEqual(test.wpm, 0)
        self.assertEqual(test.accuracy, 100)


class WrapTextTests(unittest.TestCase):
    def test_wrapping_keeps_every_character(self):
        for texts in TEXTS.values():
            for text in texts:
                for width in (10, 30, 70):
                    lines = wrap_text(text, width)
                    self.assertEqual("".join(lines), text)
                    self.assertTrue(all(len(line) <= width for line in lines))


class ScoreTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "scores.json"

    def test_missing_file_means_no_scores(self):
        self.assertEqual(load_scores(self.path), [])

    def test_damaged_file_means_no_scores(self):
        self.path.write_text("not json")
        self.assertEqual(load_scores(self.path), [])

    def test_record_is_reported_per_level(self):
        self.assertTrue(save_score("Easy", 40, 95, self.path))
        self.assertFalse(save_score("Easy", 30, 95, self.path))
        self.assertTrue(save_score("Easy", 50, 95, self.path))
        self.assertTrue(save_score("Hard", 20, 95, self.path))
        self.assertEqual(best_score(load_scores(self.path), "Easy"), 50)

    def test_top_scores_are_sorted_and_limited(self):
        for wpm in (10, 50, 30):
            save_score("Easy", wpm, 90, self.path)
        fastest = top_scores(load_scores(self.path), count=2)
        self.assertEqual([score["wpm"] for score in fastest], [50, 30])


if __name__ == "__main__":
    unittest.main()
