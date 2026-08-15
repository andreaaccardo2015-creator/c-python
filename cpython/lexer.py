from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import LexerError


class TokenType(Enum):
    # Literals / identifiers
    IDENT = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    HEX = auto()

    # Keywords
    IMPORT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    FUN = auto()
    CLASS = auto()
    ACTOR = auto()
    ON = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    THIS = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

    # Type keywords (also usable as identifiers in some contexts via IDENT)
    TYPE = auto()  # int, float, string, bool, list, dict

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    EQ = auto()
    EQEQ = auto()
    PLUSEQ = auto()  # +=
    MINUSEQ = auto()  # -=
    STAREQ = auto()  # *=
    SLASHEQ = auto()  # /=
    NE = auto()
    LT = auto()
    GT = auto()
    LE = auto()
    GE = auto()
    ARROW = auto()  # ->

    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACK = auto()
    RBRACK = auto()
    LBRACE = auto()
    RBRACE = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    SEMICOLON = auto()

    # Indentation
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()


KEYWORDS = {
    "import": TokenType.IMPORT,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "fun": TokenType.FUN,
    "class": TokenType.CLASS,
    "actor": TokenType.ACTOR,
    "on": TokenType.ON,
    "return": TokenType.RETURN,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "this": TokenType.THIS,
    "and": TokenType.AND,
    "or": TokenType.OR,
    "not": TokenType.NOT,
}

TYPES = {"int", "float", "string", "bool", "list", "dict"}


@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    column: int


