"""Typing Speed Test - a terminal game that measures how fast you type.

Run it with:  python3 typing_speed_test.py

Pick a level, type the text shown on screen, and get your speed in words per
minute (WPM) and your accuracy. The best scores are saved in scores.json.
"""

import curses
import json
import random
import textwrap
import time
from datetime import date
from pathlib import Path

SCORES_FILE = Path(__file__).with_name("scores.json")
MAX_LINE_WIDTH = 70
TOP_SCORES_SHOWN = 5

# Typing speed is measured in "standard words" of 5 characters, so that long
# and short words count fairly.
CHARS_PER_WORD = 5

# Key codes that curses gives us as text.
ESCAPE = "\x1b"
ENTER_KEYS = ("\n", "\r", curses.KEY_ENTER)
BACKSPACE_KEYS = ("\x7f", "\b", curses.KEY_BACKSPACE)

# Colour pair numbers, set up in setup_colours().
GREEN = 1
RED = 2
CYAN = 3

TEXTS = {
    "Easy": [
        "The sun is warm and the sky is blue today.",
        "My dog likes to run and play in the park.",
        "We ate lunch at school and then went home.",
        "She has a red bike and a small green bag.",
        "I read a good book before I went to sleep.",
        "The cat sat on the mat and looked at the bird.",
    ],
    "Medium": [
        "Learning to type quickly takes patience, but regular practice "
        "makes a surprising difference after only a few weeks.",
        "The library was quiet this morning, so I finished my history "
        "homework and started planning the science project.",
        "Every computer program is a list of instructions, and the "
        "machine follows them exactly as they were written.",
        "Our class visited the museum on Friday, where we saw ancient "
        "maps, old coins, and a huge dinosaur skeleton.",
        "If you keep your eyes on the screen instead of your hands, "
        "your speed will improve much faster than you expect.",
    ],
    "Hard": [
        "Python was released in 1991 by Guido van Rossum; today, it is "
        "used for web development, data science, and automation!",
        "\"Could you check the file?\" asked Maria. \"It's saved in the "
        "folder named reports_2024, on the second drive.\"",
        "A function such as print(len(words)) evaluates the inner call "
        "first, then passes that result (a number) to print.",
        "The experiment measured 37.5 degrees at 09:45, yet by 14:30 "
        "the temperature had risen by almost 12%.",
        "Good passwords mix UPPER and lower case letters, digits like "
        "7 or 9, and symbols such as #, $, or &.",
    ],
}


class TypingTest:
    """Keeps track of one round: the text, what was typed, and the timing."""

    def __init__(self, target, clock=time.monotonic):
        self.target = target
        self.typed = ""
        self.clock = clock
        self.start_time = None
        self.end_time = None
        self.correct_keys = 0
        self.total_keys = 0

    def type_char(self, char):
        """Record one typed character. The timer starts on the first one."""
        if self.finished:
            return
        if self.start_time is None:
            self.start_time = self.clock()

        self.total_keys += 1
        if char == self.target[len(self.typed)]:
            self.correct_keys += 1
        self.typed += char

        if len(self.typed) == len(self.target):
            self.end_time = self.clock()

    def backspace(self):
        """Delete the last character. The original mistake still counts."""
        if not self.finished:
            self.typed = self.typed[:-1]

    @property
    def finished(self):
        return self.end_time is not None

    @property
    def elapsed(self):
        """Seconds since the first key press."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.finished else self.clock()
        return end - self.start_time

    @property
    def correct_chars(self):
        """How many characters on screen match the text right now."""
        return sum(1 for typed, wanted in zip(self.typed, self.target)
                   if typed == wanted)

    @property
    def wpm(self):
        """Words per minute, counting only correct characters."""
        if self.elapsed == 0:
            return 0.0
        return (self.correct_chars / CHARS_PER_WORD) / (self.elapsed / 60)

    @property
    def accuracy(self):
        """Percentage of all key presses that were right the first time."""
        if self.total_keys == 0:
            return 100.0
        return self.correct_keys / self.total_keys * 100

    @property
    def mistakes(self):
        return self.total_keys - self.correct_keys


def wrap_text(text, width):
    """Split text into lines, keeping every character (spaces included).

    Joining the lines gives back the original text, so a position in the text
    can be matched to a position on the screen.
    """
    return textwrap.wrap(text, width, drop_whitespace=False)


def load_scores(path=SCORES_FILE):
    """Read the saved scores. A missing or damaged file means no scores yet."""
    try:
        scores = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    return scores if isinstance(scores, list) else []


def save_score(level, wpm, accuracy, path=SCORES_FILE):
    """Add a score to the file and return True if it beats the level's best."""
    scores = load_scores(path)
    best = best_score(scores, level)
    scores.append({
        "level": level,
        "wpm": round(wpm, 1),
        "accuracy": round(accuracy, 1),
        "date": date.today().isoformat(),
    })
    path.write_text(json.dumps(scores, indent=2))
    return best is None or wpm > best


def best_score(scores, level):
    """Return the highest WPM for a level, or None if it has no scores."""
    return max((s["wpm"] for s in scores if s["level"] == level), default=None)


def top_scores(scores, count=TOP_SCORES_SHOWN):
    """Return the fastest scores, best first."""
    return sorted(scores, key=lambda s: s["wpm"], reverse=True)[:count]


def setup_colours():
    curses.use_default_colors()
    curses.init_pair(GREEN, curses.COLOR_GREEN, -1)
    curses.init_pair(RED, curses.COLOR_WHITE, curses.COLOR_RED)
    curses.init_pair(CYAN, curses.COLOR_CYAN, -1)


