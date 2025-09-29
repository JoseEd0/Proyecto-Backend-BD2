# 🚀 Guía de Instalación y Primer Uso

## 📋 Prerequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Git (opcional, para clonar el repositorio)

## 🔧 Instalación

### 1. Verificar Python

```bash
python --version
# Debe mostrar: Python 3.8.x o superior
```

Si no tienes Python instalado:
- Windows: https://www.python.org/downloads/
- Linux/Mac: Suele venir instalado o usar `apt install python3` / `brew install python3`

### 2. Crear entorno virtual (recomendado)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instalará:
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- pydantic==2.5.0
- python-multipart==0.0.6
- python-dotenv==1.0.0

### 4. Verificar instalación

```bash
python -c "import fastapi; import uvicorn; print('✅ Dependencias OK')"
```

## 🧪 Primer Uso - Demo Básico

### Opción 1: Demo Standalone (Sin API)

```bash
python demo_sequential_integrado.py
```

Esto ejecutará un demo completo que:
- ✅ Crea una tabla "estudiantes"
- ✅ Inserta 7 registros
- ✅ Hace búsquedas exactas
- ✅ Hace búsquedas por rango
- ✅ Elimina un registro
- ✅ Muestra toda la tabla
- ✅ Muestra log de operaciones

**Salida esperada**:
```
======================================================================
🚀 DEMO - SEQUENTIAL FILE INTEGRADO
======================================================================

1️⃣  Creando adaptador de base de datos Sequential...
✅ Adaptador creado

2️⃣  Definiendo esquema de tabla 'estudiantes'...
   Creando tabla...
✅ Tabla 'estudiantes' creada

3️⃣  Insertando estudiantes...
   ✅ Insertado: 201910001 - Juan Pérez
   ✅ Insertado: 201910005 - María García
   ...

[más output...]
```

### Opción 2: Prueba Interactiva con Python

```bash
python
```

```python
>>> from Sequential_Struct.sequential_file import SequentialFile
>>> 
>>> # Crear Sequential File
>>> table_format = {"id": "i", "nombre": "50s", "edad": "i"}
>>> seq = SequentialFile(table_format, "id")
>>> 
>>> # Insertar datos
>>> seq.insert([1, "Juan", 25])
True
>>> seq.insert([3, "María", 30])
True
>>> seq.insert([2, "Carlos", 28])
True
>>> 
>>> # Buscar
>>> resultado = seq.search(2)
>>> print(resultado)
[2, 'Carlos', 28]
>>> 
>>> # Ver todos
>>> seq.print_all()
📋 Sequential File
   Índice principal: 3 | Auxiliar: 0 | Total: 3

   [0] { id: 1, nombre: Juan, edad: 25 }
   [1] { id: 2, nombre: Carlos, edad: 28 }
   [2] { id: 3, nombre: María, edad: 30 }
>>> 
>>> # Salir
>>> exit()
```

## 🌐 Iniciar la API REST

### 1. Iniciar el servidor

```bash
# Opción A: Usando uvicorn directamente
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Opción B: Usando el script start.py
python api/start.py
```

**Salida esperada**:
```
🚀 Iniciando API del Parser SQL...
📖 Documentación disponible en: http://localhost:8000/docs
🌐 Frontend disponible en: http://localhost:8000/
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 2. Verificar que funciona

Abrir navegador en:
- **Frontend**: http://localhost:8000
- **Documentación API**: http://localhost:8000/docs
- **API alternativa**: http://localhost:8000/redoc

### 3. Probar con curl

```bash
# Verificar estado del servidor
curl http://localhost:8000/api/status

# Crear una tabla
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "CREATE TABLE productos (codigo INT KEY INDEX SEQ, nombre VARCHAR[100], precio INT);",
    "validate": true
  }'

# Insertar datos
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO productos VALUES (101, \"Laptop HP\", 3500);",
    "validate": true
  }'

# Consultar
curl -X POST http://localhost:8000/api/execute \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM productos WHERE codigo = 101;",
    "validate": true
  }'

# Listar tablas
curl http://localhost:8000/api/tables
```

**Salida esperada** (crear tabla):
```json
{
  "success": true,
  "result": true,
  "parsed_query": "CreateTableQuery(...)",
  "execution_time_ms": 12.34,
  "errors": [],
  "query_type": "CREATE_TABLE"
}
```

## 📝 Ejemplos de Consultas SQL

Una vez que la API está corriendo, puedes ejecutar:

```sql
-- Crear tabla de restaurantes
CREATE TABLE restaurantes (
    id INT KEY INDEX SEQ,
    nombre VARCHAR[50],
    distrito VARCHAR[30],
    rating FLOAT
);

