from .errors import CodeInEnglishError
from .translator import translate, translate_file
from .problem_solver import solve, solve_file
from .interpreter import generate_file
from .contract import Diagnostic, ENSourceError, SourceContract, SourceLine, read_contract

from .autogen import generate_from_comments, _on_import

__version__ = "0.2.0"

__all__ = [
    "CodeInEnglishError", "Diagnostic", "ENSourceError", "SourceContract", "SourceLine",
    "translate", "translate_file", "solve", "solve_file", "generate_file", "read_contract", "generate_from_comments", "__version__",
]

_on_import()
