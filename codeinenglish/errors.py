class CodeInEnglishError(Exception):
    """A syntax error in a Code in English source file."""

    def __init__(self, filename: str, line: int, message: str, kind: str = "syntax"):
        self.filename = filename
        self.line = line
        self.message = message
        self.kind = kind
        super().__init__(f"{filename}:{line}: {message}")
