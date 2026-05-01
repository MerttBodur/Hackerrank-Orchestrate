import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from corpus import load_corpus


class CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chunks = load_corpus()

    def test_load_corpus_returns_chunks(self):
        self.assertGreater(len(self.chunks), 0)

    def test_chunk_has_required_fields(self):
        chunk = self.chunks[0]
        self.assertIn(chunk.source, ("claude", "hackerrank", "visa"))
        self.assertTrue(chunk.title)
        self.assertTrue(chunk.text)

    def test_chunk_source_matches_path(self):
        sources = {chunk.source for chunk in self.chunks}
        self.assertIn("claude", sources)
        self.assertIn("hackerrank", sources)
        self.assertIn("visa", sources)


if __name__ == "__main__":
    unittest.main()
