class CodeInEnglishError(Exception):
    """A syntax error in a Code in English source file."""

    def __init__(self, filename: str, line: int, message: str, kind: str = "syntax", column: int = 1):
        self.filename = filename
        self.line = line
        self.message = message
        self.kind = kind
        self.column = column
        super().__init__(f"{filename}:{line}: {message}")
