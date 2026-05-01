import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from retriever import retrieve
from schemas import Chunk


CHUNKS = [
    Chunk(
        source="hackerrank",
        file="a.md",
        title="Test expiration settings",
        text="Tests in HackerRank remain active indefinitely unless a start and end time is set.",
    ),
    Chunk(
        source="claude",
        file="b.md",
        title="Delete account",
        text="To delete your Claude account go to settings and click delete.",
    ),
    Chunk(
        source="visa",
        file="c.md",
        title="Lost card",
        text="Call Visa to report a lost or stolen card immediately.",
    ),
]


class RetrieverTests(unittest.TestCase):
    def test_retrieve_returns_most_relevant(self):
        results = retrieve("how long does a test stay active", CHUNKS, top_k=1)
        self.assertEqual(results[0].source, "hackerrank")

    def test_retrieve_respects_top_k(self):
        results = retrieve("account delete test card", CHUNKS, top_k=2)
        self.assertEqual(len(results), 2)

    def test_retrieve_empty_query_returns_empty(self):
        self.assertEqual(retrieve("", CHUNKS, top_k=3), [])


if __name__ == "__main__":
    unittest.main()
