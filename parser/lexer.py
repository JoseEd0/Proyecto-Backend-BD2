"""
Tokenizador (Lexer) para el parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


class TokenType(Enum):
    """Tipos de tokens reconocidos por el lexer"""

    # Palabras clave
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    CREATE = auto()
    DROP = auto()
    TABLE = auto()
    INDEX = auto()
    INSERT = auto()
    DELETE = auto()
    INTO = auto()
    VALUES = auto()
    PRIMARY = auto()
    KEY = auto()
    USING = auto()
    FILE = auto()
    BOOLEAN = auto()
    ON = auto()
    TRUE = auto()
    FALSE = auto()
    BETWEEN = auto()
    IN = auto()
    AND = auto()
    OR = auto()
    NOT = auto()

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

    # Palabras clave (todas en MAYÚSCULAS para matching case-insensitive)
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
        "BTREE": TokenType.BTREE,
        "ISAM": TokenType.ISAM,
        "HASH": TokenType.HASH,
        "RTREE": TokenType.RTREE,
        "TRUE": TokenType.TRUE,
        "FALSE": TokenType.FALSE,
        "BOOLEAN": TokenType.BOOLEAN,
        "DROP": TokenType.DROP,
        "PRIMARY": TokenType.PRIMARY,
        "ON": TokenType.ON,
        "OR": TokenType.OR,
        "NOT": TokenType.NOT,
    }

    # Valores canónicos para normalizar el .value de los tokens
    CANONICAL_CASE = {
        "BTREE": "BTree",
        "HASH": "Hash",
        "RTREE": "RTree",
        # El resto se mantiene en mayúsculas (INT, VARCHAR, SEQ, etc.)
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
            # Verificar comentarios PRIMERO (antes de espacios)
            if (
                self.pos < len(self.text) - 1
                and self.text[self.pos : self.pos + 2] == "--"
            ):
                self._skip_whitespace()
                continue

            # Luego verificar espacios
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
        """Salta espacios en blanco y comentarios"""
        while self.pos < len(self.text):
            # Saltar espacios
            if self._current_char().isspace():
                self._advance()
            # Saltar comentarios de línea (-- hasta fin de línea)
            elif (
                self.pos < len(self.text) - 1
                and self.text[self.pos : self.pos + 2] == "--"
            ):
                # Avanzar hasta el final de la línea
                while self.pos < len(self.text) and self.text[self.pos] != "\n":
                    self._advance()
                # Saltar el salto de línea también
                if self.pos < len(self.text) and self.text[self.pos] == "\n":
                    self._advance()
            else:
                break


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

                # Verificar si es palabra clave (case-insensitive)
                if token_type == TokenType.IDENTIFIER:
                    upper_value = value.upper()
                    if upper_value in self.KEYWORDS:
                        token_type = self.KEYWORDS[upper_value]
                        # Normalizar el 'value' a la forma canónica esperada por los Enums
                        value = self.CANONICAL_CASE.get(upper_value, upper_value)

                # Procesar strings
                if token_type == TokenType.STRING:
                    value = value[1:-1]  # Quitar comillas

                return Token(token_type, value, start_line, start_column)

        # Si no coincide con ningún patrón, error
        raise Exception(
            f"Carácter inesperado '{self._current_char()}' en línea {self.line}, columna {self.column}"
        )
        # Si no coincide con ningún patrón, error
        raise Exception(
            f"Carácter inesperado '{self._current_char()}' en línea {self.line}, columna {self.column}"
        )


def tokenize(sql_text: str) -> List[Token]:
    """Función de conveniencia para tokenizar directamente"""
    lexer = SQLLexer()
    return lexer.tokenize(sql_text)
