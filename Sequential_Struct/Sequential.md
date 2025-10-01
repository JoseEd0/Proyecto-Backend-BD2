# Documentación - Sequential File

## Introducción

Un **Sequential File** es una estructura de datos que mantiene registros ordenados por una clave primaria, optimizando las operaciones de búsqueda mediante el uso de un índice separado. Esta implementación combina un archivo de índice pequeño (lista enlazada ordenada) con un archivo de datos (Heap File) para lograr eficiencia en espacio y tiempo.

## Arquitectura de la Estructura

### Componentes Principales

La implementación se compone de tres módulos integrados:

1. **SequentialFile** (`Sequential_Struct/sequential_file.py`)
   - Gestiona el índice ordenado como una lista enlazada.
   - Coordina las operaciones de búsqueda, inserción, eliminación y reconstrucción.
   - Mantiene un área principal ordenada y un área auxiliar para inserciones rápidas.

2. **Heap** (`Heap_struct/Heap.py`)
   - Almacena los registros completos en un archivo binario de datos.
   - Proporciona operaciones de inserción, lectura y actualización por posición.
   - Funciona como almacenamiento de datos no ordenado (append-only).

3. **RegistroType** (`Utils/Registro.py`)
   - Define el formato y esquema de los registros.
   - Valida tipos de datos y normaliza valores.
   - Serializa y deserializa registros entre formato Python y bytes.
   - Identifica la clave primaria de cada registro.

### Relación entre Componentes

```
SequentialFile (índice ordenado)
    ├─> Heap (almacenamiento de datos)
    └─> RegistroType (formato y validación)
```

- **SequentialFile** mantiene el índice con referencias (posiciones) a los datos en el Heap.
- **Heap** almacena los registros completos y retorna posiciones físicas.
- **RegistroType** asegura consistencia de tipos entre todos los componentes.

## Estructura de Archivos

### Archivo de Índice (sequential_index.bin)

**Encabezado (12 bytes):**
```
┌────────────┬────────────┬────────────┐
│  pos_root  │  num_data  │  num_aux   │
│  (4 bytes) │  (4 bytes) │  (4 bytes) │
└────────────┴────────────┴────────────┘
```

- `pos_root`: Posición física del primer registro en el índice (raíz de la lista enlazada).
- `num_data`: Número de registros en el área principal (ordenada).
- `num_aux`: Número de registros en el área auxiliar (nuevas inserciones).

**Registro de Índice:**
```
┌──────────────────┬─────────────┬─────────────┐
│       key        │     pos     │    next     │
│ (tipo variable)  │  (4 bytes)  │  (4 bytes)  │
└──────────────────┴─────────────┴─────────────┘
```

- `key`: Valor de la clave primaria (tipo definido por `table_format`).
- `pos`: Posición del registro completo en el archivo de datos (Heap).
- `next`: Puntero al siguiente registro en la lista enlazada.
  - `-1`: Indica fin de lista.
  - `-2`: Indica registro eliminado lógicamente.
  - `≥ 0`: Posición física del siguiente registro en el índice.

**Cálculo de Posición Física:**
```
offset = HEADER_SIZE + index_position × record_size
```

### Archivo de Datos (sequential_data.bin)

Manejado completamente por la clase **Heap**:
- Almacena registros completos serializados por **RegistroType**.
- Estructura interna: encabezado + registros consecutivos.
- **SequentialFile** solo guarda las posiciones retornadas por `Heap.insert()` en el índice.

## Uso de Heap y RegistroType

### RegistroType (Utils/Registro.py)

Define el esquema de la tabla mediante un diccionario `table_format`:

```python
table_format = {
    "id": "i",      # int32
    "name": "20s",  # string de 20 bytes
    "age": "i"      # int32
}
name_key = "id"  # campo clave primaria
```

**Responsabilidades:**
- `correct_format(record)`: Normaliza tipos y tamaños de un registro.
- `to_bytes(record)`: Serializa un registro a bytes para almacenamiento.
- `from_bytes(data)`: Deserializa bytes a registro (lista de valores).
- `get_key(record)`: Extrae el valor de la clave primaria.
- `_get_null_value(format)`: Proporciona valores centinela para campos NULL.

**Formatos soportados:**
- `i`: entero de 32 bits (int32).
- `q`: entero de 64 bits (int64).
- `f`: flotante de 32 bits (float).
- `d`: flotante de 64 bits (double).
- `?`: booleano (bool).
- `Ns`: cadena de N bytes fijos (ej. `20s`).

### Heap (Heap_struct/Heap.py)

Proporciona almacenamiento persistente de registros completos:

**Métodos principales:**
- `insert(record) -> int`: Inserta un registro y retorna su posición física.
- `read(pos) -> list`: Lee un registro desde una posición específica.
- `update(pos, record)`: Actualiza un registro en una posición dada.
- `scan_all() -> list`: Retorna todos los registros almacenados.

