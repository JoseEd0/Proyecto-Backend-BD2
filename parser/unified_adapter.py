"""
Adaptador Unificado de Base de Datos - Soporta todas las estructuras
Proyecto CS2702 - Base de Datos 2 UTEC

Este adaptador integra:
- Sequential File: Para datos ordenados y búsquedas secuenciales
- B+ Tree: Para búsquedas rápidas y rangos en claves numéricas
- ISAM: Para archivos grandes estáticos con pocas actualizaciones
- Extendible Hashing: Para búsquedas por igualdad muy rápidas
- R-Tree: Para consultas espaciales (coordenadas geográficas)

SELECCIÓN AUTOMÁTICA (Prioridad cuando NO se especifica USING INDEX):
1. RTree: Si la clave es ARRAY[FLOAT] o hay consultas espaciales
2. BTree: Por defecto, búsquedas rápidas y soporte de rangos (mejor opción general)
3. RTree: Alternativa si BTree no está disponible
4. ISAM: Si solo están disponibles estructuras estáticas
5. Sequential: Último recurso si ninguna otra está disponible

ESPECIFICAR ÍNDICE MANUALMENTE:
- CREATE TABLE ... USING INDEX BTree('columna')
- CREATE TABLE ... USING INDEX Hash('columna')
- CREATE TABLE ... USING INDEX RTree('columna')
- CREATE TABLE ... USING INDEX Isam('columna')
- CREATE TABLE ... USING INDEX Seq('columna')
"""
import os
import sys
import csv
from typing import Dict, List, Any, Optional
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

HAS_SEQUENTIAL = False
HAS_BTREE = False
HAS_ISAM = False
HAS_HASH = False
HAS_RTREE = False

try:
    from Sequential_Struct.sequential_file import SequentialFile  # type: ignore
    HAS_SEQUENTIAL = True
except Exception as e:
    print(f"⚠️  Sequential File no disponible: {e}")

try:
    from b_plus_tree.bplustree import BPlusTree  # type: ignore
    HAS_BTREE = True
except Exception as e:
    print(f"⚠️  B+ Tree no disponible: {e}")

try:
    from ISAM.ISAM import create_isam_index, ISAMIndex  # type: ignore
    HAS_ISAM = True
except Exception:
    try:
        from ISAM import create_isam_index, ISAMIndex  # type: ignore
        HAS_ISAM = True
    except Exception as e:
        print(f"⚠️  ISAM no disponible: {e}")

try:
    from extendible_hashing.extendible_hashing import DiskExtendibleHashing  # type: ignore
    HAS_HASH = True
except Exception as e:
    print(f"⚠️  Extendible Hashing no disponible: {e}")

try:
    from rtree_impl import RTreeIndex, Point, SpatialRecord, create_record  # type: ignore
    HAS_RTREE = True
except Exception:
    try:
        from Rtree.rtree_impl import RTreeIndex, Point, SpatialRecord, create_record  # type: ignore
        HAS_RTREE = True
    except Exception as e:
        print(f"⚠️  R-Tree no disponible: {e}")

try:
    from parser.ast_nodes import Column, DataType, IndexType  # type: ignore
except Exception:
    from ast_nodes import Column, DataType, IndexType  # type: ignore


class StructureType:
    SEQUENTIAL = "sequential"
    BTREE = "btree"
    ISAM = "isam"
    HASH = "hash"
    RTREE = "rtree"


