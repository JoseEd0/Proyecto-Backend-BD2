# Extendible Hashing - Proyecto BD2
Implementación de índice hash extensible en disco para el curso de Base de Datos 2.

🎯 Características
- ✅ Directorio dinámico con profundidad global/local (doblamiento automático)
- ✅ Buckets en disco con encadenamiento de overflow (next_bucket_id)
- ✅ Inserción, búsqueda y eliminación por clave en O(1) promedio
- ✅ Persistencia en carpeta configurable (ej. eh_data/)
- ✅ Logs y estadísticas de I/O (si usas logger y stats)
- ✅ API simple y clara para integrar con el motor

📁 Archivos
- extendible_hashing.py     # Implementación principal del Hash Extensible
- test_extendible_hashing.py # Tests unitarios básicos (opcional)
- README.md                  # Esta documentación

Nota: Si aún no renombras el archivo, puede estar en bplustree.py con la clase DiskExtendibleHashing.

🚀 Uso Básico
from extendible_hashing import DiskExtendibleHashing
# o: from bplustree import DiskExtendibleHashing  # si no renombraste el archivo

# Crear índice
eh = DiskExtendibleHashing(
    dir_path="eh_data",
    bucket_capacity=4,
    initial_global_depth=1,
    max_global_depth=10
)

# Agregar
eh.add(42, {"name": "Alice"})
eh.add(7,  "value_7")

# Buscar
print(eh.search(42))  # -> {"name": "Alice"}

# Eliminar
eh.remove(7)

# Persistencia entre ejecuciones (los datos quedan en eh_data/)
# Para pruebas repetibles, limpia el directorio o usa otro dir_path

📋 Operaciones
Operación               Descripción
add(key, value)         Inserta o actualiza un par clave-valor
search(key)             Retorna el valor por clave o None si no existe
remove(key)             Elimina por clave (maneja cadenas de overflow)
clear()                 Limpia el directorio en disco (si lo implementaste)

🧪 Tests
# Ejecutar tests (si tienes test_extendible_hashing.py)
py -m unittest test_extendible_hashing.py -v

🗂️ Persistencia
- Directorio: dir_path (por defecto eh_data/)
- Buckets: archivos por bucket (y directorio con mapeo de índices)
- Overflow: next_bucket_id encadena buckets cuando se llena la capacidad
- Tip: para evitar “acumulación” en pruebas, usa eh.clear() o cambia dir_path

❗ Problemas Comunes
- “Se acumulan registros”: cambia dir_path o limpia con clear() / borra la carpeta.
- “No encuentra bucket 0”: asegúrate de recorrer siempre el bucket actual y luego next_bucket_id.
- “__init__ con error”: verifica que los constructores usen __init__ y no _init_.
- Convención de next_bucket_id: usa 0 o -1 como centinela de “no hay siguiente” y sé consistente.