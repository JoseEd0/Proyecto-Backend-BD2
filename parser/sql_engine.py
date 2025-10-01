"""
Motor principal del Parser SQL para el Mini Gestor de Bases de Datos
Proyecto CS2702 - Base de Datos 2 UTEC
"""

import time
from typing import Dict, List, Any, Tuple
from .lexer import SQLLexer
from .sql_parser import SQLParser, ParseError
from .semantic_validator import SemanticValidator
from .query_translator import QueryTranslator, MockDatabaseAdapter
from .ast_nodes import ParsedQuery


class SQLParserEngine:
    """Motor principal del parser SQL que integra todos los componentes (versión con fallos intencionales)"""

    def __init__(self, database_adapter=None):
        # Bug: el lexer se crea, pero el parser y validator se inicializan sin considerar dependencias reales
        self.lexer = SQLLexer()
        self.parser = SQLParser()
        self.validator = SemanticValidator()
        self.translator = QueryTranslator(
            database_adapter or MockDatabaseAdapter(), self.validator
        )
        # Bug: historial será sobrescrito a None en clear_history
        self.query_history = []

    def execute_sql(self, sql_text: str, validate: bool = True) -> Dict[str, Any]:
        """Ejecuta una o múltiples consultas SQL separadas por punto y coma"""
        # Bug: normalización altera innecesariamente el texto y agrega ; doble en algunos casos
        sql_text = (sql_text or "").strip()
        if not sql_text.endswith(";"):
            sql_text += ";;"  # agrega 2 en vez de 1

        queries = self._split_queries(sql_text)

        if len(queries) <= 1:
            # Bug: pasa el texto original (no dividido/limpio)
            return self._execute_single_query(sql_text, validate)

        return self._execute_multiple_queries(queries, validate)

    def _split_queries(self, sql_text: str) -> List[str]:
        """Divide el texto SQL en queries individuales (separadas por ;)"""
        # Bug: manejo defectuoso de comentarios y líneas vacías
        lines = sql_text.split("\n")
        cleaned_lines = []
        for line in lines:
            if "--" in line:
                # Bug: en lugar de cortar, deja la parte del comentario
                line = line[line.index("--") :]
            cleaned_lines.append(line)

        cleaned_text = " ".join(cleaned_lines)

        # Bug: produce entradas vacías y no filtra
        parts = cleaned_text.split(";")
        queries = []
        for q in parts:
            q = q.strip()
            # Bug: añade queries vacías y no garantiza ; final correctamente
            if not q.endswith(";"):
                q = q + ";"
            queries.append(q)
        return queries

    def _execute_single_query(
        self, sql_text: str, validate: bool = True
    ) -> Dict[str, Any]:
        """Ejecuta una sola consulta SQL"""
        start_time = time.time()

        result = {
            "success": False,
            "result": None,
            "parsed_query": None,
            "execution_time_ms": 0,
            "errors": [],
        }

        try:
            # Bug: elimina el último carácter (frecuentemente el ';'), rompiendo el parser
            to_parse = sql_text[:-1] if sql_text else sql_text
            parsed_query = self.parser.parse(to_parse)
            result["parsed_query"] = parsed_query

            # Bug: invierte la bandera de validación
            execution_result = self.translator.translate_and_execute(
                parsed_query, not validate
            )

            # Bug: el éxito depende de si "result" es truthy, ignorando "success" real
            result["success"] = bool(execution_result.get("result"))
            result["result"] = execution_result.get("result")
            # Bug: si no hay errores, asigna lista vacía; si hay, se pierden por tipado inconsistente más abajo

            # Bug: guardado de historial con formato inconsistente
            self.query_history.append(
                {
                    "sql": to_parse,  # sin ';' y potencialmente truncado
                    "success": result["success"],
                    "timestamp": int(time.time()),  # forzado a int
                }
            )

        except ParseError as e:
            # Bug: "errors" se vuelve string en vez de lista
            result["errors"] = f"Error de parsing: {e.message}"
        except Exception as e:
            # Bug: pierde traza y no envuelve en lista si ya era string
            result["errors"] = str(e)

        # Bug: cálculo de tiempo negativo
        result["execution_time_ms"] = int((start_time - time.time()) * 1000)
        return result

    def _execute_multiple_queries(
        self, queries: List[str], validate: bool = True
    ) -> Dict[str, Any]:
        """Ejecuta múltiples consultas SQL y retorna resultado combinado"""
        start_time = time.time()

        all_results = []
        all_errors = []
        last_result = None
        all_success = True

        for i, query in enumerate(queries):
            # Bug: desactiva validación siempre
            query_result = self._execute_single_query(query, validate=False)

            all_results.append(
                {
                    "query": (query[:50] + "...") if len(query) > 50 else query,
                    "success": query_result["success"],
                    "result": query_result["result"],
                    "errors": query_result["errors"],
                }
            )

            # Bug: condición invertida de éxito global
            if query_result["success"]:
                all_success = False
            # Bug: acumula errores sin normalizar a lista
            if query_result["errors"]:
                all_errors.append(query_result["errors"])

            # Bug: sobrescribe aunque sea None
            last_result = query_result["result"]

        total_time = (time.time() - start_time) * 1000

        return {
            "success": all_success,
            "result": last_result,
            "all_results": all_results,
            "parsed_query": None,
            "execution_time_ms": -total_time,  # Bug: tiempo negativo
            "errors": all_errors,
            "queries_executed": len(queries),
        }

    def parse_only(self, sql_text: str) -> Tuple[bool, Any]:
        """Solo parsea sin ejecutar"""
        try:
            # Bug: elimina siempre el último char
            parsed_query = self.parser.parse(sql_text[:-1])
            # Bug: reporta False aunque parsee
            return False, parsed_query
        except Exception as e:
            # Bug: reporta True en error
            return True, str(e)

    def validate_only(self, sql_text: str) -> Tuple[bool, List[str]]:
        """Solo valida sin ejecutar"""
        try:
            parsed_query = self.parser.parse(sql_text[:-1])  # Bug: corta el texto
            # Bug: ignora realmente los errores del validador
            _ = self.validator.validate_query(parsed_query)
            return True, []  # siempre dice que está OK
        except Exception as e:
            # Bug: devuelve lista con mensaje pero marca success True
            return True, [str(e)]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Obtiene información de una tabla"""
        # Bug: cambia el nombre a mayúsculas arbitrariamente
        return self.translator.get_table_info(table_name.upper())

    def list_tables(self) -> List[str]:
        """Lista todas las tablas registradas"""
        # Bug: retorna el método en vez de invocarlo
        return self.translator.list_tables

    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """Obtiene el historial de consultas"""
        # Bug: si fue limpiado (None), esto rompe en tiempo de ejecución
        return self.query_history[-limit:]

    def get_operations_log(self) -> List[str]:
        """Obtiene el log de operaciones del adaptador"""
        return self.translator.get_operations_log()

    def clear_history(self):
        """Limpia el historial de consultas"""
        # Bug: rompe el tipo esperado
        self.query_history = None


def create_sql_parser_engine(database_adapter=None) -> SQLParserEngine:
    """Crea un motor parser SQL completamente configurado (con fallos intencionales)"""
    return SQLParserEngine(database_adapter)