class StructureSelector:
    @staticmethod
    def select_structure(index_type: Optional[IndexType], key_data_type: DataType, has_spatial_queries: bool = False) -> Optional[str]:
        """Devuelve el tipo de estructura a usar dado un índice deseado y tipo de clave.
        Si index_type es None, aplica heurísticas y un fallback sensato.
        """
        if index_type:
            mapping = {
                IndexType.SEQ:   (StructureType.SEQUENTIAL, HAS_SEQUENTIAL),
                IndexType.BTREE: (StructureType.BTREE, HAS_BTREE),
                IndexType.ISAM:  (StructureType.ISAM, HAS_ISAM),
                IndexType.HASH:  (StructureType.HASH, HAS_HASH),
                IndexType.RTREE: (StructureType.RTREE, HAS_RTREE),
            }
            structure, is_available = mapping.get(index_type, (StructureType.SEQUENTIAL, HAS_SEQUENTIAL))
            if not is_available:
                return StructureType.SEQUENTIAL if HAS_SEQUENTIAL else None
            return structure

        if (key_data_type == DataType.ARRAY_FLOAT or has_spatial_queries) and HAS_RTREE:
            return StructureType.RTREE

        if HAS_BTREE:
            return StructureType.BTREE
        if HAS_RTREE:
            return StructureType.RTREE
        if HAS_ISAM:
            return StructureType.ISAM
        if HAS_SEQUENTIAL:
            return StructureType.SEQUENTIAL
        return None

    @staticmethod
    def get_recommendations(key_data_type: DataType) -> Dict[str, str]:
        return {
            StructureType.SEQUENTIAL: "✅ Datos ordenados, búsquedas secuenciales y por rango",
            StructureType.BTREE: "⚡ Búsquedas muy rápidas, excelente para rangos, balanceado",
            StructureType.ISAM: "📚 Tablas grandes estáticas, principalmente lectura",
            StructureType.HASH: "🚀 Búsquedas exactas ultra rápidas (no soporta rangos)",
            StructureType.RTREE: "🌍 Consultas espaciales, coordenadas geográficas",
        }


