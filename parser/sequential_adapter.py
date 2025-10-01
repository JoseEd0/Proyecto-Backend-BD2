"""
Database Adapter para Sequential File
Proyecto CS2702 - Base de Datos 2 UTEC

Este adaptador conecta el Sequential File con el Parser SQL,
implementando la interfaz esperada por QueryTranslator.

Proporciona:
- Gestión de múltiples tablas Sequential
- Traducción de operaciones SQL a operaciones Sequential
- Manejo de tipos de índice
- Log de operaciones
"""

import os
import csv
from typing import Dict, List, Any, Optional
from pathlib import Path

# Importar Sequential File
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from Sequential_Struct.sequential_file import SequentialFile
from parser.ast_nodes import Column, DataType, IndexType


class SequentialDatabaseAdapter:
    """
    Adaptador que conecta el Parser SQL con Sequential Files

    Maneja:
    - Creación de tablas con Sequential File
    - Operaciones CRUD (Create, Read, Update, Delete)
    - Búsquedas exactas y por rango
    - Carga desde CSV
    """

    def __init__(self, data_dir: str = "Sequential_Struct/tables"):
        """
        Inicializa el adaptador

        Args:
            data_dir: Directorio donde se almacenarán las tablas
        """
        self.data_dir = data_dir
        self.tables: Dict[str, SequentialFile] = {}
        self.schemas: Dict[str, List[Column]] = {}
        self.operations_log: List[str] = []

        # Crear directorio si no existe
        os.makedirs(data_dir, exist_ok=True)

    def _log_operation(self, operation: str):
        """Registra una operación en el log"""
        self.operations_log.append(operation)
        print(f"📝 {operation}")

    def _convert_column_to_struct_format(self, column: Column) -> str:
        """
        Convierte un Column del parser a formato struct

        Returns:
            Formato struct (ej: 'i', '50s', 'f', etc.)
        """
        if column.data_type == DataType.INT:
            return "i"
        elif column.data_type == DataType.FLOAT:
            return "f"
        elif column.data_type == DataType.VARCHAR:
            # VARCHAR[N] -> 'Ns'
            size = column.size if column.size else 50
            return f"{size}s"
        elif column.data_type == DataType.DATE:
            # DATE como string de fecha YYYY-MM-DD (10 caracteres)
            return "10s"
        elif column.data_type == DataType.ARRAY_FLOAT:
            # Para arrays (usado en RTree), podríamos usar una representación fija
            # Por ahora, asumimos array de 2 floats para coordenadas (2*4=8 bytes)
            return "8s"  # Placeholder
        else:
            return "i"  # Default

    def _get_table_files(self, table_name: str) -> tuple[str, str]:
        """Retorna las rutas de los archivos de índice y datos para una tabla"""
        index_file = os.path.join(self.data_dir, f"{table_name}_index.bin")
        data_file = os.path.join(self.data_dir, f"{table_name}_data.bin")
        return index_file, data_file

    def create_table(self, table_name: str, schema: List[Column]) -> bool:
        """
        Crea una nueva tabla con Sequential File

        Args:
            table_name: Nombre de la tabla
            schema: Lista de columnas

        Returns:
            True si se creó correctamente
        """
        try:
            # Verificar si ya existe
            if table_name in self.tables:
                print(f"❌ La tabla '{table_name}' ya existe")
                return False

            # Encontrar la columna KEY
            key_column = None
            for col in schema:
                if col.is_key:
                    key_column = col
                    break

            if not key_column:
                print(f"❌ No se especificó columna KEY para la tabla '{table_name}'")
                return False

            # Construir table_format para RegistroType
            table_format = {}
            for col in schema:
                format_str = self._convert_column_to_struct_format(col)
                table_format[col.name] = format_str

            # Obtener rutas de archivos
            index_file, data_file = self._get_table_files(table_name)

            # Crear Sequential File
            sequential = SequentialFile(
                table_format=table_format,
                name_key=key_column.name,
                index_file=index_file,
                data_file=data_file,
                max_aux_size=100,
                force_create=True,
            )

            # Guardar
            self.tables[table_name] = sequential
            self.schemas[table_name] = schema

            self._log_operation(f"CREATE TABLE {table_name} (columns={len(schema)})")
            return True

        except Exception as e:
            print(f"❌ Error creando tabla '{table_name}': {e}")
            return False

    def create_table_from_file(
        self, table_name: str, file_path: str, index_column: str, index_type: IndexType
    ) -> bool:
        """
        Crea una tabla desde un archivo CSV

        Args:
            table_name: Nombre de la tabla
            file_path: Ruta del archivo CSV
            index_column: Nombre de la columna para el índice
            index_type: Tipo de índice (para Sequential usamos SEQ)

        Returns:
            True si se creó correctamente
        """
        try:
            # Verificar que el archivo existe
            if not os.path.exists(file_path):
                print(f"❌ Archivo '{file_path}' no encontrado")
                return False

            # Leer CSV para inferir esquema
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                first_row = next(reader)

            # Inferir tipos de datos
            schema = []
            for i, header in enumerate(headers):
                value = first_row[i]

                # Inferir tipo
                try:
                    int(value)
                    data_type = DataType.INT
                    format_str = "i"
                except:
                    try:
                        float(value)
                        data_type = DataType.FLOAT
                        format_str = "f"
                    except:
                        data_type = DataType.VARCHAR
                        format_str = "100s"  # Default VARCHAR[100]

                is_key = header == index_column
                column = Column(name=header, data_type=data_type, is_key=is_key)
                schema.append(column)

            # Crear tabla
            if not self.create_table(table_name, schema):
                return False

            # Cargar datos del CSV
            sequential = self.tables[table_name]
            count = 0

            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header

                for row in reader:
                    try:
                        sequential.insert(row)
                        count += 1
                    except Exception as e:
                        print(f"⚠️  Error insertando fila {count+1}: {e}")

            self._log_operation(
                f"LOAD FROM FILE {file_path} INTO {table_name} ({count} records)"
            )
            return True

        except Exception as e:
            print(f"❌ Error cargando desde archivo: {e}")
            return False

    def _records_to_dicts(
        self, table_name: str, records: List[List[Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convierte registros (listas) a diccionarios con nombres de columnas

        Args:
            table_name: Nombre de la tabla
            records: Lista de registros como listas

        Returns:
            Lista de registros como diccionarios
        """
        if table_name not in self.schemas:
            return records

        schema = self.schemas[table_name]
        dict_results = []

        for record in records:
            if isinstance(record, list):
                record_dict = {}
                for i, col in enumerate(schema):
                    if i < len(record):
                        value = record[i]
                        # Decodificar bytes a string si es necesario
                        if isinstance(value, bytes):
                            value = value.decode("utf-8").rstrip("\x00")
                        record_dict[col.name] = value
                dict_results.append(record_dict)
            elif isinstance(record, dict):
                dict_results.append(record)

        return dict_results

    def search(self, table_name: str, column: str, key: Any) -> List[Dict[str, Any]]:
        """
        Búsqueda exacta por clave

        Args:
            table_name: Nombre de la tabla
            column: Nombre de la columna (debe ser la KEY)
            key: Valor a buscar

        Returns:
            Lista de registros que coinciden (como diccionarios)
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return []

        sequential = self.tables[table_name]
        result = sequential.search(key)

        self._log_operation(f"SEARCH {table_name} WHERE {column} = {key}")

        raw_results = [result] if result is not None else []
        return self._records_to_dicts(table_name, raw_results)

    def range_search(
        self, table_name: str, column: str, begin_key: Any, end_key: Any
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda por rango

        Args:
            table_name: Nombre de la tabla
            column: Nombre de la columna
            begin_key: Valor inicial del rango
            end_key: Valor final del rango

        Returns:
            Lista de registros en el rango (como diccionarios)
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return []

        sequential = self.tables[table_name]
        results = sequential.search_range(begin_key, end_key)

        self._log_operation(
            f"RANGE SEARCH {table_name} WHERE {column} BETWEEN {begin_key} AND {end_key}"
        )

        return self._records_to_dicts(table_name, results)

    def spatial_range_search(
        self, table_name: str, column: str, point: List[float], radius: float
    ) -> List[Any]:
        """
        Búsqueda espacial (no soportada en Sequential - scan completo)

        Args:
            table_name: Nombre de la tabla
            column: Nombre de la columna
            point: Punto central [lat, lon]
            radius: Radio de búsqueda

        Returns:
            Lista de registros dentro del radio
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return []

        # Sequential File no es óptimo para búsquedas espaciales
        # Esto requeriría un RTree - por ahora retornamos error
        print(f"⚠️  Búsqueda espacial no optimizada en Sequential File")
        self._log_operation(f"SPATIAL SEARCH {table_name} (not optimized)")

        return []

    def add(self, table_name: str, record: List[Any]) -> bool:
        """
        Inserta un registro

        Args:
            table_name: Nombre de la tabla
            record: Lista de valores del registro

        Returns:
            True si se insertó correctamente
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return False

        sequential = self.tables[table_name]
        success = sequential.insert(record)

        if success:
            self._log_operation(f"INSERT INTO {table_name} VALUES {record}")

        return success

    def remove(self, table_name: str, column: str, key: Any) -> bool:
        """
        Elimina un registro por clave

        Args:
            table_name: Nombre de la tabla
            column: Nombre de la columna KEY
            key: Valor de la clave a eliminar

        Returns:
            True si se eliminó correctamente
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return False

        sequential = self.tables[table_name]
        success = sequential.delete(key)

        if success:
            self._log_operation(f"DELETE FROM {table_name} WHERE {column} = {key}")

        return success

    def scan_all(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Scan completo de la tabla

        Args:
            table_name: Nombre de la tabla

        Returns:
            Lista de todos los registros como diccionarios
        """
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return []

        sequential = self.tables[table_name]
        results = sequential.scan_all()

        self._log_operation(f"SCAN ALL {table_name} ({len(results)} records)")

        # Convertir a diccionarios usando el helper
        return self._records_to_dicts(table_name, results)

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de una tabla"""
        if table_name not in self.schemas:
            return None

        schema = self.schemas[table_name]
        columns = []

        for col in schema:
            columns.append(
                {
                    "name": col.name,
                    "type": (
                        col.data_type.value
                        if hasattr(col.data_type, "value")
                        else str(col.data_type)
                    ),
                    "is_key": col.is_key,
                    "index_type": (
                        col.index_type.value
                        if col.index_type and hasattr(col.index_type, "value")
                        else None
                    ),
                }
            )

        return {
            "name": table_name,
            "columns": columns,
            "record_count": (
                self.tables[table_name].count() if table_name in self.tables else 0
            ),
        }

    def list_tables(self) -> List[str]:
        """Lista todas las tablas"""
        return list(self.tables.keys())

    def get_operations_log(self) -> List[str]:
        """Retorna el log de operaciones"""
        return self.operations_log.copy()

    def print_table(self, table_name: str):
        """Imprime el contenido de una tabla"""
        if table_name not in self.tables:
            print(f"❌ Tabla '{table_name}' no existe")
            return

        sequential = self.tables[table_name]
        sequential.print_all()

    def __repr__(self) -> str:
        return f"SequentialDatabaseAdapter(tables={len(self.tables)})"


# Función helper
def create_sequential_adapter(
    data_dir: str = "Sequential_Struct/tables",
) -> SequentialDatabaseAdapter:
    """
    Crea un adaptador de base de datos Sequential

    Args:
        data_dir: Directorio para almacenar tablas

    Returns:
        Instancia de SequentialDatabaseAdapter
    """
    return SequentialDatabaseAdapter(data_dir)
