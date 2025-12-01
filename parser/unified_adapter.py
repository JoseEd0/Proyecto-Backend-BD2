"""
Adaptador Unificado de Base de Datos - Soporta todas las estructuras
Proyecto CS2702 - Base de Datos 2 UTEC

Este adaptador integra:
- Sequential File: Para datos ordenados y búsquedas secuenciales
- B+ Tree: Para búsquedas rápidas y rangos en claves numéricas
- ISAM: Para archivos grandes estáticos con pocas actualizaciones
- Extendible Hashing: Para búsquedas por igualdad muy rápidas
- R-Tree: Para consultas espaciales (coordenadas geográficas)
- Bag of Words: Para búsquedas de texto completo

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
- CREATE TABLE ... USING INDEX BOW('columna')
"""
import os
import sys
import csv
import pickle
from typing import Dict, List, Any, Optional
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

HAS_SEQUENTIAL = False
HAS_BTREE = False
HAS_ISAM = False
HAS_HASH = False
HAS_RTREE = False
HAS_BOW = False

try:
    from Sequential_Struct.sequential_file import SequentialFile  # type: ignore
    HAS_SEQUENTIAL = True
except Exception as e:
    print(f"[WARNING] Sequential File no disponible: {e}")

try:
    from b_plus_tree.bplustree import BPlusTree  # type: ignore
    HAS_BTREE = True
except Exception as e:
    print(f"[WARNING] B+ Tree no disponible: {e}")

try:
    from ISAM.ISAM import create_isam_index, ISAMIndex  # type: ignore
    HAS_ISAM = True
except Exception:
    try:
        from ISAM import create_isam_index, ISAMIndex  # type: ignore
        HAS_ISAM = True
    except Exception as e:
        print(f"[WARNING] ISAM no disponible: {e}")

try:
    from extendible_hashing.extendible_hashing import DiskExtendibleHashing  # type: ignore
    HAS_HASH = True
except Exception as e:
    print(f"[WARNING] Extendible Hashing no disponible: {e}")

try:
    from rtree_impl import RTreeIndex, Point, SpatialRecord, create_record  # type: ignore
    HAS_RTREE = True
except Exception:
    try:
        from Rtree.rtree_impl import RTreeIndex, Point, SpatialRecord, create_record  # type: ignore
        HAS_RTREE = True
    except Exception as e:
        print(f"[WARNING] R-Tree no disponible: {e}")

try:
    from inverted_index.indexer import SPIMIIndexer
    from inverted_index.query_engine import QueryEngine
    from inverted_index.preprocessing import TextPreprocessor
    HAS_BOW = True
except Exception as e:
    print(f"[WARNING] Bag of Words no disponible: {e}")

try:
    from parser.ast_nodes import Column, DataType, IndexType  # type: ignore
except Exception as e1:
    try:
        from ast_nodes import Column, DataType, IndexType  # type: ignore
    except Exception as e2:
        print(f"[ERROR] Could not import ast_nodes: {e1}, {e2}")
        raise


class StructureType:
    SEQUENTIAL = "sequential"
    BTREE = "btree"
    ISAM = "isam"
    HASH = "hash"
    RTREE = "rtree"
    BOW = "bow"


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
                IndexType.BOW:   (StructureType.BOW, HAS_BOW),
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
            StructureType.SEQUENTIAL: "[OK] Datos ordenados, búsquedas secuenciales y por rango",
            StructureType.BTREE: "[FAST] Búsquedas muy rápidas, excelente para rangos, balanceado",
            StructureType.ISAM: "[STATIC] Tablas grandes estáticas, principalmente lectura",
            StructureType.HASH: "[FAST] Búsquedas exactas ultra rápidas (no soporta rangos)",
            StructureType.RTREE: "[SPATIAL] Consultas espaciales, coordenadas geográficas",
            StructureType.BOW: "[TEXT] Búsqueda de texto completo (Full-Text Search)",
        }


