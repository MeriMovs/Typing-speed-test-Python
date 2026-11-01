"""Tests for the browser version's server. Run them with:  python3 -m unittest"""

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

from typing_speed_test import TEXTS, load_scores
from typing_speed_web import GameHandler, HOST, is_valid_score


class ScoreValidationTests(unittest.TestCase):
    def test_good_score_is_accepted(self):
        self.assertTrue(is_valid_score("Easy", 40.5, 95))

    def test_bad_scores_are_rejected(self):
        bad_scores = [
            ("Impossible", 40, 95),
            (["Easy"], 40, 95),
            ("Easy", "40", 95),
            ("Easy", True, 95),
            ("Easy", -1, 95),
            ("Easy", 40, 101),
            ("Easy", float("nan"), 95),
            ("Easy", float("inf"), 95),
        ]
        for level, wpm, accuracy in bad_scores:
            self.assertFalse(is_valid_score(level, wpm, accuracy))


class ServerTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.scores_path = Path(folder.name) / "scores.json"

        handler = type("TestHandler", (GameHandler,),
                       {"scores_path": self.scores_path})
        self.server = ThreadingHTTPServer((HOST, 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def request(self, method, path, body=None, content_type="application/json"):
        connection = HTTPConnection(HOST, self.server.server_port)
        self.addCleanup(connection.close)
        headers = {"Content-Type": content_type} if body is not None else {}
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        return response.status, response.read()

    def post_score(self, level="Easy", wpm=40, accuracy=95):
        body = json.dumps({"level": level, "wpm": wpm, "accuracy": accuracy})
        return self.request("POST", "/api/scores", body)

    def test_page_is_served(self):
        status, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Typing Speed Test", body)

    def test_text_comes_from_the_chosen_level(self):
        status, body = self.request("GET", "/api/text?level=Hard")
        self.assertEqual(status, 200)
        self.assertIn(json.loads(body)["text"], TEXTS["Hard"])

    def test_unknown_level_gives_no_text(self):
        status, _ = self.request("GET", "/api/text?level=Impossible")
        self.assertEqual(status, 400)

    def test_unknown_path_is_not_found(self):
        status, _ = self.request("GET", "/scores.json")
        self.assertEqual(status, 404)

    def test_score_is_saved_and_reported_as_record(self):
        status, body = self.post_score(wpm=40)
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["new_record"])

        _, body = self.post_score(wpm=30)
        self.assertFalse(json.loads(body)["new_record"])
        self.assertEqual(len(load_scores(self.scores_path)), 2)

    def test_scores_come_back_best_first(self):
        self.post_score(wpm=30)
        self.post_score(wpm=50)
        status, body = self.request("GET", "/api/scores")
        self.assertEqual(status, 200)
        self.assertEqual([s["wpm"] for s in json.loads(body)], [50, 30])

    def test_invalid_score_is_not_saved(self):
        status, _ = self.post_score(level="Impossible")
        self.assertEqual(status, 400)
        self.assertEqual(load_scores(self.scores_path), [])

    def test_broken_json_is_rejected(self):
        status, _ = self.request("POST", "/api/scores", "not json")
        self.assertEqual(status, 400)

    def test_score_must_be_sent_as_json(self):
        body = json.dumps({"level": "Easy", "wpm": 40, "accuracy": 95})
        status, _ = self.request("POST", "/api/scores", body, "text/plain")
        self.assertEqual(status, 415)
        self.assertEqual(load_scores(self.scores_path), [])


if __name__ == "__main__":
    unittest.main()
