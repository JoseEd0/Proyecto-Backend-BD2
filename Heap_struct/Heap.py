"""
Heap File - Estructura de almacenamiento sin orden específico
Proyecto CS2702 - Base de Datos 2 UTEC

El Heap File es una estructura simple de almacenamiento donde:
- Los registros se insertan al final del archivo
- No hay orden específico
- Búsquedas requieren scan completo O(n)
- Ideal para ser usado con estructuras de índice (como Sequential File)

Ventajas:
- Inserción muy rápida O(1)
- No requiere reorganización
- Espacio contiguo eficiente

Uso:
    heap = Heap(table_format, "id", "data/heap_file.bin")
    pos = heap.insert(record)  # Retorna posición del registro
    record = heap.read(pos)     # Lee registro en posición
"""

import os
import struct
import sys
from typing import List, Any, Dict

# Importar RegistroType
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from Utils.Registro import RegistroType


# Constantes
HEADER_SIZE = 4  # 4 bytes para contador de registros (int)


class Heap:
    """
    Heap File - Almacenamiento sin orden específico
    
    Estructura del archivo:
    - Encabezado (4 bytes): Número de registros
    - Registros: Datos serializados uno tras otro
    """
    
    def __init__(self, 
                 table_format: Dict[str, str], 
                 name_key: str,
                 data_file: str = 'Heap_struct/heap_data.bin',
                 force_create: bool = False):
        """
        Inicializa el Heap File
        
        Args:
            table_format: Diccionario con formato de campos {nombre: tipo}
            name_key: Nombre del campo clave primaria
            data_file: Ruta del archivo de datos
            force_create: Si True, crea archivo nuevo (borra existente)
        """
        self.data_file = data_file
        self.RT = RegistroType(table_format, name_key)
        self.record_size = self.RT.size
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        
        # Inicializar archivo
        if force_create and os.path.exists(data_file):
            os.remove(data_file)
        
        self._initialize_file()
    
    def _initialize_file(self):
        """Inicializa el archivo con encabezado si no existe"""
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'wb') as f:
                # Encabezado: contador de registros = 0
                f.write(struct.pack('i', 0))
    
    def _read_header(self) -> int:
        """Lee el número de registros del encabezado"""
        with open(self.data_file, 'rb') as f:
            header = f.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                return 0
            return struct.unpack('i', header)[0]
    
    def _write_header(self, num_records: int):
        """Actualiza el número de registros en el encabezado"""
        with open(self.data_file, 'r+b') as f:
            f.seek(0)
            f.write(struct.pack('i', num_records))
    
    def insert(self, record: List[Any]) -> int:
        """
        Inserta un registro al final del heap
        
        Args:
            record: Lista de valores del registro
            
        Returns:
            Posición (índice) del registro insertado
        """
        # Corregir formato del registro
        record = self.RT.correct_format(record)
        
        # Leer contador actual
        num_records = self._read_header()
        
        # Calcular posición de escritura
        offset = HEADER_SIZE + num_records * self.record_size
        
        # Escribir registro
        with open(self.data_file, 'r+b') as f:
            f.seek(offset)
            f.write(self.RT.to_bytes(record))
        
        # Actualizar contador
        self._write_header(num_records + 1)
        
        return num_records  # Retorna la posición (índice) del registro
    
    def read(self, pos: int) -> List[Any]:
        """
        Lee un registro en una posición específica
        
        Args:
            pos: Posición (índice) del registro
            
        Returns:
            Lista de valores del registro
            
        Raises:
            ValueError: Si la posición es inválida
        """
        num_records = self._read_header()
        
        if pos < 0 or pos >= num_records:
            raise ValueError(f"Posición {pos} fuera de rango [0, {num_records-1}]")
        
        # Calcular offset
        offset = HEADER_SIZE + pos * self.record_size
        
        # Leer registro
        with open(self.data_file, 'rb') as f:
            f.seek(offset)
            data = f.read(self.record_size)
            
            if len(data) < self.record_size:
                raise ValueError(f"No se pudo leer el registro en posición {pos}")
            
            return self.RT.from_bytes(data)
    
    def update(self, pos: int, record: List[Any]) -> bool:
        """
        Actualiza un registro en una posición específica
        
        Args:
            pos: Posición del registro a actualizar
            record: Nuevos valores del registro
            
        Returns:
            True si se actualizó correctamente
        """
        num_records = self._read_header()
        
        if pos < 0 or pos >= num_records:
            raise ValueError(f"Posición {pos} fuera de rango")
        
        # Corregir formato
        record = self.RT.correct_format(record)
        
        # Calcular offset
        offset = HEADER_SIZE + pos * self.record_size
        
        # Escribir registro actualizado
        with open(self.data_file, 'r+b') as f:
            f.seek(offset)
            f.write(self.RT.to_bytes(record))
        
        return True
    
    def scan_all(self) -> List[List[Any]]:
        """
        Lee todos los registros del heap (scan completo)
        
        Returns:
            Lista de todos los registros
        """
        num_records = self._read_header()
        records = []
        
        with open(self.data_file, 'rb') as f:
            f.seek(HEADER_SIZE)
            
            for _ in range(num_records):
                data = f.read(self.record_size)
                if len(data) < self.record_size:
                    break
                records.append(self.RT.from_bytes(data))
        
        return records
    
    def search(self, key_value: Any) -> List[List[Any]]:
        """
        Busca registros por clave (scan completo - O(n))
        
        Args:
            key_value: Valor de la clave a buscar
            
        Returns:
            Lista de registros que coinciden con la clave
        """
        results = []
        all_records = self.scan_all()
        
        for record in all_records:
            if self.RT.get_key(record) == key_value:
                results.append(record)
        
        return results
    
    def count(self) -> int:
        """Retorna el número de registros en el heap"""
        return self._read_header()
    
    def clear(self):
        """Elimina todos los registros del heap"""
        with open(self.data_file, 'wb') as f:
            f.write(struct.pack('i', 0))
    
    def print_all(self):
        """Imprime todos los registros del heap"""
        num_records = self._read_header()
        print(f"\n📦 Heap File: {self.data_file}")
        print(f"Total registros: {num_records}\n")
        
        if num_records == 0:
            print("  (vacío)")
            return
        
        records = self.scan_all()
        for i, record in enumerate(records):
            print(f"  [{i}] ", end="")
            self.RT._print(record)
    
    def get_file_size(self) -> int:
        """Retorna el tamaño del archivo en bytes"""
        if not os.path.exists(self.data_file):
            return 0
        return os.path.getsize(self.data_file)
    
    def __repr__(self) -> str:
        """Representación del Heap"""
        num_records = self._read_header()
        return f"Heap(file={self.data_file}, records={num_records}, record_size={self.record_size})"


# Función helper
def create_heap(table_format: Dict[str, str], 
                name_key: str,
                data_file: str = 'Heap_struct/heap_data.bin') -> Heap:
    """
    Crea un Heap File
    
    Args:
        table_format: Formato de los campos
        name_key: Nombre del campo clave
        data_file: Ruta del archivo
        
    Returns:
        Instancia de Heap
    """
    return Heap(table_format, name_key, data_file)
