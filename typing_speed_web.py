"""Typing Speed Test - the same game in your web browser.

Run it with:  python3 typing_speed_web.py

This starts a small server on your own computer and opens the game in your
browser. Texts and scores are shared with the terminal version. Press Ctrl+C
in the terminal to stop the server.
"""

import json
import math
import random
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from typing_speed_test import (
    SCORES_FILE,
    TEXTS,
    load_scores,
    save_score,
    top_scores,
)

PAGE_FILE = Path(__file__).with_name("typing_speed_web.html")
HOST = "127.0.0.1"  # Only this computer can reach the server.
PORT = 8000
MAX_BODY_SIZE = 1024

# Saving reads the file and writes it back, so only one request may do it at
# a time.
scores_lock = threading.Lock()


def is_valid_score(level, wpm, accuracy):
    """Check a score sent by the browser before it goes in the file."""
    if not isinstance(level, str) or level not in TEXTS:
        return False
    for value in (wpm, accuracy):
        if type(value) not in (int, float) or not math.isfinite(value):
            return False
    return wpm >= 0 and 0 <= accuracy <= 100


class GameHandler(BaseHTTPRequestHandler):
    scores_path = SCORES_FILE

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            self.send_body(PAGE_FILE.read_bytes(), "text/html; charset=utf-8")
        elif url.path == "/api/text":
            level = parse_qs(url.query).get("level", [""])[0]
            if level in TEXTS:
                self.send_json({"text": random.choice(TEXTS[level])})
            else:
                self.send_json({"error": "Unknown level"}, 400)
        elif url.path == "/api/scores":
            self.send_json(top_scores(load_scores(self.scores_path)))
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/scores":
            self.send_json({"error": "Not found"}, 404)
            return

        # Browsers will not let other websites send this content type here,
        # so a page you happen to visit cannot add fake scores.
        if self.headers.get_content_type() != "application/json":
            self.send_json({"error": "Expected JSON"}, 415)
            return

        score = self.read_json()
        if not isinstance(score, dict) or not is_valid_score(
                score.get("level"), score.get("wpm"), score.get("accuracy")):
            self.send_json({"error": "Invalid score"}, 400)
            return

        with scores_lock:
            new_record = save_score(score["level"], score["wpm"],
                                    score["accuracy"], self.scores_path)
        self.send_json({"new_record": new_record})

    def read_json(self):
        """Return the request's JSON body, or None if it cannot be read."""
        try:
            size = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None
        if not 0 <= size <= MAX_BODY_SIZE:
            return None
        try:
            return json.loads(self.rfile.read(size))
        except ValueError:
            return None

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_body(body, "application/json", status)

    def send_body(self, body, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Keep the terminal quiet while the game is running."""


def create_server():
    """Use the usual port, or any free one if something else has taken it."""
    try:
        return ThreadingHTTPServer((HOST, PORT), GameHandler)
    except OSError:
        return ThreadingHTTPServer((HOST, 0), GameHandler)


def main():
    server = create_server()
    url = f"http://{HOST}:{server.server_port}/"
    print(f"Typing Speed Test is running at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
