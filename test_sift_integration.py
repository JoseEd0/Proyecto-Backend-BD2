"""
Test de integración SIFT - Verificación rápida
"""

import sys
import os

# Agregar rutas al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

print("=" * 60)
print("TEST DE INTEGRACIÓN SIFT")
print("=" * 60)

# Test 1: Imports
print("\n[1/5] Verificando imports...")
try:
    from SIFT_struct.InvertVisualFile import MultimediaImageRetrieval
    from Heap_struct.Heap import Heap
    from Utils.Registro import RegistroType

    print("✓ Imports correctos")
except Exception as e:
    print(f"✗ Error en imports: {e}")
    sys.exit(1)

# Test 2: Crear tabla de imágenes
print("\n[2/5] Creando tabla de imágenes...")
try:
    table_format = {"id": "i", "nombre": "100s", "ruta": "200s"}

    base_dir = os.path.dirname(__file__)
    data_file = "test_images_temp.heap"
    index_file = "test_images_index_temp.heap"

    sift_manager = MultimediaImageRetrieval(
        table_format=table_format,
        key="id",
        data_file_name=data_file,
        index_file_name=index_file,
        base_dir=base_dir,
        z=256,
        n_clusters=10,  # Pequeño para test rápido
        force_create=True,
        ruta_col_name="ruta",
    )

    print("✓ Tabla creada correctamente")
except Exception as e:
    print(f"✗ Error creando tabla: {e}")
    sys.exit(1)

# Test 3: Verificar heap principal
print("\n[3/5] Verificando Heap principal...")
try:
    count = sift_manager.HEAP.count()
    print(f"✓ Heap inicializado (registros: {count})")
except Exception as e:
    print(f"✗ Error en Heap: {e}")
    sys.exit(1)

# Test 4: Verificar compatibilidad de métodos
print("\n[4/5] Verificando métodos de compatibilidad...")
try:
    # Verificar que _select_all existe
    assert hasattr(sift_manager.HEAP, "_select_all"), "Falta método _select_all"
    assert hasattr(sift_manager.HEAP, "scan_all"), "Falta método scan_all"

    # Verificar alias en RegistroType
    rt = RegistroType({"id": "i"}, "id")
    assert hasattr(rt, "dict_format"), "Falta alias dict_format"
    assert hasattr(rt, "key"), "Falta alias key"

    print("✓ Todos los métodos de compatibilidad presentes")
except Exception as e:
    print(f"✗ Error en compatibilidad: {e}")
    sys.exit(1)

# Test 5: Limpiar archivos temporales
print("\n[5/5] Limpiando archivos temporales...")
try:
    for file in [data_file, index_file]:
        if os.path.exists(file):
            os.remove(file)

    # Limpiar descriptors si se crearon
    desc_dir = os.path.join(base_dir, "SIFT_struct", "descriptors")
    if os.path.exists(desc_dir):
        for f in os.listdir(desc_dir):
            if f.endswith(".npz") or f.endswith(".pkl"):
                try:
                    os.remove(os.path.join(desc_dir, f))
                except:
                    pass

    print("✓ Archivos temporales eliminados")
except Exception as e:
    print(f"⚠ Advertencia limpiando archivos: {e}")

# Resumen
print("\n" + "=" * 60)
print("✅ TODOS LOS TESTS PASARON")
print("=" * 60)
print("\nLa integración SIFT está lista para usar:")
print("1. cd api")
print("2. python main.py")
print("3. Navegar a http://localhost:8000/static/images.html")
print("=" * 60)
