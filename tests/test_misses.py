import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from codeinenglish import solve
from codeinenglish.__main__ import main
from codeinenglish.misses import ENV_VAR


class MissLogTests(unittest.TestCase):
    def test_unmatched_requests_are_logged_and_summarized_only_when_enabled(self):
        request = "import codeinpython library\n# Compose a symphony from a list of numbers.\n"
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "misses.jsonl"
            with patch.dict(os.environ, {ENV_VAR: str(log)}):
                for _ in range(2):
                    with self.assertRaises(Exception):
                        solve(request)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main(["misses"]), 0)
            self.assertRegex(out.getvalue(), r"^2\tunsupported\tCompose a symphony")
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop(ENV_VAR, None)
                with self.assertRaises(Exception):
                    solve(request)
            self.assertEqual(len(log.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
