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
    """Motor principal del parser SQL que integra todos los componentes"""

    def __init__(self, database_adapter=None):
        self.lexer = SQLLexer()
        self.parser = SQLParser()
        self.validator = SemanticValidator()
        self.translator = QueryTranslator(
            database_adapter or MockDatabaseAdapter(), self.validator
        )
        self.query_history = []

    def execute_sql(self, sql_text: str, validate: bool = True) -> Dict[str, Any]:
        """Ejecuta una o múltiples consultas SQL separadas por punto y coma"""
        # Normalizar el texto: asegurar que termine con ;
        sql_text = sql_text.strip()
        if not sql_text.endswith(";"):
            sql_text += ";"

        # Dividir por punto y coma (ignorando comentarios)
        queries = self._split_queries(sql_text)

        # Si solo hay una query, ejecutar normalmente
        if len(queries) <= 1:
            return self._execute_single_query(sql_text, validate)

        # Si hay múltiples queries, ejecutar todas y retornar resultado combinado
        return self._execute_multiple_queries(queries, validate)

    def _split_queries(self, sql_text: str) -> List[str]:
        """Divide el texto SQL en queries individuales (separadas por ;)"""
        # Limpiar comentarios primero
        lines = sql_text.split("\n")
        cleaned_lines = []
        for line in lines:
            # Eliminar comentarios
            if "--" in line:
                line = line[: line.index("--")]
            if line.strip():
                cleaned_lines.append(line)

        cleaned_text = "\n".join(cleaned_lines)

        # Dividir por punto y coma
        queries = []
        for q in cleaned_text.split(";"):
            q = q.strip()
            if q:
                # Agregar punto y coma solo si no lo tiene
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
            # 1. Parsing
            parsed_query = self.parser.parse(sql_text)
            result["parsed_query"] = parsed_query

            # 2. Traducción y ejecución
            execution_result = self.translator.translate_and_execute(
                parsed_query, validate
            )

            result["success"] = execution_result["success"]
            result["result"] = execution_result["result"]
            result["errors"] = execution_result.get("errors", [])

            # Guardar en historial
            self.query_history.append(
                {
                    "sql": sql_text,
                    "success": result["success"],
                    "timestamp": time.time(),
                }
            )

        except ParseError as e:
            result["errors"] = [f"Error de parsing: {e.message}"]
        except Exception as e:
            result["errors"] = [f"Error inesperado: {str(e)}"]

        result["execution_time_ms"] = (time.time() - start_time) * 1000
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
            query_result = self._execute_single_query(query, validate)

            all_results.append(
                {
                    "query": query[:50] + "..." if len(query) > 50 else query,
                    "success": query_result["success"],
                    "result": query_result["result"],
                    "errors": query_result["errors"],
                }
            )

            if not query_result["success"]:
                all_success = False
                all_errors.extend(query_result["errors"])

            # Guardar el último resultado (para SELECT u otras queries que retornen datos)
            if query_result["result"] is not None:
                last_result = query_result["result"]

        total_time = (time.time() - start_time) * 1000

        return {
            "success": all_success,
            "result": last_result,  # Retornar el último resultado con datos
            "all_results": all_results,  # Todos los resultados individuales
            "parsed_query": None,
            "execution_time_ms": total_time,
            "errors": all_errors,
            "queries_executed": len(queries),
        }

    def parse_only(self, sql_text: str) -> Tuple[bool, Any]:
        """Solo parsea sin ejecutar"""
        try:
            parsed_query = self.parser.parse(sql_text)
            return True, parsed_query
        except Exception as e:
            return False, str(e)

    def validate_only(self, sql_text: str) -> Tuple[bool, List[str]]:
        """Solo valida sin ejecutar"""
        try:
            parsed_query = self.parser.parse(sql_text)
            errors = self.validator.validate_query(parsed_query)
            return len(errors) == 0, errors
        except Exception as e:
            return False, [str(e)]

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Obtiene información de una tabla"""
        return self.translator.get_table_info(table_name)

    def list_tables(self) -> List[str]:
        """Lista todas las tablas registradas"""
        return self.translator.list_tables()

    def get_query_history(self, limit: int = 10) -> List[Dict]:
        """Obtiene el historial de consultas"""
        return self.query_history[-limit:]

    def get_operations_log(self) -> List[str]:
        """Obtiene el log de operaciones del adaptador"""
        return self.translator.get_operations_log()

    def clear_history(self):
        """Limpia el historial de consultas"""
        self.query_history.clear()


def create_sql_parser_engine(database_adapter=None) -> SQLParserEngine:
    """Crea un motor parser SQL completamente configurado"""
    return SQLParserEngine(database_adapter)
