"""
API FastAPI para el Parser SQL
Proyecto CS2702 - Base de Datos 2 UTEC

API REST que expone las funcionalidades del parser SQL
para ser consumidas desde el frontend.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
import shutil
from pathlib import Path

# Agregar el parser al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from parser import create_sql_parser_engine
    from parser.unified_adapter import UnifiedDatabaseAdapter
    from SIFT_struct.SIFTEngine import SIFTEngine, SIFTConfig
    from Heap_struct.Heap import Heap
    from inverted_index.indexer import SPIMIIndexer
    from inverted_index.query_engine import QueryEngine
    from inverted_index.preprocessing import TextPreprocessor
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

# Gestor de imágenes SIFT
sift_image_manager = None  # Se inicializará cuando se cree una tabla de imágenes

# Gestor de BOW (Bag of Words)
bow_indexer = None  # SPIMIIndexer para crear índices
bow_query_engine = None  # QueryEngine para búsquedas
bow_preprocessor = TextPreprocessor(language="spanish")
BOW_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "bow")
os.makedirs(BOW_DATA_DIR, exist_ok=True)

# Directorio para almacenar imágenes subidas
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "data", "sift", "uploaded_images")
os.makedirs(IMAGES_DIR, exist_ok=True)


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


# ==================== ENDPOINTS PARA SIFT (BÚSQUEDA DE IMÁGENES) ====================


@app.post("/api/sift/create-table")
async def create_sift_table(table_name: str = "ImagenesMultimedia"):
    """Crear tabla para almacenar imágenes con índice SIFT"""
    global sift_image_manager

    try:
        # Rutas de archivos
        base_dir = os.path.join(os.path.dirname(__file__), "..")

        # Configuración optimizada
        config = SIFTConfig(
            image_size=512,
            use_root_sift=True,
            min_images_for_vocab=10,
            use_inverted_index=True,
        )

        # Inicializar el motor SIFT
        sift_image_manager = SIFTEngine(
            base_dir=base_dir,
            data_dir="api/data/sift",
            config=config,
            force_create=True,
        )

        return {
            "success": True,
            "message": f"Tabla '{table_name}' creada exitosamente con índice SIFT",
            "table_name": table_name,
            "columns": ["id", "nombre", "ruta"],
            "sift_config": {
                "image_size": config.image_size,
                "min_images_for_vocab": config.min_images_for_vocab,
                "use_inverted_index": config.use_inverted_index,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creando tabla SIFT: {str(e)}"
        )


@app.post("/api/sift/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    image_id: Optional[int] = Form(None),
    image_name: Optional[str] = Form(None),
):
    """Subir una imagen y agregarla al índice SIFT"""
    global sift_image_manager

    # Auto-crear motor si no existe
    if sift_image_manager is None:
        try:
            print("[SIFT] Creando motor por primera vez...")
            base_dir = os.path.join(os.path.dirname(__file__), "..")

            config = SIFTConfig(
                image_size=512,
                use_root_sift=True,
                min_images_for_vocab=10,
                use_inverted_index=True,
            )

            sift_image_manager = SIFTEngine(
                base_dir=base_dir,
                data_dir="api/data/sift",
                config=config,
                force_create=False,
            )
            print("[SIFT] Motor creado exitosamente")
        except Exception as e:
            print(f"[SIFT ERROR] {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creando motor SIFT: {str(e)}",
            )

    try:
        print(f"[SIFT] Procesando imagen: {file.filename}")

        # Validar que sea una imagen
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo debe ser una imagen. Tipo recibido: {file.content_type}",
            )

        # Auto-generar ID si no se proporciona
        if image_id is None:
            all_images = sift_image_manager.get_all_images()
            if all_images:
                max_id = max(img["id"] for img in all_images)
                image_id = max_id + 1
            else:
                image_id = 1

        print(f"[SIFT] Asignado ID: {image_id}")

        # Generar nombre si no se proporciona
        if not image_name:
            image_name = os.path.splitext(file.filename)[0]

        # Guardar la imagen en el directorio de imágenes
        file_extension = os.path.splitext(file.filename)[1]
        image_filename = f"{image_name}_{image_id}{file_extension}"
        image_path = os.path.join(IMAGES_DIR, image_filename)

        # Guardar el archivo
        print("[SIFT] Guardando archivo en disco...")
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Agregar al índice SIFT
        print("[SIFT] Extrayendo descriptores SIFT y actualizando índice...")
        result = sift_image_manager.add_image(image_id, image_name, image_path)

        if not result["success"]:
            # Limpiar archivo si hay error
            if os.path.exists(image_path):
                os.remove(image_path)
            raise HTTPException(
                status_code=400, detail=result.get("error", "Error desconocido")
            )

        # Construir mensaje según el resultado
        if result.get("has_vocabulary"):
            message = "Imagen subida e indexada exitosamente con TF-IDF"
            print(f"[SIFT] ✓ Imagen indexada (ID: {image_id})")
        else:
            images_needed = result.get("images_needed", 0)
            message = f"Imagen guardada. Vocabulario pendiente (faltan {images_needed} imágenes)"
            print(f"[SIFT] ✓ Imagen guardada, vocabulario pendiente (ID: {image_id})")

        return {
            "success": True,
            "message": message,
            "image_id": image_id,
            "image_name": image_name,
            "position": result.get("position"),
            "path": image_path,
            "has_vocabulary": result.get("has_vocabulary", False),
            "descriptors": result.get("descriptors", 0),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SIFT ERROR] {str(e)}")
        import traceback

        traceback.print_exc()
        # Limpiar archivo si hay error
        if "image_path" in locals() and os.path.exists(image_path):
            os.remove(image_path)
        raise HTTPException(status_code=500, detail=f"Error subiendo imagen: {str(e)}")


@app.post("/api/sift/search-similar")
async def search_similar_images(
    file: UploadFile = File(...), k: int = Form(10), use_inverted: bool = Form(True)
):
    """Buscar las k imágenes más similares a una imagen query"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay motor SIFT inicializado")

    query_temp_path = None
    try:
        # Validar que sea una imagen
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo debe ser una imagen. Tipo recibido: {file.content_type}",
            )

        # Guardar temporalmente la imagen query
        query_temp_path = os.path.join(
            IMAGES_DIR, f"query_temp_{int(time.time() * 1000)}.jpg"
        )
        with open(query_temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Realizar búsqueda KNN
        similar_data = sift_image_manager.search(
            query_temp_path, k=k, use_inverted=use_inverted
        )

        # Formatear resultados
        results = []
        for pos, similarity, info in similar_data:
            image_info = {
                "id": info.get("id", pos),
                "nombre": info.get("nombre", f"image_{pos}"),
                "similarity": float(similarity),
                "position": pos,
            }
            print(f"[DEBUG] Image result: {image_info}")
            results.append(image_info)

        print(f"[DEBUG] Total results: {len(results)}")
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "k_requested": k,
            "search_method": "inverted_index" if use_inverted else "sequential",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error buscando imágenes similares: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal
        if query_temp_path and os.path.exists(query_temp_path):
            try:
                os.remove(query_temp_path)
            except Exception:
                pass


@app.get("/api/sift/images")
async def list_all_images():
    """Listar todas las imágenes en el sistema"""
    global sift_image_manager

    if sift_image_manager is None:
        return {
            "success": True,
            "images": [],
            "count": 0,
            "message": "No hay motor SIFT inicializado",
        }

    try:
        images = sift_image_manager.get_all_images()

        return {"success": True, "images": images, "count": len(images)}

    except Exception as e:
        print(f"[ERROR] Error listando imágenes: {str(e)}")
        return {
            "success": True,
            "images": [],
            "count": 0,
            "message": f"Error cargando imágenes: {str(e)}",
        }


@app.get("/api/sift/image/{image_id}")
async def get_image_by_id(image_id: int):
    """Obtener información de una imagen por su ID"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay motor SIFT inicializado")

    try:
        images = sift_image_manager.get_all_images()

        for img in images:
            if img["id"] == image_id:
                return {
                    "success": True,
                    "image": img,
                }

        raise HTTPException(
            status_code=404, detail=f"Imagen con ID {image_id} no encontrada"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo imagen: {str(e)}"
        )


@app.get("/api/sift/image-file/{image_id}")
async def get_image_file(image_id: int):
    """Obtener el archivo de imagen por su ID"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay motor SIFT inicializado")

    try:
        images = sift_image_manager.get_all_images()
        image_path = None

        for img in images:
            if img["id"] == image_id:
                ruta = img["ruta"]
                # Convertir ruta relativa a absoluta
                image_path = os.path.join(os.path.dirname(__file__), "..", ruta)
                break

        if not image_path or not os.path.exists(image_path):
            raise HTTPException(
                status_code=404,
                detail=f"Archivo de imagen no encontrado para ID {image_id}",
            )

        return FileResponse(
            image_path,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo archivo de imagen: {str(e)}"
        )


