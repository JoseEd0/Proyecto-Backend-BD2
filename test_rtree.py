import unittest
import os
import tempfile
import shutil
from rtree_impl import RTreeIndex, Point, SpatialRecord, create_record, create_point_from_coordinates


class TestPoint(unittest.TestCase):
    """Tests para la clase Point"""

    def test_point_creation(self):
        """Test creación básica de puntos"""
        point = Point([10.0, 20.0])
        self.assertEqual(point.coordinates, [10.0, 20.0])
        self.assertEqual(point.dimension, 2)
        self.assertIsNotNone(point.id)

    def test_point_with_id(self):
        """Test creación de punto con ID específico"""
        point = Point([5.0, 15.0], id="test_id")
        self.assertEqual(point.id, "test_id")
        self.assertEqual(point.coordinates, [5.0, 15.0])

    def test_3d_point(self):
        """Test punto 3D"""
        point = Point([1.0, 2.0, 3.0])
        self.assertEqual(point.dimension, 3)
        self.assertEqual(point.coordinates, [1.0, 2.0, 3.0])

    def test_distance_calculation(self):
        """Test cálculo de distancia entre puntos"""
        point1 = Point([0.0, 0.0])
        point2 = Point([3.0, 4.0])

        distance = point1.distance_to(point2)
        self.assertAlmostEqual(distance, 5.0, places=5)

    def test_distance_different_dimensions(self):
        """Test error al calcular distancia con diferentes dimensiones"""
        point1 = Point([0.0, 0.0])
        point2 = Point([0.0, 0.0, 0.0])

        with self.assertRaises(ValueError):
            point1.distance_to(point2)


class TestSpatialRecord(unittest.TestCase):
    """Tests para la clase SpatialRecord"""

    def test_record_creation(self):
        """Test creación básica de registro espacial"""
        point = Point([10.0, 20.0])
        data = {"nombre": "Test", "valor": 123}
        record = SpatialRecord("1", point, data)

        self.assertEqual(record.id, "1")
        self.assertEqual(record.location, point)
        self.assertEqual(record.data, data)

    def test_record_serialization(self):
        """Test serialización y deserialización de registros"""
        point = Point([5.0, 15.0])
        data = {"test": "data"}
        record = SpatialRecord("test_id", point, data)

        # Serializar
        record_dict = record.to_dict()

        # Deserializar
        restored_record = SpatialRecord.from_dict(record_dict)

        self.assertEqual(restored_record.id, record.id)
        self.assertEqual(restored_record.location.coordinates, record.location.coordinates)
        self.assertEqual(restored_record.data, record.data)


