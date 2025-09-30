"""
Traductor de consultas SQL a operaciones del mini gestor
Proyecto CS2702 - Base de Datos 2 UTEC
"""
from typing import Dict, List, Any, Optional
from .ast_nodes import *
from .semantic_validator import SemanticValidator, TableSchema


class MockDatabaseAdapter:
    """Adaptador mock para testing que simula operaciones del gestor"""

    def __init__(self):
        self.tables = {}
        self.operations_log = []

    def create_table(self, table_name: str, schema: List[Column]) -> bool:
        """Simula creación de tabla"""
        self.tables[table_name] = schema
        self.operations_log.append(f"createTable({table_name})")
        return True

    def create_table_from_file(self, table_name: str, file_path: str, index_column: str, index_type: IndexType) -> bool:
        """Simula creación de tabla desde archivo"""
        self.tables[table_name] = f"from_file_{file_path}"
        self.operations_log.append(f"createTableFromFile({table_name}, {file_path}, {index_column}, {index_type.value})")
        return True

    def search(self, table_name: str, column: str, key: Any) -> List[Any]:
        """Simula búsqueda exacta"""
        self.operations_log.append(f"search({table_name}, {column}, {key})")
        return [{"resultado": f"busqueda en {table_name} donde {column} = {key}"}]

    def range_search(self, table_name: str, column: str, begin_key: Any, end_key: Any) -> List[Any]:
        """Simula búsqueda por rango"""
        self.operations_log.append(f"rangeSearch({table_name}, {column}, {begin_key}, {end_key})")
        return [{"resultado": f"busqueda en {table_name} donde {column} BETWEEN {begin_key} AND {end_key}"}]

    def spatial_range_search(self, table_name: str, column: str, point: List[float], radius: float) -> List[Any]:
        """Simula búsqueda espacial por radio"""
        self.operations_log.append(f"spatialRangeSearch({table_name}, {column}, {point}, {radius})")
        return [{"resultado": f"busqueda espacial en {table_name} cerca de {point} con radio {radius}"}]

    def add(self, table_name: str, record: List[Any]) -> bool:
        """Simula inserción de registro"""
        self.operations_log.append(f"add({table_name}, {record})")
        return True

    def remove(self, table_name: str, column: str, key: Any) -> bool:
        """Simula eliminación de registro"""
        self.operations_log.append(f"remove({table_name}, {column}, {key})")
        return True

    def scan_all(self, table_name: str) -> List[Any]:
        """Simula scan completo de tabla"""
        self.operations_log.append(f"scanAll({table_name})")
        return [{"resultado": f"scan completo de {table_name}"}]

    def get_operations_log(self) -> List[str]:
        """Retorna el log de operaciones ejecutadas"""
        return self.operations_log.copy()