**Integración con SequentialFile:**
1. Al insertar: `SequentialFile` llama a `Heap.insert()` y guarda la posición en el índice.
2. Al buscar: `SequentialFile` busca en el índice y luego llama a `Heap.read(pos)`.
3. Ambos usan la misma instancia de `RegistroType` para consistencia.

## Algoritmos y Funciones Principales

### Contratos y Comportamiento

Todas las funciones operan sobre claves comparables del mismo tipo que `name_key` y registros en formato `RegistroType`. Las operaciones que fallan retornan `False` o `None` según corresponda.

### 1. _binary_search_prev(key)

**Propósito:** Realizar búsqueda binaria en el área principal del índice para encontrar la posición del registro previo a `key`.

**Entrada:**
- `key`: Valor de la clave a buscar.

**Salida:**
- Posición física (int) del registro previo donde debería insertarse/buscarse `key`.
- `pos_root` si `key` es menor o igual que la raíz.
- `-1` si el índice está vacío.

**Comportamiento:**
- Opera solo sobre los primeros `num_data` registros (área principal ordenada).
- Salta registros marcados como eliminados (`next == -2`).
- Retorna la última posición válida cuya clave sea menor que `key`.

**Complejidad:** O(log n) accesos a disco.

### 2. _linear_search(key, start_pos)

**Propósito:** Búsqueda lineal siguiendo punteros `next` para encontrar la posición exacta de `key` o determinar dónde insertarla.

**Entrada:**
- `key`: Valor de la clave a buscar.
- `start_pos`: Posición inicial desde donde comenzar (resultado de `_binary_search_prev`).

**Salida:**
- Tupla `(prev_pos, found_pos)`:
  - `found_pos`: Posición del registro con la clave (o `-1` si no existe).
  - `prev_pos`: Posición del registro anterior donde enlazar (`-1` si debe insertarse antes de la raíz).

**Comportamiento:**
- Recorre la lista enlazada siguiendo `next` hasta encontrar la clave o superarla.
- Salta registros eliminados (`next == -2`).
- Verifica primero si `start_pos == pos_root` para manejo especial de la raíz.

**Complejidad:** O(k) accesos a disco, donde k es el tamaño del área auxiliar.

### 3. insert(record)

**Propósito:** Insertar un nuevo registro manteniendo el orden del índice.

**Entrada:**
- `record`: Lista de valores del registro (será validado por `RegistroType`).

**Salida:**
- `True` si la inserción fue exitosa.
- `False` si la clave ya existe (no permite duplicados).

**Flujo de Ejecución:**

1. **Normalización:** Llama a `RegistroType.correct_format(record)` para validar tipos.
2. **Extracción de clave:** Obtiene `key` con `RegistroType.get_key(record)`.
3. **Inserción en Heap:** Llama a `Heap.insert(record)` y obtiene `pos_heap`.
4. **Caso índice vacío:**
   - Crea registro de índice como raíz.
   - Actualiza encabezado con `pos_root` apuntando al nuevo registro.
5. **Caso índice no vacío:**
   - Busca posición con `_binary_search_prev(key)`.
   - Refina con `_linear_search(key, prev_pos)`.
   - Si `found_pos != -1`: retorna `False` (duplicado).
   - Si `prev_pos == -1`: inserta como nueva raíz, enlazando a la raíz actual.
   - Si no: inserta después de `prev_pos`, actualizando punteros.
6. **Actualización de encabezado:** Incrementa `num_aux`.
7. **Reconstrucción:** Si `num_aux >= max_aux_size`, llama a `_reconstruct()`.

**Complejidad:** O(log n + k) + O(1) escritura en Heap.

### 4. search(key)

**Propósito:** Buscar un registro por su clave primaria.

**Entrada:**
- `key`: Valor de la clave a buscar.

**Salida:**
- Lista con los valores del registro completo (leído del Heap).
- `None` si no existe o está eliminado.

**Flujo:**
1. Busca posición con `_binary_search_prev(key)`.
2. Refina con `_linear_search(key, prev_pos)`.
3. Si `found_pos == -1`: retorna `None`.
4. Lee `IndexRecord` en `found_pos`.
5. Verifica que `next != -2` (no eliminado).
6. Lee registro completo del Heap con `Heap.read(IndexRecord.pos)`.

**Complejidad:** O(log n + k) + O(1) lectura del Heap.

### 5. search_range(key_begin, key_end)

**Propósito:** Buscar todos los registros cuyas claves estén en el rango `[key_begin, key_end]`.

**Entrada:**
- `key_begin`: Límite inferior del rango (inclusivo).
- `key_end`: Límite superior del rango (inclusivo).

**Salida:**
- Lista de registros completos ordenados por clave.
- Lista vacía si no hay coincidencias o si `key_begin > key_end`.

**Flujo:**
1. Busca punto de inicio con `_binary_search_prev(key_begin)` y `_linear_search(key_begin, prev_pos)`.
2. Si no se encuentra `key_begin` exacto, ajusta al primer registro válido mayor o igual.
3. Recorre la lista enlazada con `next` hasta que `key > key_end`.
4. Para cada registro en rango:
   - Verifica que `key >= key_begin` y `key <= key_end`.
   - Verifica que `next != -2` (no eliminado).
   - Lee registro completo del Heap y lo agrega al resultado.