class Lexer:
    def __init__(self, source: str):
        # Rimuovi BOM UTF-8 se presente (editor Windows)
        if source.startswith("\ufeff"):
            source = source[1:]
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent_stack = [0]
        self.at_line_start = True
        self.paren_depth = 0
        self.brace_depth = 0
        self._pending_tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            tok = self._next_token()
            tokens.append(tok)
            if tok.type == TokenType.EOF:
                break
        return tokens

    def _peek(self, n: int = 0) -> str:
        i = self.pos + n
        if i >= len(self.source):
            return ""
        return self.source[i]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_spaces_and_comments(self) -> None:
        while True:
            ch = self._peek()
            if ch == " " or ch == "\t":
                self._advance()
            elif ch == "/" and self._peek(1) == "/":
                while self._peek() and self._peek() != "\n":
                    self._advance()
            else:
                break

    def _emit_indent_dedents(self) -> list[Token] | None:
        """Handle indentation at start of a non-empty line. Returns tokens or None if blank/comment line."""
        start_col = self.column
        spaces = 0
        while self._peek() in (" ", "\t"):
            ch = self._advance()
            spaces += 4 if ch == "\t" else 1

        # Blank line
        if self._peek() == "\n" or self._peek() == "":
            return []

        # Comment-only line
        if self._peek() == "/" and self._peek(1) == "/":
            while self._peek() and self._peek() != "\n":
                self._advance()
            return []

        tokens: list[Token] = []
        current = self.indent_stack[-1]
        if spaces > current:
            self.indent_stack.append(spaces)
            tokens.append(Token(TokenType.INDENT, spaces, self.line, start_col))
        elif spaces < current:
            while self.indent_stack and spaces < self.indent_stack[-1]:
                self.indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, spaces, self.line, start_col))
            if self.indent_stack[-1] != spaces:
                raise LexerError(
                    f"Indentazione non allineata (attesi {self.indent_stack[-1]} spazi, trovati {spaces})",
                    self.line,
                    start_col,
                )
        self.at_line_start = False
        return tokens

    def _next_token(self) -> Token:
        if self._pending_tokens:
            return self._pending_tokens.pop(0)

        if self.at_line_start and self.paren_depth == 0 and self.brace_depth == 0:
            indents = self._emit_indent_dedents()
            if indents is None:
                pass
            elif indents:
                self._pending_tokens.extend(indents[1:])
                return indents[0]
            # blank/comment: fall through to handle newline

        self._skip_spaces_and_comments()

        if self.pos >= len(self.source):
            # Emit remaining dedents
            while len(self.indent_stack) > 1:
                self.indent_stack.pop()
                self._pending_tokens.append(Token(TokenType.DEDENT, 0, self.line, self.column))
            if self._pending_tokens:
                return self._pending_tokens.pop(0)
            return Token(TokenType.EOF, None, self.line, self.column)

        ch = self._peek()
        line, col = self.line, self.column

        if ch == "\n":
            self._advance()
            if self.paren_depth == 0 and self.brace_depth == 0:
                self.at_line_start = True
                return Token(TokenType.NEWLINE, "\n", line, col)
            # Inside () or {}: newlines are separators, keep scanning
            self.at_line_start = True
            return self._next_token()

        # Token di contenuto sulla riga corrente (es. '} else {'):
        # non siamo piu' a inizio riga — evita INDENT spurio dopo '}'.
        self.at_line_start = False

        # String
        if ch in ('"', "'"):
            return self._read_string()

        # Hex color #RRGGBB / #RGB
        if ch == "#":
            return self._read_hex_color()

        # Number
        if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
            return self._read_number()

        # Identifier / keyword
        if ch.isalpha() or ch == "_":
            return self._read_ident()

        # Two-char operators
        two = ch + self._peek(1)
        if two == "==":
            self._advance()
            self._advance()
            return Token(TokenType.EQEQ, "==", line, col)
        if two == "!=":
            self._advance()
            self._advance()
            return Token(TokenType.NE, "!=", line, col)
        if two == "<=":
            self._advance()
            self._advance()
            return Token(TokenType.LE, "<=", line, col)
        if two == ">=":
            self._advance()
            self._advance()
            return Token(TokenType.GE, ">=", line, col)
        if two == "->":
            self._advance()
            self._advance()
            return Token(TokenType.ARROW, "->", line, col)
        composti = {
            "+=": TokenType.PLUSEQ,
            "-=": TokenType.MINUSEQ,
            "*=": TokenType.STAREQ,
            "/=": TokenType.SLASHEQ,
        }
        if two in composti:
            self._advance()
            self._advance()
            return Token(composti[two], two, line, col)

        # Single-char
        single = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "%": TokenType.PERCENT,
            "=": TokenType.EQ,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACK,
            "]": TokenType.RBRACK,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            ",": TokenType.COMMA,
            ".": TokenType.DOT,
            ":": TokenType.COLON,
            ";": TokenType.SEMICOLON,
        }
        if ch in single:
            self._advance()
            tt = single[ch]
            if tt == TokenType.LPAREN:
                self.paren_depth += 1
            elif tt == TokenType.RPAREN:
                self.paren_depth = max(0, self.paren_depth - 1)
            elif tt == TokenType.LBRACK:
                self.paren_depth += 1
            elif tt == TokenType.RBRACK:
                self.paren_depth = max(0, self.paren_depth - 1)
            elif tt == TokenType.LBRACE:
                self.brace_depth += 1
            elif tt == TokenType.RBRACE:
                self.brace_depth = max(0, self.brace_depth - 1)
            return Token(tt, ch, line, col)

        raise LexerError(f"Carattere non valido: {ch!r}", line, col)

    def _read_hex_color(self) -> Token:
        line, col = self.line, self.column
        self._advance()  # #
        start = self.pos
        while self._peek() and self._peek() in "0123456789abcdefABCDEF":
            self._advance()
        raw = self.source[start : self.pos]
        if len(raw) not in (3, 6):
            raise LexerError(f"Colore hex non valido: #{raw}", line, col)
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        return Token(TokenType.HEX, int(raw, 16), line, col)

    def _read_string(self) -> Token:
        quote = self._advance()
        line, col = self.line, self.column - 1
        chars: list[str] = []
        while True:
            ch = self._peek()
            if ch == "":
                raise LexerError("Stringa non terminata", line, col)
            if ch == "\n":
                raise LexerError("Stringa non terminata (newline)", line, col)
            if ch == "\\":
                self._advance()
                esc = self._advance()
                mapping = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'"}
                chars.append(mapping.get(esc, esc))
                continue
            if ch == quote:
                self._advance()
                break
            chars.append(self._advance())
        return Token(TokenType.STRING, "".join(chars), line, col)

    def _read_number(self) -> Token:
        line, col = self.line, self.column
        start = self.pos
        is_float = False
        while self._peek().isdigit():
            self._advance()
        if self._peek() == "." and self._peek(1).isdigit():
            is_float = True
            self._advance()
            while self._peek().isdigit():
                self._advance()
        raw = self.source[start : self.pos]
        # Suffisso float: 2.5f, 90f. Non lo consumiamo se attaccato a un nome
        # (2fps sarebbe un altro token), cosi' "2.5f" resta un numero solo.
        if self._peek() in ("f", "F") and not (self._peek(1).isalnum() or self._peek(1) == "_"):
            self._advance()
            return Token(TokenType.FLOAT, float(raw), line, col)
        if is_float:
            return Token(TokenType.FLOAT, float(raw), line, col)
        return Token(TokenType.INT, int(raw), line, col)

    def _read_ident(self) -> Token:
        line, col = self.line, self.column
        start = self.pos
        while self._peek().isalnum() or self._peek() == "_":
            self._advance()
        text = self.source[start : self.pos]
        # Linguaggio case-insensitive: keyword, tipi e identificatori in minuscolo
        low = text.lower()
        if low in KEYWORDS:
            return Token(KEYWORDS[low], low, line, col)
        if low in TYPES:
            return Token(TokenType.TYPE, low, line, col)
        return Token(TokenType.IDENT, low, line, col)
