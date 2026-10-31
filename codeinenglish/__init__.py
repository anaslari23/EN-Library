from __future__ import annotations

import sys

if sys.version_info < (3, 9):  # shown instead of an obscure syntax error on very old Pythons
    raise SystemExit("EN needs Python 3.9 or newer. Install one from https://www.python.org/downloads/ and run this again.")
from .errors import CodeInEnglishError
from .translator import translate, translate_file
from .problem_solver import solve, solve_file
from .interpreter import generate_file
from .contract import Diagnostic, ENSourceError, SourceContract, SourceLine, read_contract

from .autogen import generate_from_comments, _on_import

__version__ = "0.3.0"

__all__ = [
    "CodeInEnglishError", "Diagnostic", "ENSourceError", "SourceContract", "SourceLine",
    "translate", "translate_file", "solve", "solve_file", "generate_file", "read_contract", "generate_from_comments", "__version__",
]

_on_import()
