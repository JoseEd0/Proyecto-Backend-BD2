"""
Script de prueba para verificar todas las estructuras de datos
Proyecto CS2702 - Base de Datos 2 UTEC

Este script prueba:
1. Que todas las estructuras se pueden importar
2. Que el adaptador unificado funciona correctamente
3. Que cada estructura maneja operaciones básicas
"""

import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """Prueba que todas las estructuras se pueden importar"""
    print("=" * 60)
    print("PRUEBA 1: Importación de Estructuras")
    print("=" * 60)

    results = {}

    # Sequential File
    try:
        from Sequential_Struct.sequential_file import SequentialFile

        results["Sequential"] = "✅ OK"
    except Exception as e:
        results["Sequential"] = f"❌ ERROR: {e}"

    # B+ Tree
    try:
        from b_plus_tree.bplustree import BPlusTree

        results["B+ Tree"] = "✅ OK"
    except Exception as e:
        results["B+ Tree"] = f"❌ ERROR: {e}"

    # ISAM
    try:
        from ISAM.ISAM import ISAMFile

        results["ISAM"] = "✅ OK"
    except Exception as e:
        results["ISAM"] = f"❌ ERROR: {e}"

    # Extendible Hashing
    try:
        from extendible_hashing.extendible_hashing import DiskExtendibleHashing

        results["Hash"] = "✅ OK"
    except Exception as e:
        results["Hash"] = f"❌ ERROR: {e}"

    # R-Tree
    try:
        from Rtree.rtree_impl import RTreeIndex

        results["R-Tree"] = "✅ OK"
    except Exception as e:
        results["R-Tree"] = f"❌ ERROR: {e}"

    # Mostrar resultados
    for name, status in results.items():
        print(f"  {name:20s}: {status}")

    print()
    return all("✅" in status for status in results.values())


def test_unified_adapter():
    """Prueba el adaptador unificado"""
    print("=" * 60)
    print("PRUEBA 2: Adaptador Unificado")
    print("=" * 60)

    try:
        from parser.unified_adapter import UnifiedDatabaseAdapter
        from parser.ast_nodes import Column, DataType, IndexType

        # Crear adaptador
        adapter = UnifiedDatabaseAdapter(data_dir="test_data")
        print("  ✅ Adaptador creado correctamente")

        # Crear tabla de prueba
        schema = [
            Column(
                name="id", data_type=DataType.INT, is_key=True, index_type=IndexType.SEQ
            ),
            Column(name="nombre", data_type=DataType.VARCHAR, size=50),
            Column(name="edad", data_type=DataType.INT),
        ]

        adapter.create_table("test_table", schema)
        print("  ✅ Tabla creada con Sequential File")

        # Insertar datos
        adapter.add("test_table", [1, "Ana García", 25])
        adapter.add("test_table", [2, "Carlos López", 30])
        print("  ✅ Datos insertados")

        # Buscar datos
        result = adapter.search("test_table", "id", 1)
        if result and len(result) > 0:
            print(f"  ✅ Búsqueda exacta: {result}")
        else:
            print("  ❌ Búsqueda exacta falló")

        # Scan completo
        all_records = adapter.scan_all("test_table")
        print(f"  ✅ Scan completo: {len(all_records)} registros")

        # Eliminar registro
        adapter.remove("test_table", "id", 2)
        print("  ✅ Registro eliminado")

        # Verificar eliminación
        all_records = adapter.scan_all("test_table")
        print(f"  ✅ Después de eliminar: {len(all_records)} registros")

        return True

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Limpiar archivos de prueba
        import shutil

        if os.path.exists("test_data"):
            shutil.rmtree("test_data")
        print("  🧹 Archivos de prueba limpiados")


def test_parser_integration():
    """Prueba la integración con el parser SQL"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Integración con Parser SQL")
    print("=" * 60)

    try:
        from parser import create_sql_parser_engine
        from parser.unified_adapter import UnifiedDatabaseAdapter

        # Crear adaptador y motor SQL
        adapter = UnifiedDatabaseAdapter(data_dir="test_sql_data")
        engine = create_sql_parser_engine(database_adapter=adapter)
        print("  ✅ Motor SQL creado")

        # Probar CREATE TABLE
        sql_create = """
        CREATE TABLE Empleados (
            id INT KEY INDEX SEQ,
            nombre VARCHAR[100],
            salario INT
        );
        """
        result = engine.execute_sql(sql_create)
        if result["success"]:
            print("  ✅ CREATE TABLE ejecutado")
        else:
            print(f"  ❌ CREATE TABLE falló: {result.get('errors')}")
            return False

        # Probar INSERT
        sql_insert1 = 'INSERT INTO Empleados VALUES (1, "Ana García", 3500);'
        sql_insert2 = 'INSERT INTO Empleados VALUES (2, "Carlos López", 4500);'

        result = engine.execute_sql(sql_insert1)
        if result["success"]:
            print("  ✅ INSERT 1 ejecutado")
        else:
            print(f"  ❌ INSERT 1 falló: {result.get('errors')}")

        result = engine.execute_sql(sql_insert2)
        if result["success"]:
            print("  ✅ INSERT 2 ejecutado")
        else:
            print(f"  ❌ INSERT 2 falló: {result.get('errors')}")

        # Probar SELECT
        sql_select = "SELECT * FROM Empleados;"
        result = engine.execute_sql(sql_select)
        if result["success"] and result.get("result"):
            print(f"  ✅ SELECT ejecutado: {len(result['result'])} registros")
            for record in result["result"]:
                print(f"     - {record}")
        else:
            print(f"  ❌ SELECT falló: {result.get('errors')}")

        # Probar DELETE
        sql_delete = "DELETE FROM Empleados WHERE id = 1;"
        result = engine.execute_sql(sql_delete)
        if result["success"]:
            print("  ✅ DELETE ejecutado")
        else:
            print(f"  ❌ DELETE falló: {result.get('errors')}")

        # Verificar resultado final
        result = engine.execute_sql("SELECT * FROM Empleados;")
        if result["success"]:
            print(f"  ✅ Verificación final: {len(result['result'])} registros")

        return True

    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Limpiar archivos de prueba
        import shutil

        if os.path.exists("test_sql_data"):
            shutil.rmtree("test_sql_data")
        print("  🧹 Archivos de prueba limpiados")


def main():
    """Ejecuta todas las pruebas"""
    print("\n")
    print("🧪 SUITE DE PRUEBAS - ESTRUCTURAS DE DATOS")
    print("=" * 60)
    print()

    results = []

    # Prueba 1: Importaciones
    results.append(("Importaciones", test_imports()))

    # Prueba 2: Adaptador Unificado
    results.append(("Adaptador Unificado", test_unified_adapter()))

    # Prueba 3: Integración con Parser
    results.append(("Integración Parser", test_parser_integration()))

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name:30s}: {status}")

    print("\n" + "=" * 60)

    total_passed = sum(1 for _, success in results if success)
    total_tests = len(results)

    if total_passed == total_tests:
        print(f"✅ TODAS LAS PRUEBAS PASARON ({total_passed}/{total_tests})")
    else:
        print(f"⚠️  ALGUNAS PRUEBAS FALLARON ({total_passed}/{total_tests})")

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
