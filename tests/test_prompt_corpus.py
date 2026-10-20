import json
import unittest
from pathlib import Path

from codeinenglish.errors import CodeInEnglishError
from codeinenglish.problem_prompt import ProblemPrompt
from codeinenglish.problem_recognizer import recognize_problem


CORPUS = json.loads((Path(__file__).parent / "fixtures" / "prompt_corpus.json").read_text(encoding="utf-8"))


class PromptCorpusTests(unittest.TestCase):
    def test_accepted_prompts_match_their_intent(self):
        self.assertEqual(len(CORPUS["accepted"]), 24)
        for text, family in CORPUS["accepted"]:
            with self.subTest(text=text):
                spec = recognize_problem(ProblemPrompt(text, (1,)), "corpus.en")
                self.assertEqual(spec.family.value, family)

    def test_unsupported_or_ambiguous_prompts_are_rejected(self):
        self.assertEqual(len(CORPUS["rejected"]), 8)
        for text in CORPUS["rejected"]:
            with self.subTest(text=text):
                with self.assertRaises(CodeInEnglishError) as caught:
                    recognize_problem(ProblemPrompt(text, (1,)), "corpus.en")
                self.assertEqual(caught.exception.filename, "corpus.en")
                self.assertEqual(caught.exception.line, 1)