class QueryTranslator:
    """Traductor principal de consultas SQL a operaciones del gestor"""

    def __init__(self, database_adapter=None, semantic_validator=None):
        self.db_adapter = database_adapter or MockDatabaseAdapter()
        self.validator = semantic_validator or SemanticValidator()

    def translate_and_execute(self, query: ParsedQuery, validate: bool = True) -> Dict[str, Any]:
        """Traduce y ejecuta una consulta"""
        result = {
            "success": False,
            "result": None,
            "operation": None,
            "errors": []
        }

        try:
            if validate:
                errors = self.validator.validate_query(query)
                if errors:
                    result["errors"] = errors
                    return result

            if isinstance(query, CreateTableQuery):
                result["result"] = self._execute_create_table(query)
                result["operation"] = "CREATE_TABLE"
            elif isinstance(query, CreateTableFromFileQuery):
                result["result"] = self._execute_create_table_from_file(query)
                result["operation"] = "CREATE_TABLE_FROM_FILE"
            elif isinstance(query, SelectQuery):
                result["result"] = self._execute_select(query)
                result["operation"] = "SELECT"
            elif isinstance(query, InsertQuery):
                result["result"] = self._execute_insert(query)
                result["operation"] = "INSERT"
            elif isinstance(query, DeleteQuery):
                result["result"] = self._execute_delete(query)
                result["operation"] = "DELETE"

            result["success"] = True

        except Exception as e:
            result["errors"] = [str(e)]

        return result

    def _execute_create_table(self, query: CreateTableQuery) -> Any:
        """Ejecuta CREATE TABLE"""
        success = self.db_adapter.create_table(query.table_name, query.columns)

        schema = TableSchema(query.table_name, query.columns)
        self.validator.register_table(schema)

        return f"Tabla '{query.table_name}' creada exitosamente"


    def _execute_create_table_from_file(self, query: CreateTableFromFileQuery) -> Any:
        """Ejecuta CREATE TABLE FROM FILE y registra el esquema para futuras validaciones"""
        success = self.db_adapter.create_table_from_file(
            query.table_name,
            query.file_path,
            query.index_column,
            query.index_type
        )

        # Intentar recuperar el esquema desde el adaptador y registrarlo en el validador
        try:
            if hasattr(self.db_adapter, "get_table_info"):
                info = self.db_adapter.get_table_info(query.table_name)
                if info and isinstance(info, dict) and "columns" in info:
                    cols = []
                    valid_dt = {d.value: d for d in DataType}
                    valid_ix = {i.value: i for i in IndexType}
                    for c in info["columns"]:
                        name = c.get("name")
                        tval = c.get("type")
                        dt = valid_dt.get(tval, DataType.VARCHAR)
                        size = c.get("size", None)
                        is_key = bool(c.get("is_key", False))
                        ixval = c.get("index", c.get("index_type"))
                        ix = valid_ix.get(ixval) if ixval else None
                        cols.append(Column(name=name, data_type=dt, size=size, is_key=is_key, index_type=ix))
                    self.validator.register_table(TableSchema(query.table_name, cols))
        except Exception:
            # Si algo falla, no hacemos crash; el adaptador seguirá funcionando
            pass

        return f"Tabla '{query.table_name}' creada desde archivo '{query.file_path}'"

    def _execute_select(self, query: SelectQuery) -> Any:
        """Ejecuta SELECT"""
        cond = query.condition

        # Sin WHERE → scan completo
        if cond is None:
            return self.db_adapter.scan_all(query.table_name)

        # 1) Condición compuesta: filtrar en memoria (fallback general)
        if hasattr(cond, "logical_op") and cond.logical_op:
            rows = self.db_adapter.scan_all(query.table_name)
            return [r for r in rows if self._eval_condition(r, cond)]

        # 2) Detectar patrón espacial: IN ([x,y,...], radio)
        if cond.operator == "IN":
            v = cond.value
            is_spatial = (
                    isinstance(v, list)
                    and len(v) == 2
                    and isinstance(v[0], list)  # el punto [x,y]...
                    and isinstance(v[1], (int, float))  # ...y el radio
            )
            if is_spatial:
                point, radius = v[0], float(v[1])
                return self.db_adapter.spatial_range_search(
                    query.table_name, cond.column, point, radius
                )

            # IN genérico (lista de valores) → scan + filtro
            rows = self.db_adapter.scan_all(query.table_name)
            return [r for r in rows if self._eval_condition(r, cond)]

        # 3) Operadores simples
        if cond.operator == "=":
            return self.db_adapter.search(query.table_name, cond.column, cond.value)
        elif cond.operator == "BETWEEN":
            return self.db_adapter.range_search(
                query.table_name, cond.column, cond.value, cond.value2
            )
        elif cond.operator in ["<", ">", "<=", ">="]:
            rows = self.db_adapter.scan_all(query.table_name)
            return [r for r in rows if self._eval_condition(r, cond)]
        else:
            return [{"error": f"Operador {cond.operator} no soportado"}]

    def _eval_condition(self, row: Dict[str, Any], cond: Condition) -> bool:
        if cond.logical_op:
            l = self._eval_condition(row, cond.left) if cond.left else False
            r = self._eval_condition(row, cond.right) if cond.right else False
            return (l and r) if cond.logical_op == "AND" else (l or r)

        col = cond.column
        v = row.get(col) if isinstance(row, dict) else None
        op = cond.operator

        if op == "=":
            return v == cond.value
        if op == "<":
            return v is not None and v < cond.value
        if op == ">":
            return v is not None and v > cond.value
        if op == "<=":
            return v is not None and v <= cond.value
        if op == ">=":
            return v is not None and v >= cond.value
        if op == "BETWEEN":
            return v is not None and cond.value <= v <= cond.value2
        if op == "IN":
            if isinstance(cond.value, list) and len(cond.value) == 2 and isinstance(cond.value[0], list):
                point, radius = cond.value
                try:
                    if not (isinstance(v, list) and len(v) >= 2):
                        return False
                    cx, cy = float(point[0]), float(point[1])
                    px, py = float(v[0]), float(v[1])
                    dx, dy = px - cx, py - cy
                    import math
                    return math.hypot(dx, dy) <= float(radius)
                except Exception:
                    return False
            if isinstance(cond.value, list):
                return v in cond.value
            return False
        return False

    def _execute_insert(self, query: InsertQuery) -> Any:
        """Ejecuta INSERT"""
        success = self.db_adapter.add(query.table_name, query.values)
        if not success:
            raise Exception(f"No se pudo insertar el registro en '{query.table_name}' (posible duplicado)")
        return f"Registro insertado en '{query.table_name}'"

    def _execute_delete(self, query: DeleteQuery) -> Any:
        """Ejecuta DELETE"""
        condition = query.condition
        success = self.db_adapter.remove(query.table_name, condition.column, condition.value)
        if not success:
            raise Exception(f"No se pudo eliminar el registro de '{query.table_name}'")
        return f"Registro eliminado de '{query.table_name}'"

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una tabla"""
        if table_name in self.validator.tables:
            schema = self.validator.tables[table_name]
            return {
                "name": schema.name,
                "columns": [{"name": col.name, "type": col.data_type.value, "is_key": col.is_key, "index": col.index_type.value if col.index_type else None} for col in schema.columns.values()]
            }
        return None

    def list_tables(self) -> List[str]:
        """Lista todas las tablas registradas"""
        return list(self.validator.tables.keys())

    def get_operations_log(self) -> List[str]:
        """Obtiene el log de operaciones ejecutadas"""
        if hasattr(self.db_adapter, 'get_operations_log'):
            return self.db_adapter.get_operations_log()
        return []