class UnifiedDatabaseAdapter:
    """Adaptador unificado que orquesta las distintas estructuras físicas."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        for structure in [StructureType.SEQUENTIAL, StructureType.BTREE, StructureType.ISAM, StructureType.HASH, StructureType.RTREE, StructureType.BOW]:
            (self.data_dir / structure).mkdir(parents=True, exist_ok=True)
        self.tables: Dict[str, Any] = {}
        self.table_structures: Dict[str, str] = {}
        self.table_schemas: Dict[str, List[Column]] = {}
        self.operations_log: List[str] = []

    def _log_operation(self, operation: str) -> None:
        self.operations_log.append(operation)
        # print(f"[LOG] {operation}") # Commented out to reduce noise

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

            # Check if any column requests BOW
            if any(getattr(col, "index_type", None) == IndexType.BOW for col in schema):
                structure_type = StructureType.BOW
            else:
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
            elif structure_type == StructureType.BOW:
                self._create_bow_table(table_name, schema, key_column)
            else:
                raise ValueError(f"Estructura '{structure_type}' no soportada")

            self.table_structures[table_name] = structure_type
            self.table_schemas[table_name] = schema
            return True
        except Exception as e:
            self._log_operation(f"[ERROR] Error creando tabla '{table_name}': {e}")
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

    def _create_bow_table(self, table_name: str, schema: List[Column], key_column: Column) -> None:
        if not HAS_BOW:
            raise ImportError("Bag of Words no está disponible")
        
        index_dir = str(self.data_dir / StructureType.BOW / table_name)
        os.makedirs(index_dir, exist_ok=True)
        
        indexer = SPIMIIndexer(output_dir=index_dir)
        self.tables[table_name] = indexer

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
                
                # Ensure coordinates are floats
                coordinates = [float(x) for x in coordinates]
                
                # Create SpatialRecord
                spatial_record = create_record(record_id, coordinates, record)
                structure.insert(spatial_record)
                success = True

            elif structure_type == StructureType.BOW:
                # Find content column
                content_index = next((i for i, col in enumerate(schema) if getattr(col, "index_type", None) == IndexType.BOW), None)
                if content_index is None:
                    # Fallback: look for VARCHAR
                    content_index = next((i for i, col in enumerate(schema) if col.data_type == DataType.VARCHAR), None)
                
                if content_index is None:
                     raise ValueError("BOW requiere una columna de texto")

                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                doc_id = record[key_index]
                text = record[content_index]
                
                # Tokenize
                try:
                    preprocessor = TextPreprocessor()
                    tokens = preprocessor.preprocess(text)
                    # self._log_operation(f"[DEBUG] Text: '{text}' -> Tokens: {tokens}")
                except Exception as e:
                    self._log_operation(f"[WARNING] Error preprocesando texto: {e}")
                    tokens = text.split() # Fallback

                # IMPORTANT: We need to persist the record for retrieval!
                # Let's use a simple pickle file in the index dir for raw data
                index_dir = Path(self.data_dir / StructureType.BOW / table_name)
                data_storage_path = index_dir / "data_storage.pkl"
                
                # Load existing storage
                if not hasattr(structure, "_data_storage"):
                    if data_storage_path.exists():
                        with open(data_storage_path, "rb") as f:
                            structure._data_storage = pickle.load(f)
                    else:
                        structure._data_storage = {}
                
                structure._data_storage[doc_id] = record
                
                # Save storage
                with open(data_storage_path, "wb") as f:
                    pickle.dump(structure._data_storage, f)
                
                # Add to index
                if hasattr(structure, "add_document"):
                    structure.add_document(doc_id, tokens)
                    
                    # FORCE FLUSH/MERGE for immediate consistency (inefficient but needed for tests)
                    structure.write_block_to_disk()
                    structure.merge_blocks()
                    
                    # Compute TF-IDF
                    total_docs = len(structure._data_storage) if hasattr(structure, "_data_storage") else 1
                    structure.compute_tfidf_and_norms(total_docs)
                else:
                    pass
                
                success = True

            else:
                success = False

            if success:
                self._log_operation(f"INSERT INTO {table_name} VALUES {record}")
            return success
        except Exception as e:
            self._log_operation(f"[ERROR] Error insertando en '{table_name}': {e}")
            raise

    def add_many(self, table_name: str, rows: List[List[Any]]) -> None:
        for row in rows:
            self.add(table_name, row)

    def search(self, table_name: str, column: str, key: Any) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        
        try:
            raw_results = []
            if structure_type == StructureType.SEQUENTIAL:
                raw_results = structure.search(key)

            elif structure_type == StructureType.BTREE:
                raw_results = structure.search(key)
                if not isinstance(raw_results, list):
                    raw_results = [raw_results] if raw_results else []

            elif structure_type == StructureType.ISAM:
                raw_results = structure.search(key)
                if not isinstance(raw_results, list):
                    raw_results = [raw_results] if raw_results else []

            elif structure_type == StructureType.HASH:
                result = structure.search(str(key))
                raw_results = [result] if result else []

            elif structure_type == StructureType.RTREE:
                # Search by ID?
                # RTree search usually by coordinates.
                # If searching by ID, we might need to scan or use a secondary index.
                # For now, scan all
                self._log_operation("[WARNING] RTree search by ID not optimized")
                all_records = self._scan_all_raw(table_name)
                # Filter by key
                # Assuming key is the ID
                raw_results = [r for r in all_records if str(r[0]) == str(key)] # simplistic assumption

            elif structure_type == StructureType.BOW:
                # Search by keyword (content) or ID?
                # If column is the content column, use index.
                # If column is ID, use data storage.
                
                schema = self.table_schemas[table_name]
                col_obj = next((c for c in schema if c.name == column), None)
                
                if col_obj and getattr(col_obj, "index_type", None) == IndexType.BOW:
                    # Search by keyword
                    query_engine = QueryEngine(structure.output_dir) # structure is indexer
                    # QueryEngine might need to be initialized with the index dir
                    # Assuming QueryEngine(index_dir) works
                    
                    # search(query) returns list of (doc_id, score)
                    search_results = query_engine.search(str(key))
                    
                    doc_ids = [r[0] for r in search_results]
                    
                    # Retrieve records
                    index_dir = Path(self.data_dir / StructureType.BOW / table_name)
                    data_storage_path = index_dir / "data_storage.pkl"
                    if not hasattr(structure, "_data_storage"):
                        if data_storage_path.exists():
                            with open(data_storage_path, "rb") as f:
                                structure._data_storage = pickle.load(f)
                        else:
                            structure._data_storage = {}
                    
                    raw_results = []
                    for did in doc_ids:
                        if did in structure._data_storage:
                            raw_results.append(structure._data_storage[did])
                            
                else:
                    # Search by ID
                    if hasattr(structure, "_data_storage") and key in structure._data_storage:
                        raw_results = [structure._data_storage[key]]
                    else:
                        raw_results = []

            self._log_operation(f"SEARCH {table_name} WHERE {column} = {key}")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"[ERROR] Error buscando en '{table_name}': {e}")
            raise

    def range_search(self, table_name: str, column: str, begin_key: Any, end_key: Any) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        
        try:
            raw_results = []
            if structure_type == StructureType.SEQUENTIAL:
                raw_results = structure.range_search(begin_key, end_key)

            elif structure_type == StructureType.BTREE:
                raw_results = structure.range_search(begin_key, end_key)

            elif structure_type == StructureType.ISAM:
                raw_results = structure.range_search(int(begin_key), int(end_key))

            elif structure_type == StructureType.HASH:
                self._log_operation("[WARNING] Hash no soporta RANGE, haciendo scan completo")
                raw_results = self._scan_all_raw(table_name)
                schema = self.table_schemas[table_name]
                key_index = next(i for i, col in enumerate(schema) if col.is_key)
                # Filter
                filtered = []
                for r in raw_results:
                    val = r[key_index]
                    if begin_key <= val <= end_key:
                        filtered.append(r)
                raw_results = filtered

            elif structure_type == StructureType.RTREE:
                self._log_operation("[WARNING] RTree range search (scalar) not optimized")
                # Similar fallback
                raw_results = []

            elif structure_type == StructureType.BOW:
                # Range search on ID?
                self._log_operation("[WARNING] BOW no soporta RANGE eficiente, haciendo scan completo")
                raw_results = self._scan_all_raw(table_name)
                # Filter by key range if applicable
                # ...

            self._log_operation(f"RANGE SEARCH {table_name} WHERE {column} BETWEEN {begin_key} AND {end_key}")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"[ERROR] Error en range_search de '{table_name}': {e}")
            raise

    def spatial_range_search(self, table_name: str, column: str, point: List[float], radius: float) -> List[Dict[str, Any]]:
        return self.spatial_search(table_name, column, point, radius)

    def spatial_search(self, table_name: str, column: str, point: List[float], radius: float) -> List[Dict[str, Any]]:
        if table_name not in self.tables:
            raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        
        try:
            if structure_type == StructureType.RTREE:
                # point is [x, y]
                # radius is float
                # RTree implementation might expect a rectangle or point+radius
                # Assuming range_search(center, radius) exists
                center = Point(point[0], point[1])
                results = structure.range_search(center, radius)
                raw_results = [r.data for r in results]
            else:
                self._log_operation(f"[WARNING] {structure_type.upper()} no está optimizado para spatial search")
                raw_results = []
            self._log_operation(f"SPATIAL SEARCH {table_name} WHERE {column} IN ({point}, {radius})")
            return self._records_to_dicts(table_name, raw_results)
        except Exception as e:
            self._log_operation(f"[ERROR] Error en spatial_search de '{table_name}': {e}")
            raise

    def remove(self, table_name: str, column: str, key: Any) -> bool:
        if table_name not in self.tables:
             raise ValueError(f"Tabla '{table_name}' no existe")
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        
        try:
            success = False
            if structure_type == StructureType.SEQUENTIAL:
                success = structure.delete(key)
            elif structure_type == StructureType.BTREE:
                success = structure.delete(key)
            elif structure_type == StructureType.ISAM:
                # ISAM delete?
                pass
            elif structure_type == StructureType.HASH:
                success = structure.remove(str(key))
            elif structure_type == StructureType.RTREE:
                # RTree delete by ID?
                # structure.delete(record) usually requires the record or ID+bounds
                pass
            elif structure_type == StructureType.BOW:
                 # Delete from storage
                 index_dir = Path(self.data_dir / StructureType.BOW / table_name)
                 data_storage_path = index_dir / "data_storage.pkl"
                 if hasattr(structure, "_data_storage") and key in structure._data_storage:
                     del structure._data_storage[key]
                     with open(data_storage_path, "wb") as f:
                         pickle.dump(structure._data_storage, f)
                     success = True
                 # Also need to remove from index? Hard in SPIMI/Inverted Index.
                 # Usually we just mark as deleted or ignore.
            
            if success:
                self._log_operation(f"DELETE FROM {table_name} WHERE {column} = {key}")
            return success
        except Exception as e:
            self._log_operation(f"[ERROR] Error eliminando de '{table_name}': {e}")
            raise

    def scan_all(self, table_name: str) -> List[Dict[str, Any]]:
        raw_results = self._scan_all_raw(table_name)
        return self._records_to_dicts(table_name, raw_results)

    def _scan_all_raw(self, table_name: str) -> List[Any]:
        if table_name not in self.tables:
            return []
        structure_type = self.table_structures[table_name]
        structure = self.tables[table_name]
        
        if structure_type == StructureType.SEQUENTIAL:
            return structure.scan()
        elif structure_type == StructureType.BTREE:
             # BTree scan?
             # Assuming it has a way to iterate
             # Or range search from min to max
             return [] # Implement if BTree supports it
        elif structure_type == StructureType.ISAM:
             return [] # Implement
        elif structure_type == StructureType.HASH:
             return structure.get_all()
        elif structure_type == StructureType.RTREE:
             return structure.scan()
        elif structure_type == StructureType.BOW:
             # Return all from storage
             index_dir = Path(self.data_dir / StructureType.BOW / table_name)
             data_storage_path = index_dir / "data_storage.pkl"
             if not hasattr(structure, "_data_storage"):
                if data_storage_path.exists():
                    with open(data_storage_path, "rb") as f:
                        structure._data_storage = pickle.load(f)
                else:
                    structure._data_storage = {}
             return list(structure._data_storage.values())
        return []

    def _records_to_dicts(self, table_name: str, records: List[Any]) -> List[Dict[str, Any]]:
        if not records:
            return []
        schema = self.table_schemas[table_name]
        result = []
        for r in records:
            if isinstance(r, dict):
                result.append(r)
            elif isinstance(r, (list, tuple)):
                row_dict = {}
                for i, col in enumerate(schema):
                    if i < len(r):
                        row_dict[col.name] = r[i]
                result.append(row_dict)
            else:
                # Handle other formats?
                pass
        return result

    def delete_table(self, table_name: str) -> bool:
        if table_name in self.tables:
            del self.tables[table_name]
            del self.table_structures[table_name]
            del self.table_schemas[table_name]
            self._log_operation(f"DROP TABLE {table_name}")
            return True
        return False

    def _cast_value(self, value: str, data_type: DataType) -> Any:
        try:
            if data_type == DataType.INT:
                return int(value)
            if data_type == DataType.FLOAT:
                return float(value)
            return value
        except:
            return value

    def _insert_csv_in_batches(self, table_name: str, csv_path: str, batch_size: int = 1000) -> None:
        if table_name not in self.table_schemas:
            raise ValueError(f"Tabla {table_name} no existe")
        
        schema = self.table_schemas[table_name]
        batch = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None) # Skip header if present?
            
            for row in reader:
                # Convert row types
                converted_row = []
                for i, val in enumerate(row):
                    if i < len(schema):
                        converted_row.append(self._cast_value(val, schema[i].data_type))
                
                batch.append(converted_row)
                
                if len(batch) >= batch_size:
                    self.add_many(table_name, batch)
                    batch = []
            
            if batch:
                self.add_many(table_name, batch)


def create_unified_adapter(data_dir: str = "data") -> UnifiedDatabaseAdapter:
    return UnifiedDatabaseAdapter(data_dir)