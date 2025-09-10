"""
Parser SQL para Mini Gestor de Bases de Datos
Proyecto CS2702 - Base de Datos 2 UTEC

Este módulo proporciona un parser SQL completo que incluye:
- Análisis léxico y sintáctico
- Validación semántica
- Traducción a operaciones del gestor
- Soporte para múltiples técnicas de indexación
"""

from .lexer import SQLLexer, Token, TokenType, tokenize
from .ast_nodes import *
from .sql_parser import SQLParser, parse_sql, ParseError
from .semantic_validator import SemanticValidator, TableSchema
from .query_translator import QueryTranslator, MockDatabaseAdapter
from .sql_engine import SQLParserEngine, create_sql_parser_engine

# Versión del módulo
__version__ = "1.0.0"
__author__ = "CS2702 - Base de Datos 2 UTEC"

# Exports principales
__all__ = [
    "SQLParserEngine",
    "create_sql_parser_engine",
    "SQLParser",
    "parse_sql",
    "SQLLexer",
    "tokenize",
    "SemanticValidator",
    "QueryTranslator",
    "MockDatabaseAdapter",
    "ParsedQuery",
    "CreateTableQuery",
    "CreateTableFromFileQuery",
    "SelectQuery",
    "InsertQuery",
    "DeleteQuery",
    "Column",
    "Condition",
    "DataType",
    "IndexType",
    "OperationType",
    "TableSchema",
    "Token",
    "TokenType",
    "ParseError",
]
