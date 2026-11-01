# Typing Speed Test

A game that measures how fast and how accurately you type. You can play it in
your web browser or in the terminal. It uses only the Python standard library,
so there is nothing to install.

## How to run

In your web browser:

```
python3 typing_speed_web.py
```

This opens the game in a new browser tab. Press Ctrl+C in the terminal when you
are done, to stop the server. The server can only be reached from your own
computer.

In the terminal:

```
python3 typing_speed_test.py
```

Both versions need `curses`, which Windows does not include, so on Windows
install it first with `pip install windows-curses`.

## Languages

The browser version has English and Russian. Pick one on the main screen; the
page, the tips and the texts all change, and your choice is remembered. For
Russian, switch your keyboard to the Russian layout. Scores from both languages
share one list. The terminal version is English only.

## How to play

1. Choose a level: Easy, Medium or Hard.
2. Type the text shown. The timer starts on your first key press.
3. Correct characters turn green and mistakes turn red. Press Backspace to fix
   a mistake, or Esc to go back to the menu.
4. When you reach the end of the text you see your results. Scores are saved in
   `scores.json`, and the top five appear under "Best scores". Both versions
   share the same scores.

## One minute mode

In the browser version, choose "1 minute" above the levels (or press M). You
type for 60 seconds from your first key press, and the clock counts down. Scores
go in the same list as full text rounds. The terminal version does not have
this mode.

## Keyboard hint

While you type in the browser version, a keyboard with two hands shows the next
key and the finger that should press it. For capital letters and symbols it
also shows which Shift key to use. In Russian it shows the Russian layout.

## How the score is calculated

- **WPM (words per minute)** = (correct characters / 5) / minutes. A "word" is
  counted as 5 characters, which is the standard for typing tests.
- **Accuracy** = correct key presses / all key presses x 100. A mistake you fix
  with Backspace still lowers your accuracy, but not your WPM.

## Tests

```
python3 -m unittest
```

## Files

- `typing_speed_test.py` - the game logic and the terminal version
- `typing_speed_web.py` - the server for the browser version
- `typing_speed_web.html` - the browser version's page
- `typing_tips.html` - the browser version's "How to type faster" page
- `test_typing_speed_test.py` - tests for the game logic
- `test_typing_speed_web.py` - tests for the server
- `scores.json` - saved scores, created after your first round
