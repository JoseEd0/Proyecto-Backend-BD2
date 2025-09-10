# Parser SQL - Mini Gestor de Bases de Datos

## CS2702 - Base de Datos 2 UTEC

### 📋 Descripción

Parser SQL completo para un mini gestor de bases de datos que soporta múltiples técnicas de indexación (Sequential File, ISAM, B+Tree, Extendible Hashing, RTree) y operaciones CRUD básicas.

### 🚀 Características

- **Análisis Léxico y Sintáctico**: Tokenización y parsing completo de consultas SQL
- **Validación Semántica**: Verificación de esquemas y compatibilidad de tipos
- **Traducción a Operaciones**: Conversión automática a llamadas del gestor de BD
- **Múltiples Índices**: SEQ, BTree, ISAM, Hash, RTree
- **Datos Espaciales**: Soporte para consultas geográficas con RTree
- **Manejo de Errores**: Detección y reporte detallado de errores

### 📁 Estructura del Proyecto

```
parser/
├── lexer.py              # Analizador léxico (tokenización)
├── ast_nodes.py          # Estructuras de datos del AST
├── sql_parser.py         # Analizador sintáctico
├── semantic_validator.py # Validador semántico
├── query_translator.py   # Traductor a operaciones
├── sql_engine.py         # Motor principal integrado
└── __init__.py          # Exports del módulo

demo_parser.py           # Script de demostración completa
README.md               # Este archivo
```

### 🔧 Sintaxis SQL Soportada

#### Creación de Tablas
```sql
CREATE TABLE Restaurantes (
    id INT KEY INDEX SEQ,
    nombre VARCHAR[50] INDEX BTree,
    fechaRegistro DATE,
    ubicacion ARRAY[FLOAT] INDEX RTree
);
```

#### Creación desde Archivo
```sql
CREATE TABLE Productos FROM FILE "productos.csv" USING INDEX ISAM("codigo");
```

#### Consultas SELECT
```sql
-- Búsqueda específica
SELECT * FROM Restaurantes WHERE id = 5;

-- Búsqueda por rango
SELECT * FROM Restaurantes WHERE nombre BETWEEN "A" AND "Z";

-- Búsqueda espacial
SELECT * FROM Restaurantes WHERE ubicacion IN ([12.05, -77.04], 1.0);
```

#### Inserción y Eliminación
```sql
INSERT INTO Restaurantes VALUES (1, "El Buen Sabor", "2023-01-15", [12.0462, -77.0428]);
DELETE FROM Restaurantes WHERE id = 1;
```

### 📊 Tipos de Datos

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `INT` | Números enteros | `id INT` |
| `VARCHAR[n]` | Cadenas con tamaño máximo | `nombre VARCHAR[50]` |
| `DATE` | Fechas en formato string | `fecha DATE` |
| `ARRAY[FLOAT]` | Arrays de flotantes (espaciales) | `ubicacion ARRAY[FLOAT]` |

### 🗂️ Tipos de Índices

| Índice | Descripción | Operaciones |
|--------|-------------|-------------|
| `SEQ` | Sequential File | search, rangeSearch, add |
| `BTree` | B+ Tree | search, rangeSearch, add, remove |
| `ISAM` | ISAM-Sparse Index | search, rangeSearch, add |
| `Hash` | Extendible Hashing | search, add, remove |
| `RTree` | R-Tree (espacial) | spatialRangeSearch |

### 💻 Uso

#### Instalación
```bash
# Clonar el repositorio
git clone <repo-url>
cd Proyecto-Backend-BD2

# Activar entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

#### Ejecución del Demo
```bash
python demo_parser.py
```

#### Uso Programático
```python
from parser import create_sql_parser_engine

# Crear motor parser
engine = create_sql_parser_engine()

# Ejecutar consulta SQL
resultado = engine.execute_sql("""
    CREATE TABLE Test (
        id INT KEY INDEX SEQ,
        nombre VARCHAR[20]
    );
""")

if resultado['success']:
    print("✅ Consulta ejecutada exitosamente")
    print(f"Resultado: {resultado['result']}")
else:
    print("❌ Errores:", resultado['errors'])
```

#### Funciones Útiles
```python
# Solo parsing sin ejecutar
exito, consulta = engine.parse_only("SELECT * FROM Test;")

# Solo validación
valida, errores = engine.validate_only("SELECT * FROM Test;")

# Información de tablas
tablas = engine.list_tables()
info = engine.get_table_info("Test")

# Historial de consultas
historial = engine.get_query_history()
```

### 🧪 Ejemplos de Consultas

```python
# Ejemplos incluidos en demo_parser.py
consultas = [
    # Crear tabla con múltiples índices
    "CREATE TABLE Restaurantes (id INT KEY INDEX SEQ, nombre VARCHAR[50] INDEX BTree, ubicacion ARRAY[FLOAT] INDEX RTree);",
    
    # Insertar datos
    'INSERT INTO Restaurantes VALUES (1, "El Buen Sabor", [12.0462, -77.0428]);',
    
    # Búsquedas
    "SELECT * FROM Restaurantes WHERE id = 1;",
    'SELECT * FROM Restaurantes WHERE nombre BETWEEN "A" AND "M";',
    "SELECT * FROM Restaurantes WHERE ubicacion IN ([12.05, -77.04], 0.01);",
    
    # Eliminar
    "DELETE FROM Restaurantes WHERE id = 1;"
]
```

### ✅ Validaciones Implementadas

- **Sintácticas**: Estructura correcta de consultas SQL
- **Semánticas**: Existencia de tablas y columnas
- **Tipos de Datos**: Compatibilidad entre valores y columnas
- **Índices**: Compatibilidad entre tipos de índice y operaciones
- **Restricciones**: Una columna KEY por tabla, índices apropiados para tipos de datos

### 🔍 Operaciones Traducidas

#### Para Índices Tradicionales
- `search(table, column, key)` - Búsqueda exacta
- `rangeSearch(table, column, begin, end)` - Búsqueda por rango
- `add(table, record)` - Insertar registro
- `remove(table, column, key)` - Eliminar registro

#### Para Datos Espaciales (RTree)
- `spatialRangeSearch(table, column, point, radius)` - Búsqueda por radio
- `scanAll(table)` - Scan completo de tabla

### 🚧 Limitaciones Conocidas

1. **Números negativos**: Deben escribirse sin espacios (ej: `-77.04` no `- 77.04`)
2. **Validación de archivos CSV**: No verifica existencia real del archivo
3. **Un solo WHERE**: Solo se soporta una condición WHERE por consulta
4. **Mock Database**: El adaptador actual es simulado para propósitos de testing

### 📈 Estadísticas de la Demostración

Al ejecutar `demo_parser.py` se mostrarán:
- ✅ Consultas ejecutadas exitosamente
- ❌ Errores encontrados y su tipo
- 📊 Estadísticas de rendimiento
- 🗃️ Información de tablas creadas
- 🔧 Log de operaciones ejecutadas

### 🔗 Integración

Este parser está diseñado para integrarse con el mini gestor de bases de datos del proyecto. Para conectarlo con el gestor real:

1. Implementar `DatabaseAdapter` real en lugar de `MockDatabaseAdapter`
2. Reemplazar llamadas mock con llamadas reales al gestor
3. Manejar persistencia y recuperación de esquemas de tablas

### 👥 Equipo

**CS2702 - Base de Datos 2 UTEC**  
Proyecto 1 - Mini Gestor de Bases de Datos
