"""
Sequential File Optimizado - Versión Unificada con Índice
Proyecto CS2702 - Base de Datos 2 UTEC

Esta implementación combina lo mejor de ambas versiones anteriores:
- Usa índice separado para eficiencia (como Indice_Sequential_file.py)
- Mantiene archivo auxiliar para inserciones rápidas
- Búsqueda binaria en índice principal O(log n)
- Reconstrucción automática cuando aux se llena

ESTRUCTURA:
- index_file.bin: Índice ordenado (key + posición en heap)
  - Encabezado: [pos_root, num_data, num_aux] (12 bytes)
  - Registros índice: [key, pos_heap, next] (variable según tipo de key)

- data_file.bin: Heap file con datos completos (via Heap class)

VENTAJAS:
✓ Índice pequeño = más rápido
✓ Búsqueda binaria eficiente
✓ Separación índice/datos
✓ Fácil integración con parser y API
"""

import os
import struct
import math
import sys
from typing import List, Any, Dict, Optional, Tuple

# Importar dependencias
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from Utils.Registro import RegistroType
from Heap_struct.Heap import Heap

# Constantes
HEADER_SIZE = 12  # pos_root (4) + num_data (4) + num_aux (4)


class IndexRecord:
    """
    Registro del índice ordenado

    Attributes:
        key: Valor de la clave primaria
        pos: Posición del registro completo en el Heap
        next: Puntero al siguiente en la lista enlazada (-1: final, -2: eliminado)
    """

    def __init__(self, key: Any, pos: int, next: int = -1):
        self.key = key
        self.pos = pos
        self.next = next

    def to_bytes(self, format_key: str) -> bytes:
        """Serializa el índice a bytes"""
        # Preparar la clave
        key_to_pack = self.key

        if key_to_pack is None:
            # Valores sentinela para NULL
            if format_key in ('i', 'q', 'Q'):
                key_to_pack = -2147483648
            elif format_key in ('f', 'd'):
                key_to_pack = float('nan')
            elif format_key in ('b', '?'):
                key_to_pack = -128
            elif 's' in format_key:
                max_length = int(format_key[:-1])
                key_to_pack = b'\x00' * max_length
            else:
                key_to_pack = 0
        else:
            # Convertir según tipo
            if 's' in format_key and isinstance(key_to_pack, str):
                max_length = int(format_key[:-1])
                key_to_pack = key_to_pack.encode('utf-8')[:max_length].ljust(max_length, b'\x00')
            elif format_key in ('i', 'q', 'Q'):
                key_to_pack = int(key_to_pack)
            elif format_key in ('f', 'd'):
                key_to_pack = float(key_to_pack)
            elif format_key in ('b', '?'):
                key_to_pack = bool(key_to_pack)

        # Empaquetar: key + pos + next
        format_str = f'{format_key}ii'
        return struct.pack(format_str, key_to_pack, self.pos, self.next)

    @classmethod
    def from_bytes(cls, data: bytes, format_key: str) -> 'IndexRecord':
        """Deserializa bytes a IndexRecord"""
        format_str = f'{format_key}ii'
        unpacked = struct.unpack(format_str, data)

        key = unpacked[0]
        pos = unpacked[1]
        next_pos = unpacked[2]

        # Procesar key según tipo
        if format_key in ('i', 'q', 'Q'):
            key = int(key) if key != -2147483648 else None
        elif format_key in ('f', 'd'):
            key = float(key) if not math.isnan(key) else None
        elif format_key in ('b', '?'):
            key = bool(key) if key != -128 else None
        elif 's' in format_key:
            max_length = int(format_key[:-1])
            if isinstance(key, bytes):
                key = key.decode('utf-8').rstrip('\x00') if key != b'\x00' * max_length else None

        return cls(key, pos, next_pos)

    def __repr__(self) -> str:
        return f"IndexRecord(key={self.key}, pos={self.pos}, next={self.next})"


