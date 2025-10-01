"""
Parser principal para consultas SQL del mini gestor
Proyecto CS2702 - Base de Datos 2 UTEC
"""

from typing import List, Optional, Any
from .lexer import SQLLexer, Token, TokenType
from .ast_nodes import *


class ParseError(Exception):
    """Excepción para errores de parsing"""

    def __init__(self, message: str, token: Optional[Token] = None):
        self.message = message
        self.token = token
        super().__init__(message)


class SQLParser:
    """Parser principal para consultas SQL del mini gestor"""

    def __init__(self):
        self.tokens: List[Token] = []
        self.current = 0
        self.lexer = SQLLexer()

    def parse(self, sql_text: str) -> ParsedQuery:
        """Parsea el texto SQL completo"""
        self.tokens = self.lexer.tokenize(sql_text)
        self.current = 0
        return self._parse_statement()

    def _parse_statement(self) -> ParsedQuery:
        """Parse de una declaración SQL"""
        if self._match(TokenType.CREATE):
            return self._parse_create()
        elif self._match(TokenType.SELECT):
            return self._parse_select()
        elif self._match(TokenType.INSERT):
            return self._parse_insert()
        elif self._match(TokenType.DELETE):
            return self._parse_delete()
        else:
            raise ParseError(f"Declaración SQL inesperada: {self._peek().value}")

    def _parse_create(self):
        """Parse de declaraciones CREATE"""
        self._consume(TokenType.TABLE, "Se esperaba 'TABLE' después de 'CREATE'")
        table_name = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de tabla").value

        if self._match(TokenType.FROM):
            return self._parse_create_from_file(table_name)
        else:
            return self._parse_create_table(table_name)

    def _parse_create_table(self, table_name: str) -> CreateTableQuery:
        """Parse de CREATE TABLE normal"""
        self._consume(TokenType.LPAREN, "Se esperaba '(' después del nombre de tabla")

        columns = []
        while not self._check(TokenType.RPAREN):
            columns.append(self._parse_column())
            if not self._check(TokenType.RPAREN):
                self._consume(TokenType.COMMA, "Se esperaba ',' entre columnas")

        self._consume(TokenType.RPAREN, "Se esperaba ')' después de las columnas")
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final de la declaración")

        return CreateTableQuery(OperationType.CREATE_TABLE, table_name, columns)

    def _parse_create_from_file(self, table_name: str) -> CreateTableFromFileQuery:
        """Parse de CREATE TABLE FROM FILE"""
        self._consume(TokenType.FILE, "Se esperaba 'FILE' después de 'FROM'")
        file_path = self._consume(TokenType.STRING, "Se esperaba ruta del archivo").value
        self._consume(TokenType.USING, "Se esperaba 'USING'")
        self._consume(TokenType.INDEX, "Se esperaba 'INDEX'")

        index_type_token = self._advance()
        index_type = IndexType(index_type_token.value)

        self._consume(TokenType.LPAREN, "Se esperaba '(' después del tipo de índice")
        index_column = self._consume(TokenType.STRING, "Se esperaba nombre de columna entre comillas").value
        self._consume(TokenType.RPAREN, "Se esperaba ')' después del nombre de columna")
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final")

        return CreateTableFromFileQuery(
            OperationType.CREATE_TABLE_FROM_FILE,
            table_name,
            file_path,
            index_column,
            index_type,
        )

    def _parse_column(self) -> Column:
        """Parse de una definición de columna"""
        name = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de columna").value

        data_type_token = self._advance()
        size = None
        if data_type_token.value == "VARCHAR" and self._match(TokenType.LBRACKET):
            size = int(self._consume(TokenType.NUMBER, "Se esperaba tamaño para VARCHAR").value)
            self._consume(TokenType.RBRACKET, "Se esperaba ']' después del tamaño")
            data_type = DataType.VARCHAR
        elif data_type_token.value == "ARRAY" and self._match(TokenType.LBRACKET):
            self._consume(TokenType.FLOAT, "Se esperaba 'FLOAT' en ARRAY")
            self._consume(TokenType.RBRACKET, "Se esperaba ']' después de FLOAT")
            data_type = DataType.ARRAY_FLOAT
        else:
            data_type = DataType(data_type_token.value)

        is_key = self._match(TokenType.KEY)

        index_type = None
        if self._match(TokenType.INDEX):
            index_token = self._advance()
            index_type = IndexType(index_token.value)

        return Column(name, data_type, size, is_key, index_type)

    def _parse_select(self) -> SelectQuery:
        """Parse de SELECT"""
        columns = []

        if self._match(TokenType.ASTERISK):
            columns = ["*"]
        else:
            columns.append(self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de columna").value)
            while self._match(TokenType.COMMA):
                columns.append(self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de columna").value)

        self._consume(TokenType.FROM, "Se esperaba 'FROM'")
        table_name = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de tabla").value

        condition = None
        if self._match(TokenType.WHERE):
            condition = self._parse_condition()

        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final")
        return SelectQuery(OperationType.SELECT, table_name, columns, condition)

    def _parse_condition(self) -> Condition:
        """
        Parse de una o varias condiciones WHERE (soporta AND/OR)
        Ejemplo:
            precio < 150 AND stock > 50 OR categoria = 'A'
        """
        left = self._parse_single_condition()

        while self._match(TokenType.AND, TokenType.OR):
            logical_op = self._previous().value.upper()
            right = self._parse_single_condition()
            left = Condition(left=left, logical_op=logical_op, right=right)

        return left

    def _parse_single_condition(self) -> Condition:
        """Parsea una sola condición (sin AND/OR)"""
        if self._match(TokenType.LPAREN):
            inner = self._parse_condition()
            self._consume(TokenType.RPAREN, "Se esperaba ')' de cierre en condición agrupada")
            return inner
        column = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de columna").value

        if self._match(TokenType.BETWEEN):
            value1 = self._parse_value()
            self._consume(TokenType.AND, "Se esperaba 'AND' en BETWEEN")
            value2 = self._parse_value()
            return Condition(column=column, operator="BETWEEN", value=value1, value2=value2)

        elif self._match(TokenType.IN):
            self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'IN'")
            if self._check(TokenType.LBRACKET):
                point = self._parse_array()
                self._consume(TokenType.COMMA, "Se esperaba ',' después del punto")
                radius = self._parse_value()
                self._consume(TokenType.RPAREN, "Se esperaba ')' al final de IN")
                return Condition(column=column, operator="IN", value=[point, radius])
            values = [self._parse_value()]
            while self._match(TokenType.COMMA):
                values.append(self._parse_value())
            self._consume(TokenType.RPAREN, "Se esperaba ')' después de IN")
            return Condition(column=column, operator="IN", value=values)

        else:
            operator_token = self._advance()
            operator = operator_token.value
            value = self._parse_value()
            return Condition(column=column, operator=operator, value=value)

    def _parse_value(self) -> Any:
        """Parse de un valor"""
        if self._check(TokenType.LBRACKET):
            return self._parse_array()
        elif self._match(TokenType.NUMBER):
            value = self._previous().value
            return int(value) if "." not in value else float(value)
        elif self._match(TokenType.STRING):
            return self._previous().value
        elif self._match(TokenType.TRUE):
            return True
        elif self._match(TokenType.FALSE):
            return False
        else:
            raise ParseError("Se esperaba un valor")

    def _parse_array(self) -> List[float]:
        """Parse de un array [x, y, ...]"""
        self._consume(TokenType.LBRACKET, "Se esperaba '[' para iniciar array")
        values = [float(self._consume(TokenType.NUMBER, "Se esperaba número en array").value)]
        while self._match(TokenType.COMMA):
            values.append(float(self._consume(TokenType.NUMBER, "Se esperaba número en array").value))
        self._consume(TokenType.RBRACKET, "Se esperaba ']' para cerrar array")
        return values

    def _parse_insert(self) -> InsertQuery:
        """Parse de INSERT"""
        self._consume(TokenType.INTO, "Se esperaba 'INTO' después de 'INSERT'")
        table_name = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de tabla").value
        self._consume(TokenType.VALUES, "Se esperaba 'VALUES'")
        self._consume(TokenType.LPAREN, "Se esperaba '(' después de 'VALUES'")

        values = [self._parse_value()]
        while self._match(TokenType.COMMA):
            values.append(self._parse_value())

        self._consume(TokenType.RPAREN, "Se esperaba ')' después de los valores")
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final")

        return InsertQuery(OperationType.INSERT, table_name, values)


    def _parse_delete(self) -> DeleteQuery:
        """Parse de DELETE"""
        self._consume(TokenType.FROM, "Se esperaba 'FROM' después de 'DELETE'")
        table_name = self._consume(TokenType.IDENTIFIER, "Se esperaba nombre de tabla").value
        self._consume(TokenType.WHERE, "Se esperaba 'WHERE' en DELETE")
        condition = self._parse_condition()
        self._consume(TokenType.SEMICOLON, "Se esperaba ';' al final")

        return DeleteQuery(OperationType.DELETE, table_name, condition)


    def _match(self, *types: TokenType) -> bool:
        """Verifica si el token actual coincide con alguno de los tipos"""
        for token_type in types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type: TokenType) -> bool:
        """Verifica si el token actual es del tipo dado"""
        if self._is_at_end():
            return False
        return self._peek().type == token_type

    def _advance(self) -> Token:
        """Consume el token actual y retorna el anterior"""
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        """Verifica si hemos llegado al final"""
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        """Retorna el token actual sin consumirlo"""
        return self.tokens[self.current]

    def _previous(self) -> Token:
        """Retorna el token anterior"""
        return self.tokens[self.current - 1]

    def _consume(self, token_type: TokenType, message: str) -> Token:
        """Consume un token del tipo esperado o lanza error"""
        if self._check(token_type):
            return self._advance()
        current_token = self._peek()
        raise ParseError(f"{message}. Se encontró: {current_token.value}")


def parse_sql(sql_text: str) -> ParsedQuery:
    """Función de conveniencia para parsear directamente"""
    parser = SQLParser()
    return parser.parse(sql_text)
