"""
API FastAPI para el Parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC

API REST que expone las funcionalidades del parser SQL
para ser consumidas desde el frontend.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import time
import csv
import io

# Agregar el parser al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from parser import create_sql_parser_engine
    from parser.unified_adapter import UnifiedDatabaseAdapter
except ImportError as e:
    print(f"Error importando parser: {e}")
    raise

# Crear la aplicación FastAPI
app = FastAPI(
    title="Parser SQL API - Multi-Structure Database Manager",
    description="API para ejecutar consultas SQL con soporte para Sequential, B+Tree, ISAM, Hash y R-Tree",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear adaptador unificado de base de datos
# Soporta Sequential, B+Tree, ISAM, Hash y R-Tree
database_adapter = UnifiedDatabaseAdapter(data_dir="data")

# Motor del parser SQL global con todas las estructuras
sql_engine = create_sql_parser_engine(database_adapter=database_adapter)


# Modelos Pydantic para las requests/responses
class SQLQuery(BaseModel):
    sql: str
    should_validate: bool = True


class SQLResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    parsed_query: Optional[Dict] = None
    execution_time_ms: float
    errors: List[str] = []
    query_type: Optional[str] = None


class TableInfo(BaseModel):
    name: str
    columns: List[Dict[str, Any]]


class ServerStatus(BaseModel):
    status: str
    parser_version: str
    tables_count: int
    uptime_seconds: float


# Variable para tracking del tiempo de inicio
start_time = time.time()

# === ENDPOINTS DE LA API ===


@app.get("/", response_class=FileResponse)
async def read_index():
    """Servir el archivo HTML principal"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/status", response_model=ServerStatus)
async def get_server_status():
    """Obtener el estado del servidor y parser"""
    return ServerStatus(
        status="running",
        parser_version="1.0.0",
        tables_count=len(sql_engine.list_tables()),
        uptime_seconds=time.time() - start_time,
    )


@app.post("/api/execute", response_model=SQLResponse)
async def execute_sql_query(query: SQLQuery):
    """Ejecutar una consulta SQL usando el parser"""
    try:
        # Validación básica de entrada
        if not query.sql or not query.sql.strip():
            raise HTTPException(
                status_code=400, detail="La consulta SQL no puede estar vacía"
            )

        # Validar longitud razonable
        if len(query.sql) > 10000:
            raise HTTPException(
                status_code=400,
                detail="La consulta SQL es demasiado larga (máximo 10,000 caracteres)",
            )

        # Ejecutar la consulta
        result = sql_engine.execute_sql(query.sql, validate=query.should_validate)

        # Determinar el tipo de consulta
        query_type = "unknown"
        if result.get("parsed_query"):
            parsed = result["parsed_query"]
            if hasattr(parsed, "operation_type"):
                query_type = parsed.operation_type.value

        # Formatear la respuesta
        # Convertir parsed_query a dict si existe
        parsed_query_dict = None
        if result.get("parsed_query"):
            parsed = result["parsed_query"]
            if hasattr(parsed, "__dict__"):
                parsed_query_dict = {"type": query_type, "details": str(parsed)}

        response = SQLResponse(
            success=result["success"],
            result=result.get("result"),
            parsed_query=parsed_query_dict,
            execution_time_ms=result["execution_time_ms"],
            errors=result.get("errors", []),
            query_type=query_type,
        )

        return response

    except HTTPException:
        raise
    except ValueError as e:
        # Errores de validación o lógica de negocio
        raise HTTPException(status_code=400, detail=f"Error de validación: {str(e)}")
    except KeyError as e:
        # Errores de claves no encontradas
        raise HTTPException(status_code=404, detail=f"Recurso no encontrado: {str(e)}")
    except Exception as e:
        # Otros errores inesperados
        import traceback

        error_trace = traceback.format_exc()
        print(f"❌ Error inesperado:\n{error_trace}")

        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@app.post("/api/validate")
async def validate_sql_query(query: SQLQuery):
    """Validar una consulta SQL sin ejecutarla"""
    try:
        if not query.sql or not query.sql.strip():
            return {"valid": False, "errors": ["La consulta SQL no puede estar vacía"]}

        success, errors = sql_engine.validate_only(query.sql)

        # Proporcionar mensajes de error más amigables
        friendly_errors = []
        for error in errors:
            if "Se esperaba" in error:
                friendly_errors.append(f"❌ Sintaxis: {error}")
            elif "no existe" in error:
                friendly_errors.append(f"⚠️  {error}")
            else:
                friendly_errors.append(error)

        return {
            "valid": success,
            "errors": friendly_errors if not success else [],
            "message": "Consulta válida ✓" if success else "Consulta contiene errores",
        }
    except Exception as e:
        return {"valid": False, "errors": [f"Error al validar: {str(e)}"]}