@app.get("/api/sift/stats")
async def get_sift_stats():
    """Obtener estadísticas del índice SIFT"""
    global sift_image_manager

    if sift_image_manager is None:
        return {"success": False, "message": "No hay motor SIFT inicializado"}

    try:
        stats = sift_image_manager.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@app.post("/api/sift/rebuild")
async def rebuild_sift_index():
    """Reconstruir el índice SIFT completo"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay motor SIFT inicializado")

    try:
        result = sift_image_manager.rebuild_index()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reconstruyendo índice: {str(e)}"
        )


# ==================== FIN ENDPOINTS SIFT ====================


# ==================== ENDPOINTS PARA BOW (BAG OF WORDS) ====================


@app.post("/api/bow/create-index")
async def create_bow_index(collection_name: str = "bow_collection"):
    """Crear un índice BOW nuevo"""
    global bow_indexer, bow_query_engine

    try:
        # Crear directorio específico para esta colección
        index_dir = os.path.join(BOW_DATA_DIR, collection_name)
        os.makedirs(index_dir, exist_ok=True)

        # Inicializar indexer
        bow_indexer = SPIMIIndexer(block_size_limit=10000, output_dir=index_dir)

        return {
            "success": True,
            "message": f"Índice BOW '{collection_name}' creado exitosamente",
            "collection_name": collection_name,
            "index_dir": index_dir,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creando índice BOW: {str(e)}"
        )


@app.post("/api/bow/upload-documents")
async def upload_documents(
    files: List[UploadFile] = File(...), collection_name: str = Form("bow_collection")
):
    """Subir múltiples documentos de texto y agregarlos al índice BOW"""
    global bow_indexer, bow_query_engine

    try:
        # Crear o cargar índice si no existe
        index_dir = os.path.join(BOW_DATA_DIR, collection_name)

        if bow_indexer is None:
            os.makedirs(index_dir, exist_ok=True)
            bow_indexer = SPIMIIndexer(block_size_limit=10000, output_dir=index_dir)

        processed_docs = []
        errors = []

        for idx, file in enumerate(files):
            try:
                # Validar que sea archivo de texto
                if not file.filename.endswith((".txt", ".text")):
                    errors.append(f"{file.filename}: Solo se aceptan archivos .txt")
                    continue

                # Leer contenido
                content = await file.read()
                text = content.decode("utf-8")

                # Preprocesar texto
                tokens = bow_preprocessor.preprocess(text)

                if not tokens:
                    errors.append(f"{file.filename}: No se encontraron tokens válidos")
                    continue

                # Agregar documento al índice
                doc_id = idx + 1
                bow_indexer.add_document(doc_id, tokens)

                processed_docs.append(
                    {
                        "doc_id": doc_id,
                        "filename": file.filename,
                        "tokens_count": len(tokens),
                    }
                )

            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")

        # Escribir último bloque si existe
        if bow_indexer.dictionary:
            bow_indexer.write_block_to_disk()

        return {
            "success": True,
            "message": f"Documentos procesados: {len(processed_docs)}",
            "collection_name": collection_name,
            "processed_documents": processed_docs,
            "errors": errors,
            "total_blocks": bow_indexer.block_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error subiendo documentos: {str(e)}"
        )


@app.post("/api/bow/build-index")
async def build_bow_index(
    collection_name: str = Form("bow_collection"), total_docs: int = Form(...)
):
    """Construir el índice final: merge blocks + TF-IDF"""
    global bow_indexer, bow_query_engine

    try:
        index_dir = os.path.join(BOW_DATA_DIR, collection_name)

        if not os.path.exists(index_dir):
            raise HTTPException(
                status_code=404, detail=f"Colección '{collection_name}' no encontrada"
            )

        # Si el indexer no está cargado, necesitamos recrearlo para merge
        if bow_indexer is None or bow_indexer.output_dir != index_dir:
            bow_indexer = SPIMIIndexer(block_size_limit=10000, output_dir=index_dir)
            # Contar bloques existentes
            block_files = [f for f in os.listdir(index_dir) if f.startswith("block_")]
            bow_indexer.block_count = len(block_files)

        # Merge blocks
        bow_indexer.merge_blocks()

        # Compute TF-IDF
        bow_indexer.compute_tfidf_and_norms(total_docs)

        # Inicializar query engine
        bow_query_engine = QueryEngine(index_dir=index_dir)

        return {
            "success": True,
            "message": "Índice construido exitosamente con TF-IDF",
            "collection_name": collection_name,
            "total_documents": total_docs,
            "vocabulary_size": len(bow_query_engine.vocabulary),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error construyendo índice: {str(e)}"
        )


@app.post("/api/bow/search")
async def search_bow(
    query: str = Form(...),
    k: int = Form(10),
    collection_name: str = Form("bow_collection"),
):
    """Buscar documentos similares a una consulta usando BOW + TF-IDF"""
    global bow_query_engine

    try:
        index_dir = os.path.join(BOW_DATA_DIR, collection_name)

        # Cargar query engine si no está cargado
        if bow_query_engine is None or bow_query_engine.index_dir != index_dir:
            if not os.path.exists(os.path.join(index_dir, "tfidf_index.dat")):
                raise HTTPException(
                    status_code=404,
                    detail=f"Índice '{collection_name}' no encontrado. Primero suba documentos y construya el índice.",
                )
            bow_query_engine = QueryEngine(index_dir=index_dir)

        # Realizar búsqueda
        results = bow_query_engine.search(query, k=k)

        # Formatear resultados
        formatted_results = [
            {
                "doc_id": doc_id,
                "score": float(score),
                "similarity_percentage": round(score * 100, 2),
            }
            for doc_id, score in results
        ]

        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results),
            "k_requested": k,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda: {str(e)}")


@app.get("/api/bow/collections")
async def list_bow_collections():
    """Listar todas las colecciones BOW disponibles"""
    try:
        if not os.path.exists(BOW_DATA_DIR):
            return {"success": True, "collections": [], "count": 0}

        collections = []
        for item in os.listdir(BOW_DATA_DIR):
            item_path = os.path.join(BOW_DATA_DIR, item)
            if os.path.isdir(item_path):
                # Verificar si tiene índice construido
                has_index = os.path.exists(os.path.join(item_path, "tfidf_index.dat"))

                # Contar documentos si existe el índice
                doc_count = 0
                vocab_size = 0

                if has_index:
                    norms_file = os.path.join(item_path, "doc_norms.dat")
                    if os.path.exists(norms_file):
                        with open(norms_file, "rb") as f:
                            doc_norms = pickle.load(f)
                            doc_count = len(doc_norms)

                    # Contar vocabulario
                    temp_engine = QueryEngine(index_dir=item_path)
                    vocab_size = len(temp_engine.vocabulary)

                collections.append(
                    {
                        "name": item,
                        "has_index": has_index,
                        "documents_count": doc_count,
                        "vocabulary_size": vocab_size,
                    }
                )

        return {"success": True, "collections": collections, "count": len(collections)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listando colecciones: {str(e)}"
        )


@app.delete("/api/bow/collection/{collection_name}")
async def delete_bow_collection(collection_name: str):
    """Eliminar una colección BOW completa"""
    global bow_indexer, bow_query_engine

    try:
        index_dir = os.path.join(BOW_DATA_DIR, collection_name)

        if not os.path.exists(index_dir):
            raise HTTPException(
                status_code=404, detail=f"Colección '{collection_name}' no encontrada"
            )

        # Limpiar referencias globales si es la colección activa
        if bow_indexer and bow_indexer.output_dir == index_dir:
            bow_indexer = None
        if bow_query_engine and bow_query_engine.index_dir == index_dir:
            bow_query_engine = None

        # Eliminar directorio
        shutil.rmtree(index_dir)

        return {
            "success": True,
            "message": f"Colección '{collection_name}' eliminada exitosamente",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error eliminando colección: {str(e)}"
        )


# ==================== FIN ENDPOINTS BOW ====================


# Montar archivos estáticos del build de React
static_dir = os.path.join(os.path.dirname(__file__), "static")
dist_dir = os.path.join(static_dir, "dist")

# Servir el build de React
if os.path.exists(dist_dir):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(dist_dir, "assets")),
        name="assets",
    )


@app.get("/")
async def read_root():
    """Servir la aplicación React"""
    dist_index = os.path.join(os.path.dirname(__file__), "static", "dist", "index.html")

    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    else:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Frontend not found. Please run 'npm run build' in the frontend directory."
            },
        )


# Catch-all route para React Router (debe ir al final)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Servir la aplicación React para todas las rutas no API"""
    # Si es una ruta API, dejar que FastAPI maneje el 404
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Servir el index.html de React para client-side routing
    dist_index = os.path.join(os.path.dirname(__file__), "static", "dist", "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)

    raise HTTPException(status_code=404, detail="Route not found")


# Manejar errores 404 para rutas API no encontradas
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404, content={"error": "Endpoint no encontrado", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    print("🚀 Iniciando API del Parser SQL...")
    print("📖 Documentación disponible en: http://localhost:8000/docs")
    print("🌐 Frontend disponible en: http://localhost:8000/")

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