class TestRTreeIndex(unittest.TestCase):
    """Tests para la clase RTreeIndex"""

    def setUp(self):
        """Configuración inicial para cada test"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_rtree")
        self.rtree = RTreeIndex(self.test_file, dimension=2)

        # Datos de prueba
        self.test_records = [
            create_record("1", [10.0, 20.0], {"nombre": "A", "tipo": "restaurant"}),
            create_record("2", [15.0, 25.0], {"nombre": "B", "tipo": "hotel"}),
            create_record("3", [50.0, 80.0], {"nombre": "C", "tipo": "tienda"}),
            create_record("4", [12.0, 22.0], {"nombre": "D", "tipo": "cafe"})
        ]

    def tearDown(self):
        """Limpieza después de cada test"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_records(self):
        """Test inserción de registros"""
        for record in self.test_records:
            result = self.rtree.add(record)
            self.assertTrue(result)

        self.assertEqual(self.rtree.size(), len(self.test_records))

    def test_search_by_id(self):
        """Test búsqueda por ID"""
        record = self.test_records[0]
        self.rtree.add(record)

        found = self.rtree.search(record.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, record.id)
        self.assertEqual(found.data["nombre"], record.data["nombre"])

    def test_remove_record(self):
        """Test eliminación de registros"""
        record = self.test_records[0]
        self.rtree.add(record)

        # Verificar que existe
        self.assertEqual(self.rtree.size(), 1)

        # Eliminar
        result = self.rtree.remove(record.id)
        self.assertTrue(result)
        self.assertEqual(self.rtree.size(), 0)

        # Verificar que no existe
        found = self.rtree.search(record.id)
        self.assertIsNone(found)

    def test_remove_nonexistent(self):
        """Test eliminación de registro inexistente"""
        result = self.rtree.remove("nonexistent_id")
        self.assertFalse(result)

    def test_range_search(self):
        """Test búsqueda por rango espacial"""
        # Insertar registros
        for record in self.test_records:
            self.rtree.add(record)

        # Buscar cerca del punto [11, 21] con radio 5
        center = Point([11.0, 21.0])
        radius = 5.0
        results = self.rtree.range_search(center, radius)

        # Deberían encontrarse los registros A y D (están cerca)
        self.assertGreater(len(results), 0)
        nombres_encontrados = {r.data["nombre"] for r in results}
        self.assertIn("A", nombres_encontrados)  # [10, 20] está a distancia ~1.4
        self.assertIn("D", nombres_encontrados)  # [12, 22] está a distancia ~1.4

    def test_range_search_empty(self):
        """Test búsqueda por rango en área vacía"""
        for record in self.test_records:
            self.rtree.add(record)

        center = Point([1000.0, 1000.0])  # Punto lejano
        results = self.rtree.range_search(center, 1.0)

        self.assertEqual(len(results), 0)

    def test_knn_search(self):
        """Test búsqueda de K vecinos más cercanos"""
        for record in self.test_records:
            self.rtree.add(record)

        # Buscar 2 vecinos más cercanos al punto [11, 21]
        query_point = Point([11.0, 21.0])
        k = 2
        results = self.rtree.k_nearest_neighbors(query_point, k)

        self.assertEqual(len(results), k)

        # Verificar que están ordenados por distancia
        distances = [distance for _, distance in results]
        self.assertEqual(distances, sorted(distances))

    def test_knn_search_more_than_available(self):
        """Test KNN con K mayor al número de registros"""
        record = self.test_records[0]
        self.rtree.add(record)

        query_point = Point([0.0, 0.0])
        results = self.rtree.k_nearest_neighbors(query_point, 5)  # Pedir 5, solo hay 1

        self.assertEqual(len(results), 1)

    def test_3d_points(self):
        """Test con puntos 3D"""
        rtree_3d = RTreeIndex(os.path.join(self.temp_dir, "test_3d"), dimension=3)

        record_3d = create_record("1", [1.0, 2.0, 3.0], {"nombre": "3D Point"})
        result = rtree_3d.add(record_3d)
        self.assertTrue(result)

        found = rtree_3d.search("1")
        self.assertIsNotNone(found)
        self.assertEqual(found.location.dimension, 3)

    def test_wrong_dimension(self):
        """Test error con dimensión incorrecta"""
        # El índice es 2D, intentar insertar punto 3D
        record_3d = create_record("1", [1.0, 2.0, 3.0], {"nombre": "Wrong Dimension"})
        result = self.rtree.add(record_3d)
        self.assertFalse(result)  # Debería fallar

    def test_clear_index(self):
        """Test limpieza completa del índice"""
        for record in self.test_records:
            self.rtree.add(record)

        self.assertGreater(self.rtree.size(), 0)

        self.rtree.clear()
        self.assertEqual(self.rtree.size(), 0)

    def test_add_duplicate_id(self):
        """Test inserción de registros con ID duplicado"""
        record1 = create_record("duplicate", [1.0, 1.0], {"data": "first"})
        record2 = create_record("duplicate", [2.0, 2.0], {"data": "second"})

        result1 = self.rtree.add(record1)
        result2 = self.rtree.add(record2)

        self.assertTrue(result1)
        self.assertTrue(result2)  # Debería permitir duplicados (sobrescribir)

        found = self.rtree.search("duplicate")
        self.assertIsNotNone(found)
        # El último insertado debería prevalecer
        self.assertEqual(found.data["data"], "second")

    def test_persistence(self):
        """Test persistencia de datos"""
        # Insertar datos
        for record in self.test_records:
            self.rtree.add(record)

        original_size = self.rtree.size()

        # Guardar explícitamente
        self.rtree.save_data()

        # Crear nuevo índice con el mismo archivo
        rtree2 = RTreeIndex(self.test_file, dimension=2)

        # Verificar que se cargaron los datos
        self.assertEqual(rtree2.size(), original_size)

        # Verificar que se puede buscar un registro específico
        found = rtree2.search(self.test_records[0].id)
        self.assertIsNotNone(found)
        self.assertEqual(found.data["nombre"], self.test_records[0].data["nombre"])

    def test_statistics(self):
        """Test estadísticas del índice"""
        for record in self.test_records:
            self.rtree.add(record)

        stats = self.rtree.get_statistics()

        self.assertIn('total_records', stats)
        self.assertIn('dimension', stats)
        self.assertEqual(stats['total_records'], len(self.test_records))
        self.assertEqual(stats['dimension'], 2)


def run_performance_test():
    """Test de rendimiento básico"""
    print("\n=== Test de Rendimiento ===")

    # Crear índice
    rtree = RTreeIndex("performance_test", dimension=2)

    # Insertar 1000 registros
    import time
    start_time = time.time()

    for i in range(1000):
        record = create_record(i, [float(i % 100), float(i % 50)], {"data": f"Record {i}"})
        rtree.add(record)

    insert_time = time.time() - start_time
    print(f"Inserción de 1000 registros: {insert_time:.4f} segundos")

    # Test de búsqueda
    start_time = time.time()

    for i in range(100):
        center = Point([float(i % 100), float(i % 50)])
        results = rtree.range_search(center, 5.0)

    search_time = time.time() - start_time
    print(f"100 búsquedas por rango: {search_time:.4f} segundos")

    print(f"Estadísticas finales: {rtree.get_statistics()}")


if __name__ == "__main__":
    print("=== EJECUTANDO TESTS DEL R-TREE ===")
    unittest.main(argv=[''], exit=False, verbosity=2)

    # Test adicional de rendimiento
    run_performance_test()

    print("\n=== TODOS LOS TESTS COMPLETADOS ===")