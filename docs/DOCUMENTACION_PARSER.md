# Documentación del Parser SQL
**Proyecto CS2702 - Base de Datos 2 UTEC**

## 📋 Resumen General

El parser SQL es un sistema modular que convierte consultas SQL en operaciones del mini gestor de bases de datos. Soporta múltiples técnicas de indexación y operaciones CRUD básicas.

## 🏗️ Arquitectura del Sistema

```
SQL Text → Lexer → Parser → Validator → Translator → Database Operations
```

---

## 📁 Componentes del Parser

### 1. **lexer.py** - Analizador Léxico
**¿Qué hace?** Convierte texto SQL en tokens tipados.

**¿Cómo lo hace?**
- Usa expresiones regulares compiladas para mejor rendimiento
- Reconoce palabras clave, operadores, literales e identificadores
- Maneja strings entre comillas y números (enteros/flotantes)

**Tokens principales:**
- Palabras clave: `CREATE`, `SELECT`, `INSERT`, `DELETE`, `WHERE`
- Tipos de datos: `INT`, `VARCHAR`, `DATE`, `ARRAY[FLOAT]`
- Índices: `SEQ`, `BTree`, `ISAM`, `Hash`, `RTree`
- Operadores: `=`, `<`, `>`, `BETWEEN`, `IN`

**Salida:** Lista de objetos `Token` con tipo, valor y posición.

---

### 2. **ast_nodes.py** - Estructuras de Datos
**¿Qué hace?** Define las estructuras del Árbol de Sintaxis Abstracta (AST).

**¿Cómo lo hace?**
- Usa `dataclasses` para definir objetos inmutables
- Emplea `Enum` para type safety
- Jerarquía de clases: `ParsedQuery` → `CreateTableQuery`, `SelectQuery`, etc.

**Estructuras principales:**
- `Column`: Define columnas con tipo de dato, índice y restricciones
- `Condition`: Representa condiciones WHERE con operadores
- `ParsedQuery`: Clase base para todas las consultas
- Subclases específicas para cada tipo de operación SQL

---

### 3. **sql_parser.py** - Analizador Sintáctico  
**¿Qué hace?** Construye el AST desde los tokens.

**¿Cómo lo hace?**
- Parser descendente recursivo
- Cada regla gramatical es un método
- Maneja precedencia de operadores y anidamiento

**Operaciones que parsea:**
- `CREATE TABLE` con definición de columnas e índices
- `CREATE TABLE FROM FILE` para archivos CSV
- `SELECT` con columnas específicas o `*`, condiciones WHERE
- `INSERT INTO` con valores específicos
- `DELETE FROM` con condiciones

**Salida:** Objeto `ParsedQuery` tipado según la operación.

---

### 4. **semantic_validator.py** - Validador Semántico
**¿Qué hace?** Valida que las consultas sean semánticamente correctas.

**¿Cómo lo hace?**
- Mantiene registro de esquemas de tablas
- Verifica existencia de tablas y columnas
- Valida compatibilidad entre tipos de datos e índices

**Validaciones principales:**
- Una sola columna `KEY` por tabla
- Columnas espaciales (`ARRAY[FLOAT]`) solo con índice `RTree`
- Índices `Hash` no soportan operador `BETWEEN`
- Existencia de tablas/columnas referenciadas

**Salida:** Lista de errores semánticos encontrados.

---

### 5. **query_translator.py** - Traductor de Consultas
**¿Qué hace?** Traduce consultas validadas a operaciones del gestor.

**¿Cómo lo hace?**
- Mapea operaciones SQL a métodos del adaptador de BD
- Selecciona el tipo de búsqueda según operador y tipo de índice
- Maneja casos especiales como consultas espaciales

**Operaciones traducidas:**
- `CREATE` → `createTable()` o `createTableFromFile()`
- `SELECT =` → `search()`
- `SELECT BETWEEN` → `rangeSearch()`
- `SELECT IN` (espacial) → `spatialRangeSearch()`
- `INSERT` → `add()`
- `DELETE` → `remove()`

**Adaptador Mock:** Simula operaciones reales para testing.

---

### 6. **sql_engine.py** - Motor Principal
**¿Qué hace?** Integra todos los componentes en una interfaz unificada.

**¿Cómo lo hace?**
- Orquesta el flujo: Lexer → Parser → Validator → Translator
- Maneja errores y excepciones en cada etapa
- Proporciona métrica de tiempo de ejecución

