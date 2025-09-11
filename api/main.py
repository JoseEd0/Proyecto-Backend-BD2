"""
API FastAPI para el Parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC

API REST que expone las funcionalidades del parser SQL
para ser consumidas desde el frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sys
import os
import time

# Agregar el parser al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from parser import create_sql_parser_engine
except ImportError as e:
    print(f"Error importando parser: {e}")
    raise

# Crear la aplicación FastAPI
app = FastAPI(
    title="Parser SQL API",
    description="API para ejecutar consultas SQL usando el parser personalizado",
    version="1.0.0",
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

# Motor del parser SQL global
sql_engine = create_sql_parser_engine()


# Modelos Pydantic para las requests/responses
class SQLQuery(BaseModel):
    sql: str
    validate: bool = True


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
        # Ejecutar la consulta
        result = sql_engine.execute_sql(query.sql, validate=query.validate)

        # Determinar el tipo de consulta
        query_type = "unknown"
        if result.get("parsed_query"):
            parsed = result["parsed_query"]
            if hasattr(parsed, "operation_type"):
                query_type = parsed.operation_type.value

        # Formatear la respuesta
        response = SQLResponse(
            success=result["success"],
            result=result.get("result"),
            parsed_query=(
                str(result.get("parsed_query")) if result.get("parsed_query") else None
            ),
            execution_time_ms=result["execution_time_ms"],
            errors=result.get("errors", []),
            query_type=query_type,
        )

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error interno del servidor: {str(e)}"
        )


@app.get("/api/validate/{sql_query}")
async def validate_sql_query(sql_query: str):
    """Validar una consulta SQL sin ejecutarla"""
    try:
        success, errors = sql_engine.validate_only(sql_query)
        return {"valid": success, "errors": errors if not success else []}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error validando consulta: {str(e)}"
        )


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


@app.get("/api/tables/{table_name}", response_model=TableInfo)
async def get_table_info(table_name: str):
    """Obtener información detallada de una tabla"""
    try:
        info = sql_engine.get_table_info(table_name)
        if not info:
            raise HTTPException(
                status_code=404, detail=f"Tabla '{table_name}' no encontrada"
            )

        return TableInfo(name=table_name, columns=info.get("columns", []))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo información de tabla: {str(e)}"
        )


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
    """Obtener ejemplos de consultas SQL"""
    examples = {
        "create_tables": [
            "CREATE TABLE Restaurantes (id INT KEY INDEX SEQ, nombre VARCHAR[50] INDEX BTree, ubicacion ARRAY[FLOAT] INDEX RTree);",
            "CREATE TABLE Productos (codigo INT KEY INDEX Hash, nombre VARCHAR[100], precio INT);",
            'CREATE TABLE Clientes FROM FILE "clientes.csv" USING INDEX ISAM("dni");',
        ],
        "insert_data": [
            'INSERT INTO Restaurantes VALUES (1, "La Bella Italia", [12.0462, -77.0428]);',
            'INSERT INTO Productos VALUES (101, "Pizza Margherita", 25);',
        ],
        "select_queries": [
            "SELECT * FROM Restaurantes;",
            "SELECT * FROM Productos WHERE codigo = 101;",
            "SELECT * FROM Productos WHERE precio BETWEEN 20 AND 50;",
            "SELECT * FROM Restaurantes WHERE ubicacion IN ([12.05, -77.04], 0.01);",
        ],
        "delete_queries": ["DELETE FROM Productos WHERE codigo = 101;"],
    }
    return examples


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
