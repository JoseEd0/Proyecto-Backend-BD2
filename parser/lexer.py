"""
Tokenizador (Lexer) para el parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    """Tipos de tokens reconocidos por el lexer"""

    # Palabras clave
    CREATE = "CREATE"
    TABLE = "TABLE"
    FROM = "FROM"
    FILE = "FILE"
    USING = "USING"
    INDEX = "INDEX"
    SELECT = "SELECT"
    INSERT = "INSERT"
    INTO = "INTO"
    DELETE = "DELETE"
    WHERE = "WHERE"
    VALUES = "VALUES"
    BETWEEN = "BETWEEN"
    AND = "AND"
    IN = "IN"
    KEY = "KEY"

    # Tipos de datos
    INT = "INT"
    VARCHAR = "VARCHAR"
    DATE = "DATE"
    ARRAY = "ARRAY"
    FLOAT = "FLOAT"

    # Tipos de índices
    SEQ = "SEQ"
    BTREE = "BTree"
    ISAM = "ISAM"
    HASH = "Hash"
    RTREE = "RTree"

    # Operadores
    EQUALS = "="
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_EQUAL = "<="
    GREATER_EQUAL = ">="

    # Símbolos
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    COMMA = ","
    SEMICOLON = ";"
    ASTERISK = "*"

    # Literales
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    EOF = "EOF"


@dataclass
class Token:
    type: TokenType
    value: str
    line: int = 1
    column: int = 1


class SQLLexer:
    """Analizador léxico para consultas SQL del mini gestor"""

    KEYWORDS = {
        "CREATE": TokenType.CREATE,
        "TABLE": TokenType.TABLE,
        "FROM": TokenType.FROM,
        "FILE": TokenType.FILE,
        "USING": TokenType.USING,
        "INDEX": TokenType.INDEX,
        "SELECT": TokenType.SELECT,
        "INSERT": TokenType.INSERT,
        "INTO": TokenType.INTO,
        "DELETE": TokenType.DELETE,
        "WHERE": TokenType.WHERE,
        "VALUES": TokenType.VALUES,
        "BETWEEN": TokenType.BETWEEN,
        "AND": TokenType.AND,
        "IN": TokenType.IN,
        "KEY": TokenType.KEY,
        "INT": TokenType.INT,
        "VARCHAR": TokenType.VARCHAR,
        "DATE": TokenType.DATE,
        "ARRAY": TokenType.ARRAY,
        "FLOAT": TokenType.FLOAT,
        "SEQ": TokenType.SEQ,
        "BTree": TokenType.BTREE,
        "ISAM": TokenType.ISAM,
        "Hash": TokenType.HASH,
        "RTree": TokenType.RTREE,
    }

    def __init__(self):
        self.text = ""
        self.pos = 0
        self.line = 1
        self.column = 1

        # Patrones compilados para mejor rendimiento
        self.patterns = [
            (re.compile(r'"([^"\\]|\\.)*"'), TokenType.STRING),
            (re.compile(r"'([^'\\]|\\.)*'"), TokenType.STRING),
            (re.compile(r"-?\d+\.\d+"), TokenType.NUMBER),
            (re.compile(r"-?\d+"), TokenType.NUMBER),
            (re.compile(r"<="), TokenType.LESS_EQUAL),
            (re.compile(r">="), TokenType.GREATER_EQUAL),
            (re.compile(r"<"), TokenType.LESS_THAN),
            (re.compile(r">"), TokenType.GREATER_THAN),
            (re.compile(r"="), TokenType.EQUALS),
            (re.compile(r"\("), TokenType.LPAREN),
            (re.compile(r"\)"), TokenType.RPAREN),
            (re.compile(r"\["), TokenType.LBRACKET),
            (re.compile(r"\]"), TokenType.RBRACKET),
            (re.compile(r","), TokenType.COMMA),
            (re.compile(r";"), TokenType.SEMICOLON),
            (re.compile(r"\*"), TokenType.ASTERISK),
            (re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*"), TokenType.IDENTIFIER),
        ]

    def tokenize(self, text: str) -> List[Token]:
        """Tokeniza el texto SQL y retorna lista de tokens"""
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1
        tokens = []

        while self.pos < len(self.text):
            if self._current_char().isspace():
                self._skip_whitespace()
                continue

            token = self._next_token()
            if token:
                tokens.append(token)

        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return tokens

    def _current_char(self) -> str:
        """Retorna el carácter actual"""
        if self.pos >= len(self.text):
            return "\0"
        return self.text[self.pos]

    def _advance(self):
        """Avanza al siguiente carácter"""
        if self.pos < len(self.text):
            if self.text[self.pos] == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def _skip_whitespace(self):
        """Salta espacios en blanco"""
        while self.pos < len(self.text) and self._current_char().isspace():
            self._advance()

    def _next_token(self) -> Optional[Token]:
        """Obtiene el siguiente token"""
        start_line = self.line
        start_column = self.column

        # Intentar cada patrón
        for pattern, token_type in self.patterns:
            match = pattern.match(self.text, self.pos)
            if match:
                value = match.group(0)

                # Avanzar posición
                for _ in range(len(value)):
                    self._advance()

                # Verificar si es palabra clave
                if token_type == TokenType.IDENTIFIER:
                    upper_value = value.upper()
                    if upper_value in self.KEYWORDS:
                        token_type = self.KEYWORDS[upper_value]

                # Procesar strings
                if token_type == TokenType.STRING:
                    value = value[1:-1]  # Quitar comillas

                return Token(token_type, value, start_line, start_column)

        # Si no coincide con ningún patrón, error
        raise Exception(
            f"Carácter inesperado '{self._current_char()}' en línea {self.line}, columna {self.column}"
        )


def tokenize(sql_text: str) -> List[Token]:
    """Función de conveniencia para tokenizar directamente"""
    lexer = SQLLexer()
    return lexer.tokenize(sql_text)
