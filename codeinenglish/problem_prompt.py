from dataclasses import dataclass
import json
import re

from .errors import CodeInEnglishError

LIBRARY_DIRECTIVE = "import codeinpython library"


@dataclass(frozen=True)
class ProblemPrompt:
    text: str
    source_lines: tuple[int, ...]
    examples: tuple["ProblemExample", ...] = ()


@dataclass(frozen=True)
class ProblemExample:
    input: dict[str, object]
    expected: object
    source_line: int


def has_problem_directive(source: str) -> bool:
    """Return whether the source contains the exact Code in English problem directive."""
    return any(line.strip() == LIBRARY_DIRECTIVE for line in source.splitlines())


def extract_problem_prompt(source: str, filename: str = "<string>") -> ProblemPrompt:
    """Extract a problem statement from comment lines in an ``.en`` file."""
    lines: list[tuple[str, int]] = []
    directive_seen = False
    empty_prompt_line = 1
    for line_number, original in enumerate(source.splitlines(), start=1):
        stripped = original.strip()
        if not stripped:
            continue
        if stripped == LIBRARY_DIRECTIVE:
            if directive_seen:
                raise CodeInEnglishError(filename, line_number, "library directive may appear only once")
            directive_seen = True
            continue
        if stripped.startswith("#"):
            text = stripped[1:]
            if not lines:
                empty_prompt_line = line_number
            if text.startswith(" "):
                text = text[1:]
            lines.append((text.rstrip(), line_number))
            continue
        raise CodeInEnglishError(
            filename,
            line_number,
            "problem files may contain only the library directive and comment lines",
            kind="unsupported",
        )

    return extract_problem_prompt_lines(lines, filename, empty_prompt_line)


def extract_problem_prompt_lines(lines: list[tuple[str, int]] | tuple[tuple[str, int], ...],
                                 filename: str = "<string>", empty_prompt_line: int = 1) -> ProblemPrompt:
    """Parse already-extracted request lines while retaining original line numbers."""
    lines = list(lines)
    examples: list[ProblemExample] = []
    natural_lines: list[tuple[str, int]] = []
    index = 0
    while index < len(lines):
        text, line = lines[index]
        input_match = re.fullmatch(r"Example input:\s*(.*)", text, flags=re.IGNORECASE)
        output_match = re.fullmatch(r"Example output:\s*(.*)", text, flags=re.IGNORECASE)
        if input_match:
            if index + 1 >= len(lines):
                raise CodeInEnglishError(filename, line, "each example input must be followed by an example output")
            following, _ = lines[index + 1]
            output_match = re.fullmatch(r"Example output:\s*(.*)", following, flags=re.IGNORECASE)
            if not output_match:
                raise CodeInEnglishError(filename, lines[index + 1][1], "expected an example output immediately after example input")
            try:
                example_input = json.loads(input_match.group(1))
                expected = json.loads(output_match.group(1))
            except json.JSONDecodeError as error:
                raise CodeInEnglishError(filename, line if error.doc == input_match.group(1) else lines[index + 1][1], "example data must use valid JSON") from error
            if not isinstance(example_input, dict) or not all(isinstance(key, str) for key in example_input):
                raise CodeInEnglishError(filename, line, "example input must be a JSON object with string keys")
            examples.append(ProblemExample(example_input, expected, line))
            index += 2
            continue
        if output_match:
            raise CodeInEnglishError(filename, line, "example output has no preceding example input")
        natural_lines.append((text, line))
        index += 1

    lines = natural_lines
    while lines and not lines[0][0]:
        lines.pop(0)
    while lines and not lines[-1][0]:
        lines.pop()
    if not lines:
        raise CodeInEnglishError(filename, empty_prompt_line, "add the problem statement as one or more # comment lines")
    return ProblemPrompt(
        text="\n".join(text for text, _ in lines),
        source_lines=tuple(line for _, line in lines),
        examples=tuple(examples),
    )
