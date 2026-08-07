from __future__ import annotations

from . import ast_nodes as ast
from .errors import ParseError
from .lexer import Lexer, Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    @classmethod
    def parse_source(cls, source: str) -> ast.Program:
        tokens = Lexer(source).tokenize()
        return cls(tokens).parse()

    def parse(self) -> ast.Program:
        body: list[ast.Node] = []
        self._skip_newlines()
        while not self._check(TokenType.EOF):
            body.append(self._statement())
            self._skip_newlines()
        return ast.Program(body=body, line=1, column=1)

    # ---- helpers ----
    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _check(self, *types: TokenType) -> bool:
        return self._cur().type in types

    def _advance(self) -> Token:
        tok = self._cur()
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _match(self, *types: TokenType) -> Token | None:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, typ: TokenType, msg: str) -> Token:
        if self._check(typ):
            return self._advance()
        cur = self._cur()
        raise ParseError(msg, cur.line, cur.column)

    def _skip_newlines(self) -> None:
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _at_block_end(self) -> bool:
        return self._check(TokenType.DEDENT, TokenType.EOF, TokenType.ELSE)

    # ---- statements ----
    def _statement(self) -> ast.Node:
        if self._check(TokenType.IMPORT):
            return self._import_stmt()
        if self._check(TokenType.IF):
            return self._if_stmt()
        if self._check(TokenType.WHILE):
            return self._while_stmt()
        if self._check(TokenType.FOR):
            return self._for_stmt()
        if self._check(TokenType.FUN):
            return self._fun_def()
        if self._check(TokenType.ACTOR):
            return self._actor_decl()
        if self._check(TokenType.ON):
            return self._on_handler()
        if self._check(TokenType.CLASS):
            return self._class_def()
        if self._check(TokenType.RETURN):
            return self._return_stmt()
        if self._check(TokenType.BREAK):
            tok = self._advance()
            node = ast.Break(line=tok.line, column=tok.column)
            self._match(TokenType.SEMICOLON)
            return node
        if self._check(TokenType.CONTINUE):
            tok = self._advance()
            node = ast.Continue(line=tok.line, column=tok.column)
            self._match(TokenType.SEMICOLON)
            return node
        if self._check(TokenType.TYPE):
            return self._var_decl()
        return self._assign_or_expr()

    def _import_stmt(self) -> ast.Import:
        tok = self._advance()  # import
        name_tok = self._expect(TokenType.IDENT, "Atteso nome modulo dopo import")
        name = str(name_tok.value)
        # allow dotted: import finityengine (single) or import a.b — only single for now, but accept dots
        while self._match(TokenType.DOT):
            part = self._expect(TokenType.IDENT, "Atteso nome dopo '.'")
            name += "." + str(part.value)
        return ast.Import(name=name, line=tok.line, column=tok.column)

    def _indent_block(self) -> list[ast.Node]:
        self._skip_newlines()
        self._expect(TokenType.INDENT, "Atteso blocco indentato")
        body: list[ast.Node] = []
        self._skip_newlines()
        while not self._check(TokenType.DEDENT, TokenType.EOF):
            body.append(self._statement())
            self._skip_newlines()
        self._expect(TokenType.DEDENT, "Atteso fine blocco (dedent)")
        return body

    def _brace_block(self) -> list[ast.Node]:
        self._skip_newlines()
        self._expect(TokenType.LBRACE, "Atteso '{' per il blocco")
        body: list[ast.Node] = []
        self._skip_newlines()
        while not self._check(TokenType.RBRACE, TokenType.EOF):
            body.append(self._statement())
            self._skip_newlines()
        self._expect(TokenType.RBRACE, "Atteso '}' di chiusura blocco")
        return body

    def _block(self) -> list[ast.Node]:
        """Blocco indentato oppure tra { }. Accetta anche ':' stile Python."""
        self._skip_newlines()
        self._match(TokenType.COLON)  # opzionale: fun():, if ():, for ():
        self._skip_newlines()
        if self._check(TokenType.LBRACE):
            return self._brace_block()
        return self._indent_block()

    def _if_stmt(self) -> ast.If:
        tok = self._advance()  # if
        self._expect(TokenType.LPAREN, "Atteso '(' dopo if")
        cond = self._expression()
        self._expect(TokenType.RPAREN, "Atteso ')' dopo condizione")
        then_body = self._block()
        else_body: list[ast.Node] = []
        self._skip_newlines()
        if self._match(TokenType.ELSE):
            else_body = self._block()
        return ast.If(condition=cond, then_body=then_body, else_body=else_body, line=tok.line, column=tok.column)

    def _while_stmt(self) -> ast.While:
        tok = self._advance()
        self._expect(TokenType.LPAREN, "Atteso '(' dopo while")
        cond = self._expression()
        self._expect(TokenType.RPAREN, "Atteso ')' dopo condizione")
        body = self._block()
        return ast.While(condition=cond, body=body, line=tok.line, column=tok.column)

    def _for_stmt(self) -> ast.For:
        tok = self._advance()
        self._expect(TokenType.LPAREN, "Atteso '(' dopo for")
        var = self._expect(TokenType.IDENT, "Atteso nome variabile nel for")
        self._expect(TokenType.IN, "Atteso 'in' nel for")
        iterable = self._expression()
        self._expect(TokenType.RPAREN, "Atteso ')' dopo for")
        body = self._block()
        return ast.For(var=str(var.value), iterable=iterable, body=body, line=tok.line, column=tok.column)

    def _fun_def(self) -> ast.FunDef:
        tok = self._advance()  # fun
        name = self._expect(TokenType.IDENT, "Atteso nome funzione")
        self._expect(TokenType.LPAREN, "Atteso '(' dopo nome funzione")
        params: list[tuple[str, str]] = []
        if not self._check(TokenType.RPAREN):
            params.append(self._param())
            while self._match(TokenType.COMMA):
                params.append(self._param())
        self._expect(TokenType.RPAREN, "Atteso ')' dopo parametri")
        # Tipo di ritorno preferito su `return int expr` ( -> tipo ancora accettato)
        return_type = None
        if self._match(TokenType.ARROW):
            rt = self._expect(TokenType.TYPE, "Atteso tipo di ritorno")
            return_type = str(rt.value)
        body = self._block()
        if return_type is None:
            return_type = self._infer_return_type(body)
        return ast.FunDef(
            name=str(name.value),
            params=params,
            return_type=return_type,
            body=body,
            line=tok.line,
            column=tok.column,
        )

    def _infer_return_type(self, body: list[ast.Node]) -> str | None:
        for stmt in body:
            found = self._find_return_type(stmt)
            if found:
                return found
        return None

    def _find_return_type(self, node: ast.Node) -> str | None:
        if isinstance(node, ast.Return) and node.type_name:
            return node.type_name
        if isinstance(node, ast.If):
            for s in node.then_body + node.else_body:
                t = self._find_return_type(s)
                if t:
                    return t
        if isinstance(node, ast.While):
            for s in node.body:
                t = self._find_return_type(s)
                if t:
                    return t
        return None

    def _on_handler(self) -> ast.FunDef:
        """Lifecycle FinityEngine: on start { ... } / on update(float dt) { ... }"""
        tok = self._advance()  # on
        event = self._expect(TokenType.IDENT, "Atteso evento dopo 'on' (start, update, ...)")
        event_name = str(event.value).lower()
        mapping = {
            "start": "OnStart",
            "update": "OnUpdate",
            "collision": "OnCollision",
        }
        if event_name not in mapping:
            raise ParseError(
                f"Evento 'on {event_name}' non supportato (usa start, update, collision)",
                event.line,
                event.column,
            )
        params: list[tuple[str, str]] = []
        if self._match(TokenType.LPAREN):
            if not self._check(TokenType.RPAREN):
                params.append(self._param())
                while self._match(TokenType.COMMA):
                    params.append(self._param())
            self._expect(TokenType.RPAREN, "Atteso ')' dopo parametri di on")
        elif event_name == "update":
            # default: on update { } => OnUpdate(float dt)
            params = [("float", "dt")]
        elif event_name == "collision":
            params = [("any", "other")]

        # Corpo obbligatoriamente tra { }
        self._skip_newlines()
        if not self._check(TokenType.LBRACE):
            raise ParseError("Atteso '{' dopo on start/update (il corpo va tra graffe)", self._cur().line, self._cur().column)
        body = self._brace_block()
        return ast.FunDef(
            name=mapping[event_name],
            params=params,
            return_type=None,
            body=body,
            line=tok.line,
            column=tok.column,
        )

    def _param(self) -> tuple[str, str]:
        if self._check(TokenType.TYPE):
            t = self._advance()
            n = self._expect(TokenType.IDENT, "Atteso nome parametro")
            return (str(t.value), str(n.value))
        # allow untyped: just name
        n = self._expect(TokenType.IDENT, "Atteso parametro")
        return ("any", str(n.value))

    def _class_def(self) -> ast.ClassDef:
        tok = self._advance()  # class
        name = self._expect(TokenType.IDENT, "Atteso nome classe")
        base = None
        if self._match(TokenType.COLON):
            base = self._primary_name_or_attr()
        members = self._block()
        return ast.ClassDef(name=str(name.value), base=base, members=members, line=tok.line, column=tok.column)

    def _primary_name_or_attr(self) -> ast.Node:
        """Parse Name or Name.Attr.Attr for base class."""
        tok = self._cur()
        if self._check(TokenType.IDENT, TokenType.TYPE):
            t = self._advance()
            node: ast.Node = ast.Name(id=str(t.value), line=t.line, column=t.column)
            while self._match(TokenType.DOT):
                attr = self._expect(TokenType.IDENT, "Atteso attributo")
                node = ast.Attribute(object=node, attr=str(attr.value), line=attr.line, column=attr.column)
            return node
        raise ParseError("Atteso nome classe base", tok.line, tok.column)

    def _return_stmt(self) -> ast.Return:
        tok = self._advance()
        if self._check(TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF, TokenType.RBRACE, TokenType.SEMICOLON):
            self._match(TokenType.SEMICOLON)
            return ast.Return(value=None, type_name=None, line=tok.line, column=tok.column)
        type_name = None
        if self._check(TokenType.TYPE):
            type_name = str(self._advance().value)
        if self._check(TokenType.NEWLINE, TokenType.DEDENT, TokenType.EOF, TokenType.RBRACE, TokenType.SEMICOLON):
            self._match(TokenType.SEMICOLON)
            return ast.Return(value=None, type_name=type_name, line=tok.line, column=tok.column)
        value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ast.Return(value=value, type_name=type_name, line=tok.line, column=tok.column)

    def _actor_decl(self) -> ast.ActorDecl:
        tok = self._advance()  # actor
        name = self._expect(TokenType.IDENT, "Atteso nome actor")
        self._match(TokenType.SEMICOLON)
        return ast.ActorDecl(name=str(name.value), line=tok.line, column=tok.column)

    def _var_decl(self) -> ast.VarDecl:
        type_tok = self._advance()
        name = self._expect(TokenType.IDENT, "Atteso nome variabile")
        value = None
        if self._match(TokenType.EQ) or self._match(TokenType.EQEQ):
            value = self._expression()
        self._match(TokenType.SEMICOLON)
        return ast.VarDecl(
            type_name=str(type_tok.value),
            name=str(name.value),
            value=value,
            line=type_tok.line,
            column=type_tok.column,
        )

    def _match_set(self) -> bool:
        if self._check(TokenType.IDENT) and self._cur().value == "set":
            self._advance()
            return True
        return False

    def _assign_or_expr(self) -> ast.Node:
        """Supporta: a = v | a == v | a set v | chiamata/espressione (punto e virgola opzionale)."""
        start = self.pos
        left = self._call()
        if self._match(TokenType.EQ) or self._match(TokenType.EQEQ) or self._match_set():
            value = self._expression()
            self._match(TokenType.SEMICOLON)
            return ast.Assign(target=left, value=value, line=left.line, column=left.column)
        # non è assegnazione: riparti e parse espressione completa
        self.pos = start
        expr = self._expression()
        self._match(TokenType.SEMICOLON)
        return ast.ExprStmt(expr=expr, line=expr.line, column=expr.column)

    # ---- expressions (Pratt / precedence climbing) ----
    def _expression(self) -> ast.Node:
        return self._or()

    def _or(self) -> ast.Node:
        left = self._and()
        while self._match(TokenType.OR):
            op = "or"
            right = self._and()
            left = ast.BinaryOp(op=op, left=left, right=right, line=left.line, column=left.column)
        return left

    def _and(self) -> ast.Node:
        left = self._not()
        while self._match(TokenType.AND):
            right = self._not()
            left = ast.BinaryOp(op="and", left=left, right=right, line=left.line, column=left.column)
        return left

    def _not(self) -> ast.Node:
        if self._match(TokenType.NOT):
            tok = self.tokens[self.pos - 1]
            operand = self._not()
            return ast.UnaryOp(op="not", operand=operand, line=tok.line, column=tok.column)
        return self._comparison()

    def _comparison(self) -> ast.Node:
        left = self._term()
        while self._check(TokenType.EQEQ, TokenType.NE, TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_tok = self._advance()
            right = self._term()
            left = ast.BinaryOp(op=str(op_tok.value), left=left, right=right, line=left.line, column=left.column)
        return left

    def _term(self) -> ast.Node:
        left = self._factor()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right = self._factor()
            left = ast.BinaryOp(op=str(op_tok.value), left=left, right=right, line=left.line, column=left.column)
        return left

    def _factor(self) -> ast.Node:
        left = self._unary()
        while self._check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self._advance()
            right = self._unary()
            left = ast.BinaryOp(op=str(op_tok.value), left=left, right=right, line=left.line, column=left.column)
        return left

    def _unary(self) -> ast.Node:
        if self._check(TokenType.MINUS, TokenType.PLUS):
            op_tok = self._advance()
            operand = self._unary()
            return ast.UnaryOp(op=str(op_tok.value), operand=operand, line=op_tok.line, column=op_tok.column)
        return self._call()

    def _call(self) -> ast.Node:
        node = self._primary()
        while True:
            if self._match(TokenType.LPAREN):
                args = self._arg_list()
                self._expect(TokenType.RPAREN, "Atteso ')' dopo argomenti")
                node = ast.Call(callee=node, args=args, line=node.line, column=node.column)
            elif self._match(TokenType.DOT):
                # permetti anche tipi come attributo: random.int, obj.float, ...
                if self._check(TokenType.IDENT, TokenType.TYPE):
                    attr = self._advance()
                else:
                    raise ParseError("Atteso nome attributo", self._cur().line, self._cur().column)
                node = ast.Attribute(object=node, attr=str(attr.value), line=attr.line, column=attr.column)
            elif self._match(TokenType.LBRACK):
                index = self._expression()
                self._expect(TokenType.RBRACK, "Atteso ']'")
                node = ast.Index(object=node, index=index, line=node.line, column=node.column)
            else:
                break
        return node

    def _arg_list(self) -> list[ast.Node]:
        args: list[ast.Node] = []
        if self._check(TokenType.RPAREN):
            return args
        args.append(self._expression())
        while self._match(TokenType.COMMA):
            args.append(self._expression())
        return args

    def _position_literal(self) -> ast.PositionLiteral:
        tok = self._advance()  # x
        x = self._term()
        self._expect(TokenType.SEMICOLON, "Atteso ';' tra x e y (es. x 0; y 0)")
        y_tok = self._expect(TokenType.IDENT, "Atteso 'y' nella position")
        if str(y_tok.value) != "y":
            raise ParseError("Atteso 'y' nella position (es. x 0; y 0)", y_tok.line, y_tok.column)
        y = self._term()
        return ast.PositionLiteral(x=x, y=y, line=tok.line, column=tok.column)

    def _is_position_start(self) -> bool:
        if not (self._check(TokenType.IDENT) and self._cur().value == "x"):
            return False
        if self.pos + 1 >= len(self.tokens):
            return False
        nxt = self.tokens[self.pos + 1]
        if nxt.type in (TokenType.INT, TokenType.FLOAT, TokenType.LPAREN):
            return True
        # x -1; y 0  (meno seguito da numero)
        if (
            nxt.type == TokenType.MINUS
            and self.pos + 2 < len(self.tokens)
            and self.tokens[self.pos + 2].type in (TokenType.INT, TokenType.FLOAT)
        ):
            return True
        return False

    def _primary(self) -> ast.Node:
        tok = self._cur()
        if self._match(TokenType.TRUE):
            return ast.Literal(value=True, line=tok.line, column=tok.column)
        if self._match(TokenType.FALSE):
            return ast.Literal(value=False, line=tok.line, column=tok.column)
        if self._match(TokenType.NULL):
            return ast.Literal(value=None, line=tok.line, column=tok.column)
        if self._match(TokenType.INT):
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if self._match(TokenType.FLOAT):
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if self._match(TokenType.HEX):
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if self._match(TokenType.STRING):
            return ast.Literal(value=tok.value, line=tok.line, column=tok.column)
        if self._match(TokenType.THIS):
            return ast.Name(id="this", line=tok.line, column=tok.column)
        if self._is_position_start():
            return self._position_literal()
        if self._match(TokenType.IDENT):
            return ast.Name(id=str(tok.value), line=tok.line, column=tok.column)
        if self._match(TokenType.TYPE):
            # type name as expression (e.g. rare); treat as name
            return ast.Name(id=str(tok.value), line=tok.line, column=tok.column)
        if self._match(TokenType.LPAREN):
            expr = self._expression()
            self._expect(TokenType.RPAREN, "Atteso ')'")
            return expr
        if self._match(TokenType.LBRACK):
            elements: list[ast.Node] = []
            if not self._check(TokenType.RBRACK):
                elements.append(self._expression())
                while self._match(TokenType.COMMA):
                    elements.append(self._expression())
            self._expect(TokenType.RBRACK, "Atteso ']'")
            return ast.ListLiteral(elements=elements, line=tok.line, column=tok.column)
        if self._match(TokenType.LBRACE):
            pairs: list[tuple[ast.Node, ast.Node]] = []
            if not self._check(TokenType.RBRACE):
                k = self._expression()
                self._expect(TokenType.COLON, "Atteso ':' nel dict")
                v = self._expression()
                pairs.append((k, v))
                while self._match(TokenType.COMMA):
                    k = self._expression()
                    self._expect(TokenType.COLON, "Atteso ':' nel dict")
                    v = self._expression()
                    pairs.append((k, v))
            self._expect(TokenType.RBRACE, "Atteso '}'")
            return ast.DictLiteral(pairs=pairs, line=tok.line, column=tok.column)

        raise ParseError(f"Espressione non valida vicino a {tok.type.name}", tok.line, tok.column)
