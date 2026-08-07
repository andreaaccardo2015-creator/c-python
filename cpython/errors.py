class CPythonError(Exception):
    """Errore base del linguaggio C Python."""

    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        self.message = message
        self.line = line
        self.column = column
        loc = ""
        if line is not None:
            loc = f" (riga {line}"
            if column is not None:
                loc += f", colonna {column}"
            loc += ")"
        super().__init__(f"{message}{loc}")


class LexerError(CPythonError):
    pass


class ParseError(CPythonError):
    pass


class RuntimeError_(CPythonError):
    """Runtime error (nome distinto da RuntimeError built-in)."""
    pass
