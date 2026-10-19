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
```

Public API: `CodeInEnglishError`, `translate`, `translate_file`, `solve`, and `solve_file`.

## CLI

```sh
python3 -m codeinenglish translate greeting.en
python3 -m codeinenglish solve problem.en
```

`translate` accepts supported instruction-language statements. `solve` extracts a problem statement from `.en` comments, recognizes supported problem families, and writes a Python solution beside the source file (or to `--output`). Generated Python is syntax-checked, but is never run by the generator. Review it before executing.

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
