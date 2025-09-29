"""
Módulo para manejo de registros y tipos de datos
Proyecto CS2702 - Base de Datos 2 UTEC

Este módulo proporciona la clase RegistroType que permite:
- Definir esquemas de registros con diferentes tipos de datos
- Serializar/deserializar registros a formato binario
- Validar y convertir tipos de datos
- Extraer claves primarias de registros
"""

import struct
import math
from typing import Dict, List, Any, Union


class RegistroType:
    """
    Clase para manejar el formato y serialización de registros

    Tipos soportados:
    - 'i': int (4 bytes)
    - 'q': long long (8 bytes)
    - 'Q': unsigned long long (8 bytes)
    - 'f': float (4 bytes)
    - 'd': double (8 bytes)
    - 'b': byte (1 byte)
    - '?': bool (1 byte)
    - 'Ns': string de longitud N (N bytes)

    Ejemplo:
        table_format = {
            "id": "i",           # entero de 4 bytes
            "nombre": "50s",     # string de 50 bytes
            "precio": "f",       # float de 4 bytes
            "activo": "?"        # bool de 1 byte
        }
        rt = RegistroType(table_format, "id")
    """

    def __init__(self, table_format: Dict[str, str], name_key: str):
        """
        Inicializa el tipo de registro

        Args:
            table_format: Diccionario con nombre_campo -> tipo_formato
            name_key: Nombre del campo que es clave primaria
        """
        self.table_format = table_format
        self.name_key = name_key
        self.field_names = list(table_format.keys())
        self.format_key = table_format[name_key]

        # Calcular formato struct y tamaño
        self.struct_format = self._build_struct_format()
        self.size = struct.calcsize(self.struct_format)

    def _build_struct_format(self) -> str:
        """Construye el formato struct para pack/unpack"""
        format_parts = []
        for field_type in self.table_format.values():
            format_parts.append(field_type)
        return ''.join(format_parts)

    def correct_format(self, record: List[Any]) -> List[Any]:
        """
        Convierte los valores del registro al tipo correcto

        Args:
            record: Lista de valores del registro

        Returns:
            Lista de valores con tipos correctos
        """
        if len(record) != len(self.field_names):
            raise ValueError(f"Se esperaban {len(self.field_names)} campos, se recibieron {len(record)}")

        corrected = []
        for i, (field_name, field_type) in enumerate(self.table_format.items()):
            value = record[i]
            corrected_value = self._convert_value(value, field_type)
            corrected.append(corrected_value)

        return corrected

    def _convert_value(self, value: Any, field_type: str) -> Any:
        """Convierte un valor al tipo especificado"""
        if value is None:
            return self._get_null_value(field_type)

        # Tipos enteros
        if field_type in ('i', 'q', 'Q', 'b'):
            return int(value)

        # Tipos flotantes
        elif field_type in ('f', 'd'):
            return float(value)

        # Bool
        elif field_type == '?':
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'si', 'y')
            return bool(value)

        # String
        elif 's' in field_type:
            max_length = int(field_type[:-1])
            if isinstance(value, bytes):
                return value[:max_length]
            else:
                return str(value).encode('utf-8')[:max_length]

        return value

    def _get_null_value(self, field_type: str) -> Any:
        """Retorna el valor nulo para un tipo de campo"""
        if field_type in ('i', 'q', 'Q'):
            return -2147483648  # Valor sentinela para NULL
        elif field_type in ('f', 'd'):
            return float('nan')
        elif field_type in ('b', '?'):
            return -128
        elif 's' in field_type:
            max_length = int(field_type[:-1])
            return b'\x00' * max_length
        else:
            return 0

    def to_bytes(self, record: List[Any]) -> bytes:
        """
        Serializa un registro a bytes

        Args:
            record: Lista de valores del registro

        Returns:
            Bytes del registro serializado
        """
        # Preparar valores para empaquetado
        values_to_pack = []
        for i, (field_name, field_type) in enumerate(self.table_format.items()):
            value = record[i]

            # Manejar strings
            if 's' in field_type:
                max_length = int(field_type[:-1])
                if isinstance(value, str):
                    value = value.encode('utf-8')
                if isinstance(value, bytes):
                    # Asegurar que tenga el tamaño correcto
                    value = value[:max_length].ljust(max_length, b'\x00')
                else:
                    value = b'\x00' * max_length

            values_to_pack.append(value)

        return struct.pack(self.struct_format, *values_to_pack)

    def from_bytes(self, data: bytes) -> List[Any]:
        """
        Deserializa bytes a un registro

        Args:
            data: Bytes del registro

        Returns:
            Lista de valores del registro
        """
        if len(data) < self.size:
            raise ValueError(f"Se esperaban al menos {self.size} bytes, se recibieron {len(data)}")

        unpacked = struct.unpack(self.struct_format, data[:self.size])

        # Procesar valores
        record = []
        for i, (field_name, field_type) in enumerate(self.table_format.items()):
            value = unpacked[i]

            # Procesar strings
            if 's' in field_type:
                if isinstance(value, bytes):
                    value = value.decode('utf-8').rstrip('\x00')

            # Detectar valores nulos
            elif field_type in ('i', 'q', 'Q') and value == -2147483648:
                value = None
            elif field_type in ('f', 'd') and math.isnan(value):
                value = None
            elif field_type in ('b', '?') and value == -128:
                value = None

            record.append(value)

        return record

    def get_key(self, record: List[Any]) -> Any:
        """
        Extrae el valor de la clave primaria del registro

        Args:
            record: Lista de valores del registro

        Returns:
            Valor de la clave primaria
        """
        key_index = self.field_names.index(self.name_key)
        return record[key_index]

    def get_field_value(self, record: List[Any], field_name: str) -> Any:
        """
        Extrae el valor de un campo específico

        Args:
            record: Lista de valores del registro
            field_name: Nombre del campo a extraer

        Returns:
            Valor del campo
        """
        if field_name not in self.field_names:
            raise ValueError(f"Campo '{field_name}' no existe en el esquema")

        field_index = self.field_names.index(field_name)
        return record[field_index]

    def create_empty_record(self) -> List[Any]:
        """Crea un registro vacío con valores nulos"""
        record = []
        for field_type in self.table_format.values():
            record.append(self._get_null_value(field_type))
        return record

    def _print(self, record: List[Any]):
        """
        Imprime un registro de forma legible

        Args:
            record: Lista de valores del registro
        """
        # Evitar imprimir los últimos 2 campos si son punteros (sig, lugar)
        num_fields = len(self.field_names)

        print("{ ", end="")
        for i, field_name in enumerate(self.field_names):
            if i >= len(record):
                break
            value = record[i]

            # Formatear strings
            if isinstance(value, bytes):
                value = value.decode('utf-8').rstrip('\x00')

            print(f"{field_name}: {value}", end="")
            if i < num_fields - 1 and i < len(record) - 1:
                print(", ", end="")

        # Imprimir punteros si existen (últimos 2 elementos)
        if len(record) > num_fields:
            sig = record[-2]
            lugar = record[-1]
            print(f" | next: {sig}, lugar: {lugar}", end="")

        print(" }")

    def __repr__(self) -> str:
        """Representación del tipo de registro"""
        return f"RegistroType(fields={self.field_names}, key={self.name_key}, size={self.size})"


# Funciones auxiliares
def create_registro_type(table_format: Dict[str, str], name_key: str) -> RegistroType:
    """
    Función helper para crear un RegistroType

    Args:
        table_format: Diccionario con nombre_campo -> tipo_formato
        name_key: Nombre del campo que es clave primaria

    Returns:
        Instancia de RegistroType
    """
    return RegistroType(table_format, name_key)
