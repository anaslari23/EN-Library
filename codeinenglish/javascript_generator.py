"""Small, explicit JavaScript backend for the shared EN semantic forms."""

import json

from .errors import CodeInEnglishError
from .ir import Assign, Display, Literal, Name, Program
from .problem_recognizer import ProblemFamily, ProblemSpec


def _expression(node, filename: str) -> str:
    if isinstance(node, Literal):
        if isinstance(node.value, float) or (type(node.value) is int and abs(node.value) > 2**53 - 1):
            raise CodeInEnglishError(filename, 1, "JavaScript currently supports only exact integer, text, boolean, and null literals", kind="unsupported")
        return json.dumps(node.value, ensure_ascii=False)
    if isinstance(node, Name):
        return f"en_{node.identifier}"
    raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {type(node).__name__} expressions", kind="unsupported")


def generate_javascript(program: Program | ProblemSpec, filename: str) -> str:
    if isinstance(program, ProblemSpec):
        return _problem_javascript(program, filename)
    lines = ['"use strict";',
             "function enString(value) {",
             "  return value === null ? 'None' : value === true ? 'True' : value === false ? 'False' : String(value);",
             "}"]
    declared = set()
    for statement in program.statements:
        if isinstance(statement, Assign):
            prefix = "" if statement.name in declared else "let "
            lines.append(f"{prefix}en_{statement.name} = {_expression(statement.value, filename)};")
            declared.add(statement.name)
        elif isinstance(statement, Display):
            values = [_expression(value, filename) for value in statement.values]
            if not values:
                raise CodeInEnglishError(filename, 1, "JavaScript display needs a value", kind="unsupported")
            lines.append(f"console.log({' + '.join(f'enString({value})' for value in values)});")
        else:
            raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {type(statement).__name__} instructions", kind="unsupported")
    return "\n".join(lines) + "\n"


def _problem_javascript(spec: ProblemSpec, filename: str) -> str:
    if spec.family != ProblemFamily.SORT_ASCENDING:
        raise CodeInEnglishError(filename, 1, f"JavaScript does not yet support {spec.family.value} problems", kind="unsupported")
    for example in spec.examples:
        if any(abs(value) > 2**53 - 1 for value in example.input["nums"]):
            raise CodeInEnglishError(filename, example.source_line, "JavaScript sort examples need integers within the exact Number range", kind="unsupported")
    examples = json.dumps([{"input": item.input, "expected": item.expected} for item in spec.examples], ensure_ascii=False)
    return "\n".join((
        '"use strict";',
        "const fs = require('node:fs');",
        "function sort_ascending(nums) {",
        "  return [...nums].sort((a, b) => a - b);",
        "}",
        f"const examples = {examples};",
        "if (process.argv.includes('--check-examples')) {",
        "  for (const [index, example] of examples.entries()) {",
        "    const actual = sort_ascending(example.input.nums);",
        "    if (JSON.stringify(actual) !== JSON.stringify(example.expected)) {",
        "      console.error(`Example ${index + 1} failed: ${JSON.stringify(actual)}`);",
        "      process.exit(1);",
        "    }",
        "  }",
        "  console.log(`All ${examples.length} examples passed.`);",
        "} else {",
        "  const input = JSON.parse(fs.readFileSync(0, 'utf8'));",
        "  if (!Array.isArray(input.nums) || !input.nums.every(Number.isSafeInteger)) {",
        "    throw new Error('input.nums must be a list of exact integers');",
        "  }",
        "  console.log(JSON.stringify(sort_ascending(input.nums)));",
        "}",
        "",
    ))
