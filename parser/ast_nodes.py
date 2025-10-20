"""
Estructuras de datos para representar el resultado del parsing SQL
Proyecto CS2702 - Base de Datos 2 UTEC
"""
from enum import Enum
from typing import Any, List, Optional
from dataclasses import dataclass


class IndexType(Enum):
    """Tipos de índices soportados por el mini gestor"""
    SEQ = "SEQ"
    BTREE = "BTree"
    ISAM = "ISAM"
    HASH = "Hash"
    RTREE = "RTree"


class DataType(Enum):
    """Tipos de datos soportados"""
    INT = "INT"
    VARCHAR = "VARCHAR"
    DATE = "DATE"
    ARRAY_FLOAT = "ARRAY[FLOAT]"


class OperationType(Enum):
    """Tipos de operaciones SQL"""
    CREATE_TABLE = "CREATE_TABLE"
    CREATE_TABLE_FROM_FILE = "CREATE_TABLE_FROM_FILE"
    SELECT = "SELECT"
    INSERT = "INSERT"
    DELETE = "DELETE"


@dataclass
class Column:
    """Representa una columna en la definición de tabla"""
    name: str
    data_type: DataType
    size: Optional[int] = None  # Para VARCHAR[n]
    is_key: bool = False
    index_type: Optional[IndexType] = None


@dataclass
class Condition:
    """Representa una condición WHERE"""
    column: str
    operator: str  # =, <, >, <=, >=, BETWEEN, IN
    value: Any
    value2: Optional[Any] = None  # Para BETWEEN


@dataclass
class ParsedQuery:
    """Clase base para todas las consultas parseadas"""
    operation_type: OperationType
    table_name: str


@dataclass
class CreateTableQuery(ParsedQuery):
    """Consulta CREATE TABLE parseada"""
    columns: List[Column]

    def __post_init__(self):
        self.operation_type = OperationType.CREATE_TABLE

    def get_key_column(self) -> Optional[Column]:
        """Retorna la columna marcada como KEY"""
        for col in self.columns:
            if col.is_key:
                return col
        return None


@dataclass
class CreateTableFromFileQuery(ParsedQuery):
    """Consulta CREATE TABLE FROM FILE parseada"""
    file_path: str
    index_column: str
    index_type: IndexType

    def __post_init__(self):
        self.operation_type = OperationType.CREATE_TABLE_FROM_FILE


@dataclass
class SelectQuery(ParsedQuery):
    """Consulta SELECT parseada"""
    columns: List[str]  # ["*"] para SELECT *
    condition: Optional[Condition] = None

    def __post_init__(self):
        self.operation_type = OperationType.SELECT

    def is_select_all(self) -> bool:
        """Verifica si es SELECT *"""
        return len(self.columns) == 1 and self.columns[0] == "*"


@dataclass
class InsertQuery(ParsedQuery):
    """Consulta INSERT parseada"""
    values: List[Any]

    def __post_init__(self):
        self.operation_type = OperationType.INSERT


@dataclass
class DeleteQuery(ParsedQuery):
    """Consulta DELETE parseada"""
    condition: Condition

    def __post_init__(self):
        self.operation_type = OperationType.DELETE
