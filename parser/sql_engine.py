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
        self.translator = QueryTranslator(database_adapter or MockDatabaseAdapter(), self.validator)
        self.query_history = []

    def execute_sql(self, sql_text: str, validate: bool = True) -> Dict[str, Any]:
        """Ejecuta una consulta SQL completa"""
        start_time = time.time()
        
        result = {
            "success": False,
            "result": None,
            "parsed_query": None,
            "execution_time_ms": 0,
            "errors": []
        }

        try:
            # 1. Parsing
            parsed_query = self.parser.parse(sql_text)
            result["parsed_query"] = parsed_query

            # 2. Traducción y ejecución
            execution_result = self.translator.translate_and_execute(parsed_query, validate)
            
            result["success"] = execution_result["success"]
            result["result"] = execution_result["result"]
            result["errors"] = execution_result.get("errors", [])

            # Guardar en historial
            self.query_history.append({
                "sql": sql_text,
                "success": result["success"],
                "timestamp": time.time()
            })

        except ParseError as e:
            result["errors"] = [f"Error de parsing: {e.message}"]
        except Exception as e:
            result["errors"] = [f"Error inesperado: {str(e)}"]

        result["execution_time_ms"] = (time.time() - start_time) * 1000
        return result

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