**Métodos principales:**
- `execute_sql()`: Ejecución completa de consulta
- `parse_only()`: Solo parsing sin validación
- `validate_only()`: Solo validación sin ejecución
- `list_tables()`, `get_table_info()`: Metadatos

---

### 7. **__init__.py** - Módulo Principal
**¿Qué hace?** Expone la API pública del parser.

**¿Cómo lo hace?**
- Importa y exporta clases principales
- Define función factory `create_sql_parser_engine()`
- Establece versión y metadatos del módulo

---

## 🔧 Flujo de Procesamiento

1. **Tokenización** (lexer.py)
   ```
   "SELECT * FROM tabla;" → [SELECT, *, FROM, tabla, ;]
   ```

2. **Parsing** (sql_parser.py)
   ```
   [Tokens] → SelectQuery(columns=["*"], table="tabla", condition=None)
   ```

3. **Validación** (semantic_validator.py)
   ```
   ¿Existe tabla "tabla"? ¿Son válidas las columnas?
   ```

4. **Traducción** (query_translator.py)
   ```
   SelectQuery → scanAll("tabla")
   ```

5. **Ejecución** (sql_engine.py)
   ```
   Resultado + métricas + manejo de errores
   ```

---

## 🎯 Tipos de Datos y Operaciones Soportadas

### Tipos de Datos
- **INT**: Números enteros
- **VARCHAR[n]**: Cadenas con tamaño máximo
- **DATE**: Fechas como strings
- **ARRAY[FLOAT]**: Arrays de flotantes para datos espaciales

### Tipos de Índices
- **SEQ**: Sequential File - búsquedas lineales
- **BTree**: B+ Tree - búsquedas y rangos eficientes  
- **ISAM**: ISAM Sparse - índice de tres niveles
- **Hash**: Extendible Hashing - búsquedas exactas rápidas
- **RTree**: R-Tree - datos espaciales multidimensionales

### Operadores SQL
- **Exactos**: `=` (todos los índices)
- **Rangos**: `<`, `>`, `<=`, `>=`, `BETWEEN` (excepto Hash)
- **Espaciales**: `IN ([x,y], radio)` (solo RTree)

---

## 🔍 Ejemplos de Uso

### Crear Tabla
```sql
CREATE TABLE Restaurantes (
    id INT KEY INDEX SEQ,
    nombre VARCHAR[50] INDEX BTree,
    ubicacion ARRAY[FLOAT] INDEX RTree
);
```
**Traducción:** `createTable("Restaurantes", [columnas...])`

### Consulta Espacial
```sql
SELECT * FROM Restaurantes 
WHERE ubicacion IN ([12.05, -77.04], 0.1);
```
**Traducción:** `spatialRangeSearch("Restaurantes", "ubicacion", [12.05, -77.04], 0.1)`

### Búsqueda por Rango
```sql
SELECT * FROM Productos 
WHERE precio BETWEEN 10 AND 50;
```
**Traducción:** `rangeSearch("Productos", "precio", 10, 50)`

---

## ⚠️ Limitaciones Conocidas

1. **Una sola condición WHERE** por consulta
2. **Números negativos** sin espacios: `-77.04` ✅, `- 77.04` ❌
3. **Adaptador mock** para testing (no BD real)
4. **Validación de archivos CSV** no verifica existencia real

---

## 🚀 Integración

Para usar el parser en tu aplicación:

```python
from parser import create_sql_parser_engine

# Crear motor
engine = create_sql_parser_engine()

# Ejecutar consulta
resultado = engine.execute_sql("CREATE TABLE Test (id INT KEY INDEX SEQ);")

if resultado['success']:
    print("✅ Consulta exitosa")
else:
    print("❌ Errores:", resultado['errors'])
```

---

## 📊 Estadísticas del Código

| Archivo | Líneas | Función Principal |
|---------|--------|-------------------|
| `lexer.py` | 214 | Tokenización |
| `sql_parser.py` | 305 | Análisis sintáctico |
| `semantic_validator.py` | 143 | Validación semántica |
| `query_translator.py` | 183 | Traducción a operaciones |
| `sql_engine.py` | 103 | Orquestación |
| `ast_nodes.py` | 118 | Estructuras de datos |
| `__init__.py` | 49 | API pública |
| **Total** | **1,115** | **Parser completo** |

---

**Desarrollado para CS2702 - Base de Datos 2 UTEC**  
*Parser SQL modular y extensible para mini gestor de BD*
