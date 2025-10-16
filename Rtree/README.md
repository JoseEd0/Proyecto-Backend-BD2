# R-Tree - Proyecto BD2

Implementación completa de índice espacial R-Tree para el curso de Base de Datos 2.

## Archivos

```
rtree_impl.py     # Implementación principal del R-Tree
test_rtree.py     # Tests unitarios completos  
README.md         # Esta documentación
```

## Operaciones

| Operación | Descripción |
|-----------|-------------|
| `add(record)` | Insertar registro espacial |
| `remove(id)` | Eliminar por ID |
| `search(id)` | Buscar por ID |
| `range_search(point, radius)` | Buscar en radio |
| `k_nearest_neighbors(point, k)` | K vecinos más cercanos |

## Tests

```bash
# Ejecutar todos los tests
py -m unittest test_rtree.py -v

# Resultado: 21 tests OK
```