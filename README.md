# ISAM (Índice Secuencial con Acceso Directo) – Proyecto BD2

Implementación completa del **ISAM de tres niveles (L2–L1–L0/Super Root, Root y Leaf)**.

---

## 🎯 Características

- ✅ **ISAM estático de 3 niveles** (`Super Root`, `Root`, `Leaf`)
- ✅ **Soporte de páginas primarias y overflow encadenadas**
- ✅ **Persistencia binaria** (`.dat` y `.dat_idx`)
- ✅ **Operaciones completas**: `add`, `remove`, `search`, `range_search`, `scanAll`
- ✅ **Bloques configurables** (`BLOCK_FACTOR`, `L0_BLOCK_FACTOR`, `L1_BLOCK_FACTOR`)
- ✅ **Registros de ejemplo tipo Restaurante** (`id`, `nombre`, `fecha`, `rating`)
- ✅ **Listo para integrar con otras estructuras (B+Tree, RTree, Hashing)**

---

## 📁 Archivos

```

ISAM.py   # Implementación principal del ISAM (3 niveles)
test_isam_big.py    # Test grande con muchos registros
README.md

````

---

## 🧱 Estructura del Índice

```mermaid
graph TD
    A[L2 - Directorio Principal] --> B1[L1 - Bloque 1]
    A --> B2[L1 - Bloque 2]
    B1 --> C1[L0 - Leaf 0-2]
    B1 --> C2[L0 - Leaf 3-5]
    B2 --> C3[L0 - Leaf 6-8]
    C1 --> D1[Páginas Primarias + Overflow]
    C2 --> D2[Páginas Primarias + Overflow]
    C3 --> D3[Páginas Primarias + Overflow]
````

Cada nivel agrupa las claves máximas de su nivel inferior:

* **L0** → asocia claves máximas con páginas primarias.
* **L1** → agrupa entradas L0.
* **L2** → agrupa entradas L1.

---

## 📋 Operaciones

| Operación            | Descripción                                                       |
| -------------------- | ----------------------------------------------------------------- |
| `add(record)`        | Inserta un nuevo registro (usa overflow si la página está llena). |
| `search(key)`        | Devuelve todos los registros cuyo `id` coincide con la clave.     |
| `range_search(a, b)` | Busca todos los registros con `id` dentro del rango `[a, b]`.     |
| `remove(key)`        | Elimina todas las coincidencias de la clave.                      |
| `scanAll()`          | Muestra en consola las páginas de datos y los índices L0–L2.      |

---

## 🧪 Tests

```bash
# Test con bastantes datos
py test_isam_big.py

```

Ejemplo de salida parcial del test grande:

```
================= MAPA JERÁRQUICO DEL ÍNDICE =================
SR[0] max_key=27  -> Root idx [0..2]
   R[0] max_key=9  -> Leaf idx [0..2]
      Leaf block: (max=3→pág0), (max=6→pág1), (max=9→pág2)
   R[1] max_key=18 -> Leaf idx [3..5]
      Leaf block: (max=12→pág3), (max=15→pág4), (max=18→pág5)
   ...
SR[1] max_key=54  -> Root idx [3..5]
...
================================================================
```

---

## 🧠 Conceptos Clave

| Concepto                                    | Descripción                                                                              |
| ------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **ISAM (Indexed Sequential Access Method)** | Método de acceso indexado y secuencial que combina índices estáticos y páginas overflow. |
| **Overflow Encadenado**                     | Las nuevas inserciones no reestructuran el índice: se crean páginas extra enlazadas.     |
| **Bloque de datos (Page)**                  | Contenedor de registros con cabecera (`size`, `next_page`) y espacio fijo.               |
| **Índice L0–L2**                            | Tres niveles jerárquicos de indexación (hojas, raíz media y raíz superior).              |
| **Estático**                                | El índice no se reorganiza tras las inserciones: la estructura inicial se mantiene.      |

---

## ⚙️ Configuración

```python
BLOCK_FACTOR = 3        # Registros por página de datos
L0_BLOCK_FACTOR = 3     # Entradas L0 agrupadas por cada bloque L1
L1_BLOCK_FACTOR = 3     # Entradas L1 agrupadas por bloque L2
```

Cambiar estos valores ajusta el **grado de agrupamiento** de los índices.

---

## 📈 Complejidad de las Operaciones

| Operación              | Complejidad Promedio | Observaciones                       |
| ---------------------- | -------------------- | ----------------------------------- |
| `search(key)`          | O(log n)             | Usa los 3 niveles de índice         |
| `range_search(a,b)`    | O(log n + k)         | `k` = registros dentro del rango    |
| `add(record)`          | O(1)                 | Solo crea overflow, sin reorganizar |
| `remove(key)`          | O(1)                 | Borrado físico dentro de página     |
| `build_from_records()` | O(n log n)           | Ordenamiento inicial por clave      |

---

## 📊 Ejemplo de Tabla Usada

```sql
CREATE TABLE Restaurantes (
    id INT KEY INDEX ISAM,
    nombre VARCHAR[20],
    fechaRegistro DATE,
    rating FLOAT
);
```

---

