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
    from SIFT_struct.InvertVisualFile import MultimediaImageRetrieval
    from Heap_struct.Heap import Heap
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
        # Formato de la tabla: id, nombre, ruta
        table_format = {"id": "i", "nombre": "100s", "ruta": "200s"}

        # Rutas de archivos
        base_dir = os.path.join(os.path.dirname(__file__), "..")
        data_file = os.path.join("data", "sift", f"{table_name}.heap")
        index_file = os.path.join("data", "sift", f"{table_name}_index.heap")

        # Crear directorio si no existe
        os.makedirs(
            os.path.join(os.path.dirname(__file__), "data", "sift"), exist_ok=True
        )

        # Inicializar el gestor de imágenes SIFT
        sift_image_manager = MultimediaImageRetrieval(
            table_format=table_format,
            key="id",
            data_file_name=data_file,
            index_file_name=index_file,
            base_dir=base_dir,
            z=256,
            n_clusters=100,
            force_create=True,
            ruta_col_name="ruta",
        )

        return {
            "success": True,
            "message": f"Tabla '{table_name}' creada exitosamente con índice SIFT",
            "table_name": table_name,
            "columns": ["id", "nombre", "ruta"],
            "sift_config": {"image_size": 256, "clusters": 100},
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

    # Auto-crear tabla si no existe
    if sift_image_manager is None:
        try:
            print("[SIFT] Creando tabla por primera vez...")
            table_format = {"id": "i", "nombre": "100s", "ruta": "200s"}
            base_dir = os.path.join(os.path.dirname(__file__), "..")
            data_file = os.path.join("data", "sift", "images.heap")
            index_file = os.path.join("data", "sift", "images_index.heap")

            os.makedirs(
                os.path.join(os.path.dirname(__file__), "data", "sift"), exist_ok=True
            )

            sift_image_manager = MultimediaImageRetrieval(
                table_format=table_format,
                key="id",
                data_file_name=data_file,
                index_file_name=index_file,
                base_dir=base_dir,
                z=256,
                n_clusters=50,  # Reducido de 100 a 50 para más velocidad
                force_create=True,
                ruta_col_name="ruta",
            )
            print("[SIFT] Tabla creada exitosamente")
        except Exception as e:
            print(f"[SIFT ERROR] {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error creando tabla automáticamente: {str(e)}",
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
            all_records = sift_image_manager.HEAP.scan_all()
            if all_records:
                max_id = max(record[0] for record in all_records)
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
        print(f"[SIFT] Guardando archivo en disco...")
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ruta relativa para almacenar en la BD
        relative_path = os.path.join(
            "api", "data", "sift", "uploaded_images", image_filename
        )

        # Insertar registro en el heap principal
        print(f"[SIFT] Insertando en heap principal...")
        pos = sift_image_manager.HEAP.insert([image_id, image_name, relative_path])

        # Agregar al índice SIFT (esto puede tomar tiempo)
        print(f"[SIFT] Extrayendo descriptores SIFT y actualizando índice...")
        insert_result = sift_image_manager.insert(pos)

        # Construir mensaje según el resultado
        if insert_result["has_vocabulary"]:
            message = "Imagen subida e indexada exitosamente con TF-IDF"
            print(f"[SIFT] ✓ Imagen indexada con vocabulario (ID: {image_id})")
        else:
            images_count = insert_result.get("images_count", 0)
            message = (
                f"Imagen guardada. Vocabulario pendiente ({images_count}/10 imágenes)"
            )
            print(
                f"[SIFT] ✓ Imagen guardada sin vocabulario aún (ID: {image_id}, {images_count}/10)"
            )

        return {
            "success": True,
            "message": message,
            "image_id": image_id,
            "image_name": image_name,
            "position": pos,
            "path": image_path,
            "has_vocabulary": insert_result["has_vocabulary"],
            "images_count": insert_result.get("images_count", None),
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
async def search_similar_images(file: UploadFile = File(...), k: int = Form(10)):
    """Buscar las k imágenes más similares a una imagen query"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay tabla de imágenes creada")

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

        # Realizar búsqueda KNN usando la ruta temporal
        similar_data = sift_image_manager.knn_search_with_similarity(
            query_temp_path, k=k
        )

        # Obtener información de las imágenes similares
        results = []
        for pos, similarity in similar_data:
            record = sift_image_manager.HEAP.read(pos)
            image_info = {
                "id": record[0],
                "nombre": (
                    record[1].strip()
                    if isinstance(record[1], str)
                    else record[1].decode("utf-8").strip()
                ),
                "similarity": float(similarity),
                "position": pos,
            }
            print(f"[DEBUG] Image result: {image_info}")  # Debug log
            results.append(image_info)

        print(f"[DEBUG] Total results: {len(results)}")  # Debug log
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "k_requested": k,
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
            except:
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
            "message": "No hay tabla de imágenes creada",
        }

    try:
        all_records = sift_image_manager.HEAP.scan_all()

        images = []
        for i, record in enumerate(all_records):
            images.append(
                {
                    "id": record[0],
                    "nombre": (
                        record[1].strip()
                        if isinstance(record[1], str)
                        else record[1].decode("utf-8").strip()
                    ),
                    "ruta": (
                        record[2].strip()
                        if isinstance(record[2], str)
                        else record[2].decode("utf-8").strip()
                    ),
                    "position": i,
                }
            )

        return {"success": True, "images": images, "count": len(images)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listando imágenes: {str(e)}"
        )


@app.get("/api/sift/image/{image_id}")
async def get_image_by_id(image_id: int):
    """Obtener información de una imagen por su ID"""
    global sift_image_manager

    if sift_image_manager is None:
        raise HTTPException(status_code=400, detail="No hay tabla de imágenes creada")

    try:
        all_records = sift_image_manager.HEAP.scan_all()

        for i, record in enumerate(all_records):
            if record[0] == image_id:
                return {
                    "success": True,
                    "image": {
                        "id": record[0],
                        "nombre": (
                            record[1].strip()
                            if isinstance(record[1], str)
                            else record[1].decode("utf-8").strip()
                        ),
                        "ruta": (
                            record[2].strip()
                            if isinstance(record[2], str)
                            else record[2].decode("utf-8").strip()
                        ),
                        "position": i,
                    },
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
        raise HTTPException(status_code=400, detail="No hay tabla de imágenes creada")

    try:
        # Buscar la imagen por ID
        all_records = sift_image_manager.HEAP.scan_all()
        image_path = None

        for record in all_records:
            if record[0] == image_id:
                ruta = (
                    record[2].strip()
                    if isinstance(record[2], str)
                    else record[2].decode("utf-8").strip()
                )
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


# ==================== FIN ENDPOINTS SIFT ====================


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
