import json
import unittest

from codeinenglish.interpreter import interpret_source
from codeinenglish.problem_solver import render_problem_python

from tests.test_recipes import CASES, MIGRATED


def result(request, given):
    spec = interpret_source("target python\n# " + request + "\n")
    scope = {"__name__": "generated"}
    exec(compile(render_problem_python(spec), "<generated>", "exec"), scope)
    return json.loads(json.dumps(scope[spec.function_name](**given)))


class MetamorphicTests(unittest.TestCase):
    def test_polite_wrapping_does_not_change_the_answer(self):
        for key, (request, given, expected) in {**CASES, **MIGRATED}.items():
            with self.subTest(key):
                self.assertEqual(result("Please " + request[0].lower() + request[1:].rstrip(".") + ", thanks.", given), result(request, given))

    def test_an_added_condition_is_refused_never_dropped(self):
        for key, (request, given, expected) in {**CASES, **MIGRATED}.items():
            with self.subTest(key), self.assertRaises(Exception):
                result(request.rstrip(".") + " but only for values greater than 3.", given)

    def test_an_extra_clause_is_refused_never_dropped(self):
        for key, (request, given, expected) in {**CASES, **MIGRATED}.items():
            with self.subTest(key), self.assertRaises(Exception):
                result(request.rstrip(".") + " and then email the result to my boss.", given)


if __name__ == "__main__":
    unittest.main()
