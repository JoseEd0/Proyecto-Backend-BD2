"""
Validador semántico para consultas SQL
Proyecto CS2702 - Base de Datos 2 UTEC
"""
from typing import Dict, List, Optional
from .ast_nodes import *


class TableSchema:
    """Representa el esquema de una tabla"""
    def __init__(self, name: str, columns: List[Column]):
        self.name = name
        self.columns = {col.name: col for col in columns}

    def has_column(self, column_name: str) -> bool:
        """Verifica si la tabla tiene una columna específica"""
        return column_name in self.columns

    def get_column(self, column_name: str) -> Optional[Column]:
        """Obtiene la definición de una columna"""
        return self.columns.get(column_name)


class SemanticValidator:
    """Validador semántico para consultas SQL"""

    def __init__(self):
        self.tables: Dict[str, TableSchema] = {}

    def register_table(self, schema: TableSchema):
        """Registra el esquema de una tabla"""
        self.tables[schema.name] = schema

    def validate_query(self, query: ParsedQuery) -> List[str]:
        """Valida una consulta y retorna lista de errores"""
        errors = []

        if isinstance(query, CreateTableQuery):
            errors.extend(self._validate_create_table(query))
        elif isinstance(query, SelectQuery):
            errors.extend(self._validate_select(query))
        elif isinstance(query, InsertQuery):
            errors.extend(self._validate_insert(query))
        elif isinstance(query, DeleteQuery):
            errors.extend(self._validate_delete(query))

        return errors

    def _validate_create_table(self, query: CreateTableQuery) -> List[str]:
        """Valida CREATE TABLE"""
        errors = []
        
        # Verificar que existe exactamente una columna KEY
        key_columns = [col for col in query.columns if col.is_key]
        if len(key_columns) == 0:
            errors.append("La tabla debe tener exactamente una columna marcada como KEY")
        elif len(key_columns) > 1:
            errors.append("La tabla no puede tener más de una columna KEY")

        # Validar compatibilidad de tipos de índice con tipos de datos
        for col in query.columns:
            if col.index_type:
                if col.data_type == DataType.ARRAY_FLOAT and col.index_type != IndexType.RTREE:
                    errors.append(f"Los datos espaciales (ARRAY[FLOAT]) solo pueden usar índice RTree")
                elif col.data_type != DataType.ARRAY_FLOAT and col.index_type == IndexType.RTREE:
                    errors.append(f"El índice RTree solo puede usarse con datos espaciales (ARRAY[FLOAT])")

        return errors

    def _validate_select(self, query: SelectQuery) -> List[str]:
        """Valida SELECT"""
        errors = []
        
        # Verificar que la tabla existe
        if query.table_name not in self.tables:
            errors.append(f"La tabla '{query.table_name}' no existe")
            return errors

        schema = self.tables[query.table_name]
        
        # Verificar columnas (excepto *)
        if not query.is_select_all():
            for col_name in query.columns:
                if not schema.has_column(col_name):
                    errors.append(f"La columna '{col_name}' no existe en la tabla '{query.table_name}'")

        # Validar condición WHERE
        if query.condition:
            errors.extend(self._validate_condition(query.condition, schema))

        return errors

    def _validate_insert(self, query: InsertQuery) -> List[str]:
        """Valida INSERT"""
        errors = []
        
        if query.table_name not in self.tables:
            errors.append(f"La tabla '{query.table_name}' no existe")
            return errors

        schema = self.tables[query.table_name]
        
        # Verificar que el número de valores coincide con el número de columnas
        if len(query.values) != len(schema.columns):
            errors.append(f"Se esperaban {len(schema.columns)} valores, se proporcionaron {len(query.values)}")

        return errors

    def _validate_delete(self, query: DeleteQuery) -> List[str]:
        """Valida DELETE"""
        errors = []
        
        if query.table_name not in self.tables:
            errors.append(f"La tabla '{query.table_name}' no existe")
            return errors

        schema = self.tables[query.table_name]
        errors.extend(self._validate_condition(query.condition, schema))

        return errors

    def _validate_condition(self, condition: Condition, schema: TableSchema) -> List[str]:
        """Valida una condición WHERE"""
        errors = []
        
        # Verificar que la columna existe
        if not schema.has_column(condition.column):
            errors.append(f"La columna '{condition.column}' no existe")
            return errors

        column = schema.get_column(condition.column)
        
        # Validar consultas espaciales
        if condition.operator == "IN" and isinstance(condition.value, list) and len(condition.value) == 2:
            # Es una consulta espacial
            if column.data_type != DataType.ARRAY_FLOAT:
                errors.append(f"Las consultas espaciales solo pueden usarse en columnas ARRAY[FLOAT]")

        # Validar BETWEEN con índices HASH
        if condition.operator == "BETWEEN" and column.index_type == IndexType.HASH:
            errors.append(f"Los índices HASH no soportan búsquedas por rango (BETWEEN)")

        return errors