**Complejidad:** O(log n + k + r), donde r es el número de registros en el rango.

### 6. delete(key)

**Propósito:** Eliminar lógicamente todos los registros con la clave especificada.

**Entrada:**
- `key`: Valor de la clave a eliminar.

**Salida:**
- `True` si se eliminó al menos un registro.
- `False` si no se encontró la clave.

**Flujo:**
1. Busca posición con `_binary_search_prev(key)` y `_linear_search(key, prev_pos)`.
2. Si `found_pos == -1`: retorna `False`.
3. Recorre todos los registros con `key` y marca cada uno con `next = -2`.
4. Actualiza punteros:
   - Si se eliminó la raíz (`prev_pos == -1`): actualiza `pos_root` al siguiente válido.
   - Si no: actualiza `prev_pos.next` para saltar los eliminados.
5. **Nota:** No se decrementa `num_aux` ni `num_data`; la compactación ocurre en `_reconstruct()`.

**Complejidad:** O(log n + k).

### 7. _reconstruct()

**Propósito:** Compactar el índice eliminando registros marcados y consolidando área principal y auxiliar.

**Flujo:**
1. Recorre toda la lista enlazada desde `pos_root` siguiendo `next`.
2. Recolecta todos los registros con `next != -2` (no eliminados) en una lista temporal.
3. Crea un archivo temporal `index_file.tmp`.
4. Escribe encabezado con:
   - `pos_root = 0` (primera posición física).
   - `num_data = total_registros_válidos`.
   - `num_aux = 0` (área auxiliar vacía tras reconstrucción).
5. Escribe todos los registros válidos consecutivamente, actualizando punteros:
   - `next = i+1` para los registros intermedios.
   - `next = -1` para el último registro.
6. Reemplaza `index_file` original por el temporal.
7. Actualiza `max_aux_size` dinámicamente: `max(10, int(sqrt(num_data) + 0.5))`.

**Cuándo se ejecuta:**
- Automáticamente cuando `num_aux >= max_aux_size` tras una inserción.

**Complejidad:** O(n) accesos a disco (lectura + escritura de todo el índice).

### 8. scan_all()

**Propósito:** Retornar todos los registros válidos en orden.

**Salida:**
- Lista de registros completos (leídos del Heap).

**Flujo:**
1. Recorre la lista enlazada desde `pos_root`.
2. Para cada registro con `next != -2`, lee los datos del Heap y los agrega al resultado.

**Complejidad:** O(n).

### 9. count()

**Propósito:** Contar el número de registros válidos (no eliminados).

**Salida:**
- Entero con el número de registros.

**Implementación:** Llama a `scan_all()` y retorna la longitud.

**Complejidad:** O(n).

## Análisis de Complejidad

| Operación         | Accesos a Disco       | Complejidad           |
|-------------------|-----------------------|-----------------------|
| Inserción         | log(n) + k + O(1)     | O(log n + k)          |
| Búsqueda exacta   | log(n) + k + O(1)     | O(log n + k)          |
| Búsqueda por rango| log(n) + k + r        | O(log n + k + r)      |
| Eliminación       | log(n) + k            | O(log n + k)          |
| Reconstrucción    | n (lectura + escritura)| O(n)                 |
| Scan completo     | n                     | O(n)                  |

**Donde:**
- `n`: Número total de registros en el índice.
- `k`: Tamaño del área auxiliar (≈ √n tras reconstrucción).
- `r`: Número de registros en el rango buscado.

## Decisiones de Diseño

### Separación Índice-Datos

El índice almacena solo `(key, pos, next)` mientras que los datos completos están en el Heap. Esto reduce:
- El tamaño del índice (búsqueda binaria más eficiente en caché).
- La cantidad de datos movidos durante reconstrucción.
- El acoplamiento entre ordenamiento y almacenamiento.

### Área Auxiliar Dinámica

El área auxiliar crece hasta un límite `k` (aprox. √n) antes de reconstruir. Esto balancea:
- **Inserciones rápidas:** O(k) en lugar de O(n) por cada inserción.
- **Búsquedas eficientes:** Mantener k pequeño limita el costo lineal.
- **Reconstrucciones espaciadas:** Ocurren cada ~√n inserciones.

### Eliminación Lógica

Los registros eliminados se marcan con `next = -2` en lugar de removerse físicamente:
- **Ventaja:** Evita reorganización inmediata (O(1) vs O(n)).
- **Desventaja:** Desperdicia espacio hasta la próxima reconstrucción.
- **Justificación:** Las reconstrucciones periódicas compactan automáticamente.

### Lista Enlazada Ordenada

El índice es una lista enlazada en lugar de un array ordenado:
- **Ventaja:** Insertar en el área auxiliar no requiere mover datos (solo actualizar punteros).
- **Desventaja:** Búsqueda lineal en el área auxiliar.
- **Solución:** Mantener k pequeño minimiza el impacto lineal.