def show(stdscr, y, x, text, style=curses.A_NORMAL):
    """Draw text, ignoring anything that does not fit in the window."""
    try:
        stdscr.addstr(y, x, text, style)
    except curses.error:
        pass


def read_key(stdscr):
    """Return the next key, or None if nothing was pressed in time."""
    try:
        return stdscr.get_wch()
    except curses.error:
        return None


def wait_for_enter(stdscr):
    """Only Enter continues, so fast typers do not skip the screen by accident."""
    curses.flushinp()
    while read_key(stdscr) not in ENTER_KEYS:
        pass


def draw_test(stdscr, test, level):
    stdscr.erase()
    screen_width = stdscr.getmaxyx()[1]
    line_width = max(10, min(screen_width - 4, MAX_LINE_WIDTH))

    show(stdscr, 1, 2, f"Level: {level}", curses.A_BOLD)
    show(stdscr, 2, 2, f"Time: {test.elapsed:5.1f}s   WPM: {test.wpm:5.1f}   "
                       f"Accuracy: {test.accuracy:5.1f}%",
         curses.color_pair(CYAN))

    # Draw the text one character at a time, coloured by what was typed.
    position = 0
    cursor = (4, 2)
    lines = wrap_text(test.target, line_width)
    for row, line in enumerate(lines, start=4):
        for column, char in enumerate(line, start=2):
            if position == len(test.typed):
                cursor = (row, column)
                style = curses.A_NORMAL
            elif position > len(test.typed):
                style = curses.A_DIM
            elif test.typed[position] == char:
                style = curses.color_pair(GREEN)
            else:
                style = curses.color_pair(RED)
            show(stdscr, row, column, char, style)
            position += 1

    show(stdscr, 5 + len(lines), 2, "Backspace: fix a mistake   Esc: back to menu",
         curses.A_DIM)
    try:
        stdscr.move(*cursor)
    except curses.error:
        pass
    stdscr.refresh()


def play_round(stdscr, level):
    """Run one round and return the finished test, or None if cancelled."""
    test = TypingTest(random.choice(TEXTS[level]))
    curses.flushinp()
    stdscr.timeout(100)  # Wake up 10 times a second to refresh the timer.

    while not test.finished:
        draw_test(stdscr, test, level)
        key = read_key(stdscr)
        if key == ESCAPE:
            stdscr.timeout(-1)
            return None
        if key in BACKSPACE_KEYS:
            test.backspace()
        elif isinstance(key, str) and key.isprintable():
            test.type_char(key)

    stdscr.timeout(-1)
    return test


def show_results(stdscr, test, level):
    new_record = save_score(level, test.wpm, test.accuracy)

    stdscr.erase()
    show(stdscr, 1, 2, "Results", curses.A_BOLD)
    show(stdscr, 3, 2, f"Speed:     {test.wpm:.1f} WPM", curses.color_pair(GREEN))
    show(stdscr, 4, 2, f"Accuracy:  {test.accuracy:.1f}%")
    show(stdscr, 5, 2, f"Mistakes:  {test.mistakes}")
    show(stdscr, 6, 2, f"Time:      {test.elapsed:.1f} seconds")
    if new_record:
        show(stdscr, 8, 2, f"New best score for {level}!",
             curses.color_pair(CYAN) | curses.A_BOLD)
    show(stdscr, 10, 2, "Press Enter to return to the menu", curses.A_DIM)
    stdscr.refresh()
    wait_for_enter(stdscr)


def show_scores(stdscr):
    scores = top_scores(load_scores())

    stdscr.erase()
    show(stdscr, 1, 2, "Best Scores", curses.A_BOLD)
    if not scores:
        show(stdscr, 3, 2, "No scores yet. Play a round first!")
    for row, score in enumerate(scores, start=3):
        show(stdscr, row, 2, f"{row - 2}. {score['wpm']:6.1f} WPM   "
                             f"{score['accuracy']:5.1f}%   "
                             f"{score['level']:<7} {score['date']}")
    show(stdscr, len(scores) + 4, 2, "Press Enter to return to the menu",
         curses.A_DIM)
    stdscr.refresh()
    wait_for_enter(stdscr)


def show_menu(stdscr):
    """Show the menu and return the key that was chosen."""
    levels = list(TEXTS)

    stdscr.erase()
    show(stdscr, 1, 2, "TYPING SPEED TEST", curses.color_pair(CYAN) | curses.A_BOLD)
    for row, level in enumerate(levels, start=3):
        show(stdscr, row, 2, f"{row - 2}. {level}")
    show(stdscr, 7, 2, "S. Best scores")
    show(stdscr, 8, 2, "Q. Quit")
    show(stdscr, 10, 2, "Choose an option. The timer starts when you start typing.",
         curses.A_DIM)
    stdscr.refresh()

    while True:
        key = read_key(stdscr)
        if isinstance(key, str) and key.lower() in ("1", "2", "3", "s", "q"):
            return key.lower()


def main(stdscr):
    setup_colours()
    levels = list(TEXTS)

    while True:
        choice = show_menu(stdscr)
        if choice == "q":
            return
        if choice == "s":
            show_scores(stdscr)
            continue

        level = levels[int(choice) - 1]
        test = play_round(stdscr, level)
        if test is not None:
            show_results(stdscr, test, level)


if __name__ == "__main__":
    curses.set_escdelay(25)  # Make the Esc key respond straight away.
    curses.wrapper(main)