@app.get("/api/parse/{sql_query}")
async def parse_sql_query(sql_query: str):
    """Parsear una consulta SQL sin ejecutarla"""
    try:
        success, parsed = sql_engine.parse_only(sql_query)
        return {
            "success": success,
            "parsed_query": str(parsed) if success else None,
            "error": str(parsed) if not success else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error parseando consulta: {str(e)}"
        )


@app.get("/api/tables", response_model=List[str])
async def get_tables():
    """Obtener lista de tablas creadas"""
    try:
        return sql_engine.list_tables()
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo tablas: {str(e)}"
        )


@app.get("/api/tables/{table_name}")
async def get_table_info(table_name: str):
    """Obtener información detallada de una tabla"""
    try:
        info = sql_engine.get_table_info(table_name)
        if not info:
            raise HTTPException(
                status_code=404, detail=f"Tabla '{table_name}' no encontrada"
            )

        # Agregar información sobre la estructura de datos usada
        response = {
            "name": table_name,
            "columns": info.get("columns", []),
            "structure": info.get("structure", "unknown"),
            "record_count": info.get("record_count", 0),
            "metadata": {
                "structure_info": get_structure_description(
                    info.get("structure", "unknown")
                )
            },
        }

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo información de tabla: {str(e)}"
        )


def get_structure_description(structure: str) -> str:
    """Retorna descripción de la estructura de datos"""
    descriptions = {
        "sequential": "✅ Sequential File - Datos ordenados, búsquedas O(log n)",
        "btree": "⚡ B+ Tree - Búsquedas rápidas, excelente para rangos",
        "isam": "📚 ISAM - Óptimo para tablas grandes estáticas",
        "hash": "🚀 Hash - Búsquedas exactas ultra rápidas O(1)",
        "rtree": "🌍 R-Tree - Consultas espaciales optimizadas",
    }
    return descriptions.get(structure, "Estructura de datos no especificada")


@app.get("/api/history")
async def get_query_history(limit: int = 10):
    """Obtener historial de consultas ejecutadas"""
    try:
        history = sql_engine.get_query_history(limit)
        return {"history": history, "total_queries": len(history)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo historial: {str(e)}"
        )


@app.get("/api/operations")
async def get_operations_log():
    """Obtener log de operaciones del adaptador de BD"""
    try:
        operations = sql_engine.get_operations_log()
        return {"operations": operations, "total_operations": len(operations)}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo operaciones: {str(e)}"
        )


@app.delete("/api/history")
async def clear_query_history():
    """Limpiar el historial de consultas"""
    try:
        sql_engine.clear_history()
        return {"message": "Historial limpiado exitosamente"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error limpiando historial: {str(e)}"
        )


@app.get("/api/examples")
async def get_sql_examples():
    """Obtener ejemplos de consultas SQL con todas las estructuras de datos"""
    examples = {
        "create_tables": {
            "sequential": "CREATE TABLE Empleados (id INT KEY INDEX SEQ, nombre VARCHAR[100], salario INT);",
            "btree": "CREATE TABLE Productos (codigo INT KEY INDEX BTree, nombre VARCHAR[100], precio FLOAT);",
            "isam": "CREATE TABLE Clientes (dni INT KEY INDEX ISAM, nombre VARCHAR[100], ciudad VARCHAR[50]);",
            "hash": "CREATE TABLE Usuarios (username VARCHAR[50] KEY INDEX Hash, email VARCHAR[100], edad INT);",
            "rtree": "CREATE TABLE Restaurantes (id INT KEY, nombre VARCHAR[100], ubicacion ARRAY[FLOAT] INDEX RTree);",
        },
        "insert_data": [
            'INSERT INTO Empleados VALUES (1, "Ana García", 3500);',
            'INSERT INTO Empleados VALUES (2, "Carlos López", 4500);',
            'INSERT INTO Productos VALUES (101, "Laptop HP", 999.99);',
            'INSERT INTO Restaurantes VALUES (1, "La Bella Italia", [12.0462, -77.0428]);',
        ],
        "select_queries": {
            "exact_search": "SELECT * FROM Empleados WHERE id = 1;",
            "range_search": "SELECT * FROM Productos WHERE codigo BETWEEN 100 AND 200;",
            "spatial_search": "SELECT * FROM Restaurantes WHERE ubicacion IN ([12.05, -77.04], 0.01);",
            "full_scan": "SELECT * FROM Empleados;",
        },
        "delete_queries": [
            "DELETE FROM Empleados WHERE id = 1;",
            "DELETE FROM Productos WHERE codigo = 101;",
        ],
        "complete_workflow": """-- Flujo completo: CREATE → INSERT → SELECT → DELETE
CREATE TABLE Productos (
    codigo INT KEY INDEX BTree,
    nombre VARCHAR[100],
    precio FLOAT,
    stock INT
);

INSERT INTO Productos VALUES (1, "Laptop Dell", 1299.99, 10);
INSERT INTO Productos VALUES (2, "Mouse Logitech", 25.50, 50);
INSERT INTO Productos VALUES (3, "Teclado Mecánico", 89.99, 30);

SELECT * FROM Productos;

SELECT * FROM Productos WHERE codigo BETWEEN 1 AND 2;

DELETE FROM Productos WHERE codigo = 2;

SELECT * FROM Productos;""",
    }

    return examples


