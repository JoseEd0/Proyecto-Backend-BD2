# API y Frontend para Parser SQL

## 🚀 Inicio Rápido

### Método 1: Script Automático (Recomendado)
```bash
cd api
python start.py
```

### Método 2: Manual
```bash
cd api
pip install -r requirements.txt
python main.py
```

## 🌐 Acceso a la Aplicación

- **Frontend (Consola SQL):** http://localhost:8000/
- **Documentación API:** http://localhost:8000/docs
- **API Alternativa:** http://localhost:8000/redoc

## 📊 Características del Frontend

### 🖥️ Interfaz de Consola SQL
- **Editor de consultas** con highlighting de sintaxis
- **Ejecución en tiempo real** con Ctrl+Enter
- **Validación** y **parsing** separados
- **Historial** de consultas en consola
- **Ejemplos integrados** por tipo de consulta

### 📋 Panel de Información
- **Lista de tablas activas** con detalles
- **Estado del servidor** en tiempo real
- **Métricas de rendimiento** (tiempo de ejecución)
- **Log de operaciones** del sistema

### ⌨️ Atajos de Teclado
- `Ctrl+Enter`: Ejecutar consulta
- `Ctrl+K`: Limpiar editor
- `F5`: Refrescar lista de tablas

## 🔧 Endpoints de la API

### Ejecutar Consultas
```http
POST /api/execute
Content-Type: application/json

{
  "sql": "CREATE TABLE Test (id INT KEY INDEX SEQ);",
  "validate": true
}
```

### Validar Consultas
```http
GET /api/validate/SELECT * FROM Test;
```

### Parsear Consultas
```http
GET /api/parse/CREATE TABLE Test (id INT KEY);
```

### Gestión de Tablas
```http
GET /api/tables                    # Listar tablas
GET /api/tables/{table_name}       # Info de tabla específica
```

### Sistema
```http
GET /api/status                    # Estado del servidor
GET /api/history                   # Historial de consultas
GET /api/operations                # Log de operaciones
DELETE /api/history                # Limpiar historial
```

### Ejemplos
```http
GET /api/examples                  # Consultas de ejemplo
```

## 💻 Uso del Frontend

### 1. Crear Tablas
```sql
CREATE TABLE Restaurantes (
    id INT KEY INDEX SEQ,
    nombre VARCHAR[50] INDEX BTree,
    ubicacion ARRAY[FLOAT] INDEX RTree
);
```

### 2. Insertar Datos
```sql
INSERT INTO Restaurantes VALUES (1, "La Bella Italia", [12.0462, -77.0428]);
```

### 3. Consultar Datos
```sql
-- Búsqueda simple
SELECT * FROM Restaurantes;

-- Búsqueda por ID
SELECT * FROM Restaurantes WHERE id = 1;

-- Búsqueda espacial
SELECT * FROM Restaurantes WHERE ubicacion IN ([12.05, -77.04], 0.01);
```

### 4. Eliminar Datos
```sql
DELETE FROM Restaurantes WHERE id = 1;
```

## 🎨 Características Visuales

- **Tema oscuro** optimizado para desarrollo
- **Colores semánticos** (verde=éxito, rojo=error, azul=info)
- **Animaciones fluidas** y feedback visual
- **Diseño responsive** para diferentes pantallas
- **Tipografía monospace** para código SQL

## 🛠️ Desarrollo

### Estructura de Archivos
```
api/
├── main.py              # Servidor FastAPI principal
├── start.py             # Script de inicio automático
├── requirements.txt     # Dependencias Python
├── README.md           # Esta documentación
└── static/
    └── index.html      # Frontend de consola SQL
```

### Dependencias
- **FastAPI 0.104.1** - Framework web moderno
- **Uvicorn 0.24.0** - Servidor ASGI de alto rendimiento
- **Pydantic 2.5.0** - Validación de datos

### Características Técnicas
- **CORS configurado** para desarrollo
- **Manejo de errores** robusto
- **Logging completo** de operaciones
- **Validación de entrada** con Pydantic
- **Documentación automática** con OpenAPI

## 🐛 Solución de Problemas

### Puerto ocupado
```bash
# Cambiar puerto en main.py línea 274
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

### Error de importación del parser
```bash
# Verificar que estás en el directorio correcto
cd Proyecto-Backend-BD2/api
python start.py
```

### Dependencias faltantes
```bash
# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

## 📈 Próximas Mejoras

- [ ] Autocompletado SQL en el editor
- [ ] Exportación de resultados (JSON/CSV)
- [ ] Modo oscuro/claro toggle
- [ ] Historial persistente
- [ ] Ejecución de múltiples consultas
- [ ] Visualización de datos espaciales

## 🎯 Integración con Mini Gestor

Este frontend está diseñado para trabajar con el parser SQL y puede extenderse fácilmente para conectarse con el mini gestor de bases de datos real una vez implementado.

---

**Desarrollado para CS2702 - Base de Datos 2 UTEC**  
*Sistema completo de consola SQL con API REST*