-- Insertar datos
INSERT INTO restaurantes VALUES (1, "La Rosa Náutica", "Miraflores", 4.5);
INSERT INTO restaurantes VALUES (3, "Astrid & Gastón", "San Isidro", 4.8);
INSERT INTO restaurantes VALUES (2, "Central", "Barranco", 4.9);

-- Consultas
SELECT * FROM restaurantes;
SELECT * FROM restaurantes WHERE id = 2;
SELECT * FROM restaurantes WHERE id BETWEEN 1 AND 3;

-- Eliminar
DELETE FROM restaurantes WHERE id = 3;
```

## 🐛 Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'fastapi'"

**Solución**:
```bash
pip install fastapi uvicorn pydantic
```

### Error: "ImportError: cannot import name 'RegistroType'"

**Causa**: Falta el módulo Utils/Registro.py

**Solución**: Verifica que existan estos archivos:
```bash
ls Utils/Registro.py
ls Utils/__init__.py
ls Heap_struct/Heap.py
ls Heap_struct/__init__.py
```

Si faltan, es porque el código no se copió correctamente.

### Error: "Address already in use" (puerto 8000 ocupado)

**Solución**:
```bash
# Opción 1: Usar otro puerto
uvicorn api.main:app --reload --port 8001

# Opción 2: Matar proceso que usa el puerto 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID [PID] /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### La API responde pero las consultas fallan

**Verificar**:
1. Que el Sequential Adapter esté importado en `api/main.py`
2. Que exista el directorio `Sequential_Struct/tables/`
3. Ver logs de la API en la terminal

### Archivos .bin no se crean

**Causa**: Problemas de permisos o directorios

**Solución**:
```bash
# Crear directorio manualmente
mkdir -p Sequential_Struct/tables
mkdir -p Heap_struct

# Dar permisos (Linux/Mac)
chmod -R 755 Sequential_Struct
chmod -R 755 Heap_struct
```

## 📚 Documentación Adicional

- **Integración completa**: `docs/INTEGRACION_SEQUENTIAL.md`
- **Sequential File**: `Sequential_Struct/README_NUEVO.md`
- **Parser SQL**: `docs/DOCUMENTACION_PARSER.md`
- **Resumen de cambios**: `RESUMEN_CAMBIOS.txt`

## 🎓 Tutoriales Paso a Paso

### Tutorial 1: Crear tu primera tabla

```python
from parser.sequential_adapter import SequentialDatabaseAdapter
from parser.ast_nodes import Column, DataType, IndexType

# 1. Crear adaptador
db = SequentialDatabaseAdapter()

# 2. Definir esquema
schema = [
    Column("id", DataType.INT, is_key=True, index_type=IndexType.SEQ),
    Column("nombre", DataType.VARCHAR, type_params={"size": 50}),
]

# 3. Crear tabla
db.create_table("personas", schema)

# 4. Insertar datos
db.add("personas", [1, "Juan"])
db.add("personas", [2, "María"])

# 5. Consultar
resultado = db.search("personas", "id", 1)
print(resultado)  # [1, 'Juan']

# 6. Ver todo
db.print_table("personas")
```

### Tutorial 2: Cargar datos desde CSV

```python
from parser.sequential_adapter import SequentialDatabaseAdapter
from parser.ast_nodes import IndexType
import csv

# 1. Crear archivo CSV
with open("productos.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["codigo", "nombre", "precio"])
    writer.writerows([
        [101, "Laptop", 3500],
        [102, "Mouse", 50],
        [103, "Teclado", 150],
    ])

# 2. Cargar en base de datos
db = SequentialDatabaseAdapter()
db.create_table_from_file(
    table_name="productos",
    file_path="productos.csv",
    index_column="codigo",
    index_type=IndexType.SEQ
)

# 3. Usar la tabla
db.print_table("productos")
```

## 🎉 ¡Listo para usar!

Si llegaste hasta aquí y todo funcionó:

✅ Sequential File instalado y funcionando
✅ Parser SQL integrado
✅ API REST corriendo
✅ Listo para desarrollar tu mini base de datos

**Próximos pasos**:
1. Experimenta con el demo
2. Crea tus propias tablas
3. Integra con tu frontend
4. Agrega más estructuras (B+Tree, Hash, RTree)

---

**¿Necesitas ayuda?**
- Revisa `docs/INTEGRACION_SEQUENTIAL.md`
- Consulta los ejemplos en `demo_sequential_integrado.py`
- Verifica los logs de operaciones con `get_operations_log()`

¡Éxito con tu proyecto! 🚀