@app.post("/api/upload-csv")
async def upload_csv_file(file: UploadFile = File(...), table_name: str = None):
    """Cargar un archivo CSV y crear una tabla con sus datos"""
    try:
        # Validar que sea un archivo CSV
        if not file.filename:
            raise HTTPException(
                status_code=400, detail="No se proporcionó ningún archivo"
            )

        if not file.filename.endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo debe ser un CSV. Recibido: {file.filename}",
            )

        # Leer el contenido del archivo
        contents = await file.read()
        decoded = contents.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded))

        # Obtener las columnas del CSV
        fieldnames = csv_reader.fieldnames
        if not fieldnames:
            raise HTTPException(
                status_code=400,
                detail="El archivo CSV está vacío o no tiene encabezados",
            )

        # Usar el nombre del archivo como nombre de tabla si no se proporciona
        if not table_name:
            table_name = file.filename.replace(".csv", "").replace(" ", "_")

        # Leer todas las filas para inferir tipos de datos
        rows = list(csv_reader)
        if not rows:
            raise HTTPException(
                status_code=400, detail="El archivo CSV no contiene datos"
            )

        # Inferir tipos de datos basándose en la primera fila
        column_types = []
        for col in fieldnames:
            sample_value = rows[0].get(col, "")

            # Intentar determinar el tipo
            try:
                int(sample_value)
                col_type = "INT"
            except ValueError:
                try:
                    float(sample_value)
                    col_type = "FLOAT"
                except ValueError:
                    # Es un string, determinar tamaño
                    max_len = max(len(str(row.get(col, ""))) for row in rows)
                    col_type = f"VARCHAR[{max(max_len + 10, 50)}]"

            column_types.append((col, col_type))

        # Construir consulta CREATE TABLE
        # La primera columna será la KEY
        columns_def = []
        for i, (col, col_type) in enumerate(column_types):
            if i == 0:
                columns_def.append(f"{col} {col_type} KEY")
            else:
                columns_def.append(f"{col} {col_type}")

        create_table_sql = f"CREATE TABLE {table_name} ({', '.join(columns_def)});"

        # Ejecutar CREATE TABLE
        create_result = sql_engine.execute_sql(create_table_sql, validate=True)

        if not create_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Error creando tabla: {', '.join(create_result.get('errors', []))}",
            )

        # Insertar los datos
        inserted_count = 0
        errors = []

        for row in rows:
            values = []
            for col, col_type in column_types:
                value = row.get(col, "")

                # Formatear el valor según el tipo
                if "INT" in col_type or "FLOAT" in col_type:
                    values.append(str(value) if value else "0")
                else:
                    # Escapar comillas en strings
                    escaped_value = str(value).replace('"', '\\"')
                    values.append(f'"{escaped_value}"')

            insert_sql = f"INSERT INTO {table_name} VALUES ({', '.join(values)});"

            try:
                insert_result = sql_engine.execute_sql(insert_sql, validate=True)
                if insert_result["success"]:
                    inserted_count += 1
                else:
                    errors.append(
                        f"Fila {inserted_count + 1}: {', '.join(insert_result.get('errors', []))}"
                    )
            except Exception as e:
                errors.append(f"Fila {inserted_count + 1}: {str(e)}")

        return {
            "success": True,
            "table_name": table_name,
            "columns": len(fieldnames),
            "rows_processed": len(rows),
            "rows_inserted": inserted_count,
            "errors": errors[:10] if errors else [],  # Limitar a 10 errores
            "create_table_sql": create_table_sql,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error procesando archivo CSV: {str(e)}"
        )


@app.get("/api/table-data/{table_name}")
async def get_table_data(table_name: str, limit: int = 100):
    """Obtener datos de una tabla con límite"""
    try:
        sql = f"SELECT * FROM {table_name};"
        result = sql_engine.execute_sql(sql, validate=True)

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=f"Error obteniendo datos: {', '.join(result.get('errors', []))}",
            )

        # Limitar resultados
        data = result.get("result", [])
        if isinstance(data, list) and len(data) > limit:
            data = data[:limit]
            truncated = True
        else:
            truncated = False

        return {
            "success": True,
            "table_name": table_name,
            "data": data,
            "count": len(data) if isinstance(data, list) else 0,
            "truncated": truncated,
            "limit": limit,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo datos de tabla: {str(e)}"
        )


# Montar archivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Manejar errores 404 para rutas no encontradas
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint no encontrado", "detail": str(exc)}


if __name__ == "__main__":
    import uvicorn

    print("🚀 Iniciando API del Parser SQL...")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    print("🌐 Frontend disponible en: http://localhost:8000/")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