class SequentialFile:
    """
    Sequential File Optimizado con Índice

    Proporciona:
    - Búsqueda O(log n) en índice principal
    - Inserción rápida en auxiliar
    - Búsqueda por rango eficiente
    - Reconstrucción automática
    """

    def __init__(self,
                 table_format: Dict[str, str],
                 name_key: str,
                 index_file: str = 'Sequential_Struct/sequential_index.bin',
                 data_file: str = 'Sequential_Struct/sequential_data.bin',
                 max_aux_size: int = 100,
                 force_create: bool = False):
        """
        Inicializa el Sequential File

        Args:
            table_format: Formato de campos {nombre: tipo}
            name_key: Nombre del campo clave primaria
            index_file: Ruta del archivo de índice
            data_file: Ruta del archivo de datos (Heap)
            max_aux_size: Tamaño máximo del área auxiliar antes de reconstruir
            force_create: Si True, crea archivos nuevos
        """
        self.index_file = index_file
        self.data_file = data_file
        self.RT = RegistroType(table_format, name_key)
        self.format_key = table_format[name_key]
        self.max_aux_size = max_aux_size

        # Calcular tamaño del índice
        format_str = f'{self.format_key}ii'
        self.index_record_size = struct.calcsize(format_str)

        # Crear directorios
        os.makedirs(os.path.dirname(index_file), exist_ok=True)
        os.makedirs(os.path.dirname(data_file), exist_ok=True)

        # Inicializar archivos
        if force_create:
            if os.path.exists(index_file):
                os.remove(index_file)
            if os.path.exists(data_file):
                os.remove(data_file)

        self._initialize_files()

        # Heap para datos
        self.heap = Heap(table_format, name_key, data_file, force_create)

    def _initialize_files(self):
        """Inicializa archivos con encabezados"""
        # Índice
        if not os.path.exists(self.index_file):
            with open(self.index_file, 'wb') as f:
                # Encabezado: pos_root=-1, num_data=0, num_aux=0
                f.write(struct.pack('iii', -1, 0, 0))

        # Datos (se inicializa via Heap)

    # === MANEJO DE ENCABEZADO ===

    def _read_header(self) -> Tuple[int, int, int]:
        """Lee encabezado del índice: (pos_root, num_data, num_aux)"""
        with open(self.index_file, 'rb') as f:
            header = f.read(HEADER_SIZE)
            return struct.unpack('iii', header)

    def _write_header(self, pos_root: int, num_data: int, num_aux: int):
        """Escribe encabezado del índice"""
        with open(self.index_file, 'r+b') as f:
            f.seek(0)
            f.write(struct.pack('iii', pos_root, num_data, num_aux))

    # === MANEJO DE REGISTROS DE ÍNDICE ===

    def _read_index(self, pos: int) -> IndexRecord:
        """Lee un registro de índice en posición específica"""
        with open(self.index_file, 'rb') as f:
            offset = HEADER_SIZE + pos * self.index_record_size
            f.seek(offset)
            data = f.read(self.index_record_size)
            return IndexRecord.from_bytes(data, self.format_key)

    def _write_index(self, pos: int, index_record: IndexRecord):
        """Escribe un registro de índice en posición específica"""
        with open(self.index_file, 'r+b') as f:
            offset = HEADER_SIZE + pos * self.index_record_size
            f.seek(offset)
            f.write(index_record.to_bytes(self.format_key))

    def _append_index(self, index_record: IndexRecord) -> int:
        """Agrega un registro de índice al final"""
        pos_root, num_data, num_aux = self._read_header()
        new_pos = num_data + num_aux

        with open(self.index_file, 'r+b') as f:
            offset = HEADER_SIZE + new_pos * self.index_record_size
            f.seek(offset)
            f.write(index_record.to_bytes(self.format_key))

        # Actualizar encabezado (incrementar num_aux)
        self._write_header(pos_root, num_data, num_aux + 1)

        return new_pos

    # === BÚSQUEDA BINARIA ===

    def _binary_search_prev(self, key: Any) -> int:
        """
        Busca la posición del registro anterior a la clave en el índice principal

        Returns:
            Posición del registro previo o pos_root si key es menor que root
        """
        pos_root, num_data, _ = self._read_header()

        if pos_root == -1:
            return -1

        # Si no hay datos en el área principal, retornar pos_root directamente
        if num_data == 0:
            return pos_root

        root = self._read_index(pos_root)

        # Si key es menor o igual que root, no hay previo en el área principal
        if key <= root.key:
            return pos_root

        left, right = 0, num_data - 1
        prev_pos = pos_root

        while left <= right:
            mid = (left + right) // 2
            index_record = self._read_index(mid)

            # Saltar eliminados
            if index_record.next == -2:
                # Buscar registro válido cercano
                if mid > 0:
                    right = mid - 1
                else:
                    left = mid + 1
                continue

            if index_record.key == key:
                # Encontrado - buscar previo válido
                prev_pos = mid - 1
                while prev_pos >= 0:
                    prev = self._read_index(prev_pos)
                    if prev.next != -2 and prev.key < key:
                        return prev_pos
                    prev_pos -= 1
                return pos_root

            elif index_record.key < key:
                prev_pos = mid
                left = mid + 1
            else:
                right = mid - 1

        # No encontrado - buscar el último válido menor que key
        while prev_pos >= 0:
            prev = self._read_index(prev_pos)
            if prev.next != -2 and prev.key < key:
                return prev_pos
            prev_pos -= 1

        return pos_root

    # === BÚSQUEDA LINEAL ===

    def _linear_search(self, key: Any, start_pos: int) -> Tuple[int, int]:
        """
        Búsqueda lineal desde start_pos siguiendo punteros next

        Args:
            key: Clave a buscar
            start_pos: Posición desde donde empezar (debe ser <= key)

        Returns:
            (prev_pos, current_pos) donde:
            - current_pos tiene la key (si se encontró) o -1 (si no existe)
            - prev_pos es el registro anterior donde debería insertarse
        """
        if start_pos == -1:
            return -1, -1

        pos_root, _, _ = self._read_header()

        # Empezar desde start_pos
        current_pos = start_pos
        prev_pos = -1

        # Primera verificación: el root
        if current_pos == pos_root:
            root = self._read_index(pos_root)

            if root.key == key:
                return -1, pos_root  # Encontrado en root

            if root.key > key:
                return -1, -1  # Key debería ir antes del root

            # Key es mayor que root, seguir buscando
            prev_pos = pos_root
            current_pos = root.next

        # Búsqueda lineal desde start_pos
        while current_pos != -1:
            index_record = self._read_index(current_pos)

            # Saltar registros eliminados
            if index_record.next == -2:
                current_pos = -1  # Fin de la cadena en eliminado
                break

            if index_record.key == key:
                return prev_pos, current_pos  # Encontrado

            if index_record.key > key:
                return prev_pos, -1  # No existe, insertar antes de current

            # Avanzar
            prev_pos = current_pos
            current_pos = index_record.next

        # Llegamos al final, insertar al final
        return prev_pos, -1

    # === OPERACIONES PRINCIPALES ===

    def insert(self, record: List[Any]) -> bool:
        """
        Inserta un registro en el Sequential File

        Args:
            record: Lista de valores del registro

        Returns:
            True si se insertó correctamente
        """
        # Corregir formato
        record = self.RT.correct_format(record)
        key = self.RT.get_key(record)

        pos_root, num_data, num_aux = self._read_header()

        # Caso 1: Índice vacío
        if pos_root == -1:
            # Insertar en heap y obtener posición
            pos_heap = self.heap.insert(record)

            # Crear registro de índice
            index_record = IndexRecord(key, pos_heap)
            new_pos = self._append_index(index_record)
            self._write_header(new_pos, 0, 1)  # pos_root=new_pos, num_data=0, num_aux=1

            print(f"✅ Registro {key} insertado como raíz")
            return True

        # Caso 2: Verificar si ya existe y encontrar posición
        # Búsqueda binaria en índice principal
        prev_pos = self._binary_search_prev(key)

        # Búsqueda lineal desde prev_pos
        prev_pos, found_pos = self._linear_search(key, prev_pos)

        # Si ya existe, rechazar
        if found_pos != -1:
            print(f"❌ Registro con clave {key} ya existe")
            return False

        # Insertar en heap
        pos_heap = self.heap.insert(record)
        index_record = IndexRecord(key, pos_heap)

        # Caso 2.1: Insertar como nueva raíz (key menor que root)
        if prev_pos == -1:
            index_record.next = pos_root
            new_pos = self._append_index(index_record)
            self._write_header(new_pos, num_data, num_aux + 1)
            print(f"✅ Registro {key} insertado como nueva raíz")

        # Caso 2.2: Insertar en medio o al final
        else:
            prev_index = self._read_index(prev_pos)
            index_record.next = prev_index.next
            new_pos = self._append_index(index_record)

            # Actualizar puntero del previo
            prev_index.next = new_pos
            self._write_index(prev_pos, prev_index)
            print(f"✅ Registro {key} insertado después de {prev_index.key}")

        # Verificar si necesita reconstrucción
        _, _, num_aux = self._read_header()
        if num_aux >= self.max_aux_size:
            self._reconstruct()

        return True

    def search(self, key: Any) -> Optional[List[Any]]:
        """
        Busca un registro por clave

        Args:
            key: Valor de la clave a buscar

        Returns:
            Registro completo o None si no existe
        """
        pos_root, num_data, _ = self._read_header()

        if pos_root == -1:
            return None

        # Búsqueda binaria + lineal
        prev_pos = self._binary_search_prev(key)
        _, found_pos = self._linear_search(key, prev_pos)

        if found_pos == -1:
            return None

        # Leer del índice
        index_record = self._read_index(found_pos)

        # Verificar que no esté eliminado
        if index_record.next == -2:
            return None

        # Leer registro completo del heap
        return self.heap.read(index_record.pos)

    def search_range(self, key_begin: Any, key_end: Any) -> List[List[Any]]:
        """
        Busca registros en un rango [key_begin, key_end]

        Args:
            key_begin: Clave inicial del rango
            key_end: Clave final del rango

        Returns:
            Lista de registros en el rango
        """
        if key_begin > key_end:
            print("❌ Rango inválido: key_begin debe ser <= key_end")
            return []

        pos_root, num_data, _ = self._read_header()

        if pos_root == -1:
            return []

        results = []

        # Buscar punto de inicio
        prev_pos = self._binary_search_prev(key_begin)
        _, start_pos = self._linear_search(key_begin, prev_pos)

        # Si no se encontró exact match, empezar desde el previo
        if start_pos == -1:
            start_pos = prev_pos if prev_pos != -1 else pos_root

        # Recorrer desde start_pos hasta key_end
        current_pos = start_pos

        while current_pos != -1:
            index_record = self._read_index(current_pos)

            # Si la clave es mayor que key_end, terminar
            if index_record.key > key_end:
                break

            # Si está en el rango y no eliminado, agregar
            if (index_record.key >= key_begin and
                    index_record.key <= key_end and
                    index_record.next != -2):
                record = self.heap.read(index_record.pos)
                results.append(record)

            current_pos = index_record.next

        return results

    def delete(self, key: Any) -> bool:
        """
        Elimina un registro (eliminación lógica)

        Args:
            key: Clave del registro a eliminar

        Returns:
            True si se eliminó correctamente
        """
        pos_root, num_data, num_aux = self._read_header()

        if pos_root == -1:
            print(f"❌ Registro con clave {key} no encontrado")
            return False

        # Buscar registro
        prev_pos = self._binary_search_prev(key)
        prev_pos, found_pos = self._linear_search(key, prev_pos)

        if found_pos == -1:
            print(f"❌ Registro con clave {key} no encontrado")
            return False

        # Leer registro a eliminar
        index_to_delete = self._read_index(found_pos)

        # Actualizar punteros
        if prev_pos == -1:
            # Es la raíz
            self._write_header(index_to_delete.next, num_data, num_aux)
        else:
            # Actualizar puntero del previo
            prev_index = self._read_index(prev_pos)
            prev_index.next = index_to_delete.next
            self._write_index(prev_pos, prev_index)

        # Marcar como eliminado
        index_to_delete.next = -2
        self._write_index(found_pos, index_to_delete)

        print(f"✅ Registro con clave {key} eliminado")
        return True

    def _reconstruct(self):
        """Reconstruye el Sequential File (compacta índice principal y auxiliar)"""
        print("🔄 Reconstruyendo Sequential File...")

        pos_root, _, _ = self._read_header()

        if pos_root == -1:
            return

        # Recolectar todos los registros válidos en orden
        valid_indices = []
        current_pos = pos_root

        while current_pos != -1:
            index_record = self._read_index(current_pos)

            # Solo incluir no eliminados
            if index_record.next != -2:
                valid_indices.append(index_record)

            current_pos = index_record.next

        # Crear archivo temporal
        temp_file = self.index_file + ".tmp"

        with open(temp_file, 'wb') as f:
            # Escribir encabezado
            new_num_data = len(valid_indices)
            f.write(struct.pack('iii', 0, new_num_data, 0))

            # Escribir índices en orden con punteros consecutivos
            for i, index_record in enumerate(valid_indices):
                if i < new_num_data - 1:
                    index_record.next = i + 1
                else:
                    index_record.next = -1

                f.write(index_record.to_bytes(self.format_key))

        # Reemplazar archivo original
        os.remove(self.index_file)
        os.rename(temp_file, self.index_file)

        # Actualizar max_aux_size dinámicamente
        self.max_aux_size = max(10, int(math.sqrt(new_num_data) + 0.5))

        print(f"✅ Reconstrucción completada: {new_num_data} registros, nuevo max_aux={self.max_aux_size}")

    def scan_all(self) -> List[List[Any]]:
        """Retorna todos los registros en orden"""
        pos_root, _, _ = self._read_header()

        if pos_root == -1:
            return []

        results = []
        current_pos = pos_root

        while current_pos != -1:
            index_record = self._read_index(current_pos)

            if index_record.next != -2:  # No eliminado
                record = self.heap.read(index_record.pos)
                results.append(record)

            current_pos = index_record.next

        return results

    def count(self) -> int:
        """Retorna número de registros válidos"""
        return len(self.scan_all())

    def print_all(self):
        """Imprime todos los registros ordenados"""
        records = self.scan_all()
        pos_root, num_data, num_aux = self._read_header()

        print(f"\n📋 Sequential File")
        print(f"   Índice principal: {num_data} | Auxiliar: {num_aux} | Total: {len(records)}")
        print(f"   Max aux size: {self.max_aux_size}\n")

        if not records:
            print("   (vacío)")
            return

        for i, record in enumerate(records):
            print(f"   [{i}] ", end="")
            self.RT._print(record)

    def __repr__(self) -> str:
        pos_root, num_data, num_aux = self._read_header()
        return f"SequentialFile(records={num_data + num_aux}, data={num_data}, aux={num_aux})"


# Función helper
def create_sequential_file(table_format: Dict[str, str],
                           name_key: str,
                           index_file: str = 'Sequential_Struct/sequential_index.bin',
                           data_file: str = 'Sequential_Struct/sequential_data.bin',
                           max_aux_size: int = 100) -> SequentialFile:
    """
    Crea un Sequential File

    Args:
        table_format: Formato de campos
        name_key: Nombre del campo clave
        index_file: Ruta del archivo de índice
        data_file: Ruta del archivo de datos
        max_aux_size: Tamaño máximo del auxiliar

    Returns:
        Instancia de SequentialFile
    """
    return SequentialFile(table_format, name_key, index_file, data_file, max_aux_size)
