# Code in English Python Library

`codeinenglish` is the offline Python implementation for Code in English. It translates documented English-like instructions and a growing set of DSA problem descriptions in `.en` files into editable Python. It uses deterministic rules and Python's standard library; it does not download models, contact a service, or execute generated programs.

## Install from this repository

```sh
python3 -m pip install git+https://github.com/anaslari23/EN-Library.git
```

For a local checkout, run `python3 -m pip install .` from the checkout. Then use the library from Python:

```python
import codeinenglish

source = codeinenglish.translate('show "Hello"')
output_path = codeinenglish.solve_file("problem.en")
output_path = codeinenglish.generate_file("program.en")
```

`generate_file` selects the comment-based problem solver when the source contains the exact `import codeinpython library` directive; other `.en` sources go through the instruction translator. It writes a sibling `.py` file by default and never executes it.

Public API: `CodeInEnglishError`, `translate`, `translate_file`, `solve`, `solve_file`, and `generate_file`.

## CLI

```sh
python3 -m codeinenglish translate greeting.en
python3 -m codeinenglish solve problem.en
python3 -m codeinenglish generate any_program.en
```

`generate` is the normal one-command workflow: it selects the problem solver when the exact library directive is present and otherwise translates supported instruction-language statements. `translate` and `solve` remain available for explicit use. All commands write Python beside the source file (or to `--output`); generated code is syntax-checked and never run by the generator. Review it before executing.

A problem file can look like:

```text
import codeinpython library
# Find two numbers that add up to the target.
# Return their indices. Exactly one solution exists.
```

The offline recognizer currently covers common array/string families including two-sum indices, duplicates, frequencies, palindrome/anagram checks, binary search, extrema/sum, first unique character, reverse text, moving zeros, merging sorted lists, maximum subarray sum, and balanced delimiters. Supported wording and assumptions are documented in the language repository. This is deterministic rule-based recognition, not unrestricted English understanding; unsupported or ambiguous prompts produce diagnostics rather than guessed code.

## Development

The distribution has no runtime dependencies and supports Python 3.10+. Run its self-contained tests with:

```sh
python3 -m unittest discover -s tests -v
```

Test fixtures live in `tests/fixtures/`; the package suite does not need the separate language repository.