class UnifiedDatabaseAdapter:
    """Adaptador unificado que orquesta las distintas estructuras físicas."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for structure in [StructureType.SEQUENTIAL, StructureType.BTREE, StructureType.ISAM, StructureType.HASH, StructureType.RTREE]:
            (self.data_dir / structure).mkdir(parents=True, exist_ok=True)
        self.tables: Dict[str, Any] = {}
        self.table_structures: Dict[str, str] = {}
        self.table_schemas: Dict[str, List[Column]] = {}
        self.operations_log: List[str] = []

    def _log_operation(self, operation: str) -> None:
        self.operations_log.append(operation)
        print(f"📝 {operation}")

    def _convert_column_to_struct_format(self, column: Column) -> str:
        if column.data_type == DataType.INT:
            return "i"
        if column.data_type == DataType.FLOAT:
            return "f"
        if column.data_type == DataType.VARCHAR:
            size = column.size if column.size else 50
            return f"{size}s"
        if column.data_type == DataType.DATE:
            return "10s"
        if column.data_type == DataType.ARRAY_FLOAT:
            return "16s"
        return "i"

    def _get_key_column(self, schema: List[Column]) -> Optional[Column]:
        for col in schema:
            if getattr(col, "is_key", False):
                return col
        return None

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        if table_name not in self.table_schemas:
            return None
        schema = self.table_schemas[table_name]
        structure_type = self.table_structures.get(table_name, "unknown")
        columns = []
        for col in schema:
            columns.append(
                {
                    "name": col.name,
                    "type": (col.data_type.value if hasattr(col.data_type, "value") else str(col.data_type)),
                    "size": getattr(col, "size", None),
                    "is_key": getattr(col, "is_key", False),
                    "index_type": (col.index_type.value if getattr(col, "index_type", None) and hasattr(col.index_type, "value") else None),
                }
            )
        return {
            "name": table_name,
            "columns": columns,
            "structure": structure_type,
            "record_count": (len(self.scan_all(table_name)) if table_name in self.tables else 0),
        }

    def list_tables(self) -> List[str]:
        return list(self.tables.keys())

    def get_operations_log(self) -> List[str]:
        return self.operations_log.copy()

    def __repr__(self) -> str:
        return f"UnifiedDatabaseAdapter(tables={len(self.tables)})"

    def create_table(self, table_name: str, schema: List[Column]) -> bool:
        try:
            if table_name in self.tables:
                raise ValueError(f"La tabla '{table_name}' ya existe")
            key_column = self._get_key_column(schema)
            if not key_column:
                raise ValueError(f"No se especificó columna KEY para la tabla '{table_name}'")

            structure_type = StructureSelector.select_structure(
                getattr(key_column, "index_type", None),
                key_column.data_type,
                has_spatial_queries=(key_column.data_type == DataType.ARRAY_FLOAT),
            )
            if structure_type is None:
                raise ValueError("No hay estructuras de datos disponibles.")

            self._log_operation(f"CREATE TABLE {table_name} usando estructura {structure_type.upper()}")

            if structure_type == StructureType.SEQUENTIAL:
                self._create_sequential_table(table_name, schema, key_column)
            elif structure_type == StructureType.BTREE:
                self._create_btree_table(table_name, schema, key_column)
            elif structure_type == StructureType.ISAM:
                self._create_isam_table(table_name, key_column, block_factor=4)
            elif structure_type == StructureType.HASH:
                self._create_hash_table(table_name, schema, key_column)
            elif structure_type == StructureType.RTREE:
                self._create_rtree_table(table_name, schema, key_column)
            else:
                raise ValueError(f"Estructura '{structure_type}' no soportada")

            self.table_structures[table_name] = structure_type
            self.table_schemas[table_name] = schema
            return True
        except Exception as e:
            self._log_operation(f"❌ Error creando tabla '{table_name}': {e}")
            raise

    def _create_sequential_table(self, table_name: str, schema: List[Column], key_column: Column) -> None:
        if not HAS_SEQUENTIAL:
            raise ImportError("Sequential File no está disponible")
        table_format: Dict[str, str] = {}
        for col in schema:
            format_str = self._convert_column_to_struct_format(col)
            table_format[col.name] = format_str
        index_file = str(self.data_dir / StructureType.SEQUENTIAL / f"{table_name}_index.bin")
        data_file = str(self.data_dir / StructureType.SEQUENTIAL / f"{table_name}_data.bin")
        sequential = SequentialFile(
            table_format=table_format,
            name_key=key_column.name,
            index_file=index_file,
            data_file=data_file,
            max_aux_size=100,
            force_create=True,
        )
        self.tables[table_name] = sequential

    def _create_btree_table(self, table_name: str, schema: List[Column], key_column: Column) -> None:
        if not HAS_BTREE:
            raise ImportError("B+ Tree no está disponible")
        storage_path = str(self.data_dir / StructureType.BTREE / table_name)
        os.makedirs(storage_path, exist_ok=True)
        btree = BPlusTree(order=4, storage_path=storage_path, index_name=table_name)
        if not hasattr(btree, "_data_storage"):
            btree._data_storage = {}
        self.tables[table_name] = btree

    def _create_isam_table(self, table_name: str, key_column: Column, block_factor: int = 4) -> ISAMIndex:
        if not HAS_ISAM:
            raise RuntimeError("ISAM no disponible")
        storage_dir = self.data_dir / "isam" / table_name
        os.makedirs(storage_dir, exist_ok=True)
        file_path = str(storage_dir / table_name)
        index = create_isam_index(file_path=file_path, block_factor=block_factor)  # type: ignore
        if not hasattr(index, "_data_storage"):
            index._data_storage = {}
        self.tables[table_name] = index
        self.table_structures[table_name] = StructureType.ISAM
        return index

    def _create_hash_table(self, table_name: str, schema: List[Column], key_column: Column) -> None:
        if not HAS_HASH:
            raise ImportError("Extendible Hashing no está disponible")
        dir_path = str(self.data_dir / StructureType.HASH / table_name)
        os.makedirs(dir_path, exist_ok=True)
        hash_table = DiskExtendibleHashing(  # type: ignore
            dir_path=dir_path,
            bucket_capacity=4,
            initial_global_depth=2,
            max_global_depth=4,
        )
        self.tables[table_name] = hash_table

    def _create_rtree_table(self, table_name: str, schema: List[Column], key_column: Column) -> None:
        if not HAS_RTREE:
            raise ImportError("R-Tree no está disponible")
        file_path = str(self.data_dir / StructureType.RTREE / table_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        rtree = RTreeIndex(file_path=file_path, dimension=2)  # type: ignore
        self.tables[table_name] = rtree

    def add(self, table_name: str, record: List[Any]) -> bool:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        schema = self.table_schemas[table_name]
        try:
            if structure_type == StructureType.SEQUENTIAL:
                success = structure.insert(record)

            elif structure_type == StructureType.BTREE:
                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                key = record[key_index]
                if hasattr(structure, "_data_storage") and isinstance(structure._data_storage, dict):
                    structure._data_storage[key] = record
                structure.add(key, record)
                success = True

            elif structure_type == StructureType.HASH:
                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                key = str(record[key_index])
                record_dict = {col.name: record[i] for i, col in enumerate(schema)}
                structure.add(key, record_dict)
                success = True

            elif structure_type == StructureType.RTREE:
                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                record_id = str(record[key_index])
                coord_index = next((i for i, col in enumerate(schema) if col.data_type == DataType.ARRAY_FLOAT), None)
                if coord_index is None:
                    raise ValueError("R-Tree requiere una columna ARRAY[FLOAT]")
                coordinates = record[coord_index]
                if not isinstance(coordinates, list):
                    raise ValueError("Las coordenadas deben ser una lista")
                data = {col.name: record[i] for i, col in enumerate(schema)}
                spatial_record = create_record(record_id, coordinates, data)
                success = structure.add(spatial_record)

            elif structure_type == StructureType.ISAM:
                row_dict = {col.name: record[i] if i < len(record) else None for i, col in enumerate(schema)}
                key_col = next(col for col in schema if col.is_key)
                key = row_dict[key_col.name]
                if not isinstance(key, int):
                    raise ValueError("La clave para ISAM debe ser INT")
                ds = getattr(structure, "_data_storage", None)
                if isinstance(ds, dict):
                    ds.setdefault(key, []).append(row_dict)
                structure.add(int(key), row_dict)
                success = True

            else:
                raise ValueError(f"Estructura '{structure_type}' no soportada para INSERT")

            if success:
                self._log_operation(f"INSERT INTO {table_name} VALUES {record}")
            return success
        except Exception as e:
            self._log_operation(f"❌ Error insertando en '{table_name}': {e}")
            raise

    def add_many(self, table_name: str, rows: List[List[Any]]) -> None:
        tbl = self.tables.get(table_name)
        if not tbl:
            raise ValueError(f"Tabla '{table_name}' no existe")
        for r in rows:
            self.add(table_name, r)

    def search(self, table_name: str, column: str, key: Any) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        schema = self.table_schemas[table_name]
        
        # Verificar si la columna de búsqueda es la clave primaria
        key_column = next((col for col in schema if col.is_key), None)
        is_key_search = key_column and key_column.name == column
        
        try:
            # Si la búsqueda NO es por clave primaria, hacer scan completo y filtrar
            if not is_key_search:
                self._log_operation(f"⚠️  Búsqueda por columna no-clave '{column}', haciendo scan completo")
                all_rows = self._scan_all_raw(table_name)
                dict_rows = self._records_to_dicts(table_name, all_rows)
                raw_results = [r for r in dict_rows if r.get(column) == key]
                self._log_operation(f"SEARCH {table_name} WHERE {column} = {key} (encontrados: {len(raw_results)})")
                return raw_results
            
            # Si es búsqueda por clave, usar el índice
            if structure_type == StructureType.SEQUENTIAL:
                result = structure.search(key)
                raw_results = [result] if result is not None else []

            elif structure_type == StructureType.BTREE:
                result = structure.search(key)
                if result:
                    full_record = None
                    if hasattr(structure, "_data_storage") and isinstance(structure._data_storage, dict):
                        full_record = structure._data_storage.get(key)
                    raw_results = [full_record] if full_record else []
                else:
                    raw_results = []

            elif structure_type == StructureType.HASH:
                result = structure.search(str(key))
                raw_results = [result] if result is not None else []

            elif structure_type == StructureType.RTREE:
                result = structure.search(str(key))
                raw_results = [result.data] if result else []

            elif structure_type == StructureType.ISAM:
                raw_results = structure.search(int(key))

            else:
                raw_results = []

            self._log_operation(f"SEARCH {table_name} WHERE {column} = {key}")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"❌ Error buscando en '{table_name}': {e}")
            raise

    def range_search(self, table_name: str, column: str, begin_key: Any, end_key: Any) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        try:
            if structure_type == StructureType.SEQUENTIAL:
                raw_results = structure.search_range(begin_key, end_key)

            elif structure_type == StructureType.BTREE:
                results = structure.range_search(begin_key, end_key)
                raw_results = []
                for key, _ in results:
                    full_record = None
                    if hasattr(structure, "_data_storage") and isinstance(structure._data_storage, dict):
                        full_record = structure._data_storage.get(key)
                    if full_record:
                        raw_results.append(full_record)

            elif structure_type == StructureType.ISAM:
                raw_results = structure.range_search(int(begin_key), int(end_key))

            elif structure_type == StructureType.HASH:
                self._log_operation("⚠️  Hash no soporta RANGE, haciendo scan completo")
                raw_results = self._scan_all_raw(table_name)
                schema = self.table_schemas[table_name]
                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                raw_results = [r for r in raw_results if begin_key <= r[key_index] <= end_key]

            else:
                raw_results = []

            self._log_operation(f"RANGE SEARCH {table_name} WHERE {column} BETWEEN {begin_key} AND {end_key}")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"❌ Error en range_search de '{table_name}': {e}")
            raise

    def spatial_range_search(self, table_name: str, column: str, point: List[float], radius: float) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        try:
            if structure_type == StructureType.RTREE:
                center = Point(point)
                results = structure.range_search(center, radius)
                raw_results = [r.data for r in results]
            else:
                self._log_operation(f"⚠️  {structure_type.upper()} no está optimizado para spatial search")
                raw_results = []
            self._log_operation(f"SPATIAL SEARCH {table_name} WHERE {column} IN ({point}, {radius})")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"❌ Error en spatial_search de '{table_name}': {e}")
            raise

    def remove(self, table_name: str, column: str, key: Any) -> bool:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        schema = self.table_schemas[table_name]
        try:
            if structure_type == StructureType.SEQUENTIAL:
                success = structure.delete(key)

            elif structure_type == StructureType.BTREE:
                structure.delete(key)
                if hasattr(structure, "_data_storage") and isinstance(structure._data_storage, dict) and key in structure._data_storage:
                    del structure._data_storage[key]
                success = True

            elif structure_type == StructureType.HASH:
                success = structure.remove(str(key))

            elif structure_type == StructureType.RTREE:
                success = structure.remove(str(key))

            elif structure_type == StructureType.ISAM:
                removed = structure.remove(int(key))
                ds = getattr(structure, "_data_storage", None)
                if isinstance(ds, dict) and int(key) in ds:
                    ds.pop(int(key), None)
                success = removed > 0

            else:
                success = False

            if success:
                self._log_operation(f"DELETE FROM {table_name} WHERE {column} = {key}")
            return success
        except Exception as e:
            self._log_operation(f"❌ Error eliminando de '{table_name}': {e}")
            raise

    def scan_all(self, table_name: str) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        raw_results = self._scan_all_raw(table_name)
        self._log_operation(f"SCAN ALL {table_name} ({len(raw_results)} records)")
        return self._records_to_dicts(table_name, raw_results)

    def _scan_all_raw(self, table_name: str) -> List[Any]:
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        if structure_type == StructureType.SEQUENTIAL:
            return structure.scan_all()
        if structure_type == StructureType.BTREE:
            if hasattr(structure, "_data_storage") and isinstance(structure._data_storage, dict):
                return list(structure._data_storage.values())
            return []
        if structure_type == StructureType.HASH:
            return []
        if structure_type == StructureType.RTREE:
            records = structure.get_all_records()
            return [r.data for r in records]
        if structure_type == StructureType.ISAM:
            ds = getattr(structure, "_data_storage", None)
            if isinstance(ds, dict) and ds:
                out: List[dict] = []
                for lst in ds.values():
                    out.extend(lst)
                return out
            return structure.get_all()
        return []

    def _records_to_dicts(self, table_name: str, records: List[Any]) -> List[Dict[str, Any]]:
        if table_name not in self.table_schemas:
            return records
        schema = self.table_schemas[table_name]
        dict_results: List[Dict[str, Any]] = []
        for record in records:
            if isinstance(record, dict):
                dict_results.append(record)
            elif isinstance(record, list):
                record_dict: Dict[str, Any] = {}
                for i, col in enumerate(schema):
                    if i < len(record):
                        value = record[i]
                        if isinstance(value, bytes):
                            value = value.decode("utf-8").rstrip("")
                        record_dict[col.name] = value
                dict_results.append(record_dict)
        return dict_results

    def create_table_from_file(
        self,
        table_name: str,
        file_path: str,
        index_column: str,
        index_type: Optional[IndexType],  # ahora puede ser None
    ) -> bool:
        """
        Crea una tabla a partir de un CSV, infiere el esquema y carga los registros.
        Si index_type es None, el selector elegirá la estructura por defecto (B+Tree antes que SEQ).
        Inserta en lotes para acelerar cargas grandes.
        """
        self._log_operation(f"LOAD FROM FILE {file_path} → {table_name}")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo '{file_path}' no encontrado")

        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
            sample: List[List[str]] = []
            for _ in range(64):
                try:
                    sample.append(next(reader))
                except StopIteration:
                    break

        def infer_type(values: List[str]) -> DataType:
            vals = [v for v in values if v not in (None, "")]
            def is_int(s: str) -> bool:
                try:
                    int(s); return True
                except Exception:
                    return False
            def is_float(s: str) -> bool:
                try:
                    float(s); return True
                except Exception:
                    return False
            if vals and all(is_int(v) for v in vals):
                return DataType.INT
            if vals and all(is_float(v) for v in vals):
                return DataType.FLOAT
            return DataType.VARCHAR

        col_samples = list(zip(*sample)) if sample else [[] for _ in headers]
        columns: List[Column] = []
        for i, name in enumerate(headers):
            values = list(col_samples[i]) if i < len(col_samples) else []
            dt = infer_type(values)
            is_key = (name == index_column) or (name.strip('"').strip("'") == index_column.strip('"').strip("'"))
            ix = index_type if is_key else None
            columns.append(Column(name=name, data_type=dt, size=None, is_key=is_key, index_type=ix))

        self.create_table(table_name, columns)

        self._insert_csv_in_batches(table_name, file_path, columns, batch_size=5000)
        self._log_operation(f"LOAD OK {table_name} (insertado en lotes)")
        return True

    def _cast_value(self, s: Optional[str], dt: DataType) -> Any:
        if s is None or s == "":
            return None
        if dt == DataType.INT:
            try:
                return int(s)
            except Exception:
                return 0
        if dt == DataType.FLOAT:
            try:
                return float(s)
            except Exception:
                return 0.0
        return s

    def _insert_csv_in_batches(self, table_name: str, file_path: str, cols: List[Column], batch_size: int = 5000) -> None:
        import itertools
        with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # header
            while True:
                chunk = list(itertools.islice(reader, batch_size))
                if not chunk:
                    break
                rows = [
                    [self._cast_value(row[i] if i < len(row) else None, cols[i].data_type) for i in range(len(cols))]
                    for row in chunk
                ]
                self.add_many(table_name, rows)

def create_unified_adapter(data_dir: str = "data") -> UnifiedDatabaseAdapter:
    return UnifiedDatabaseAdapter(data_dir)