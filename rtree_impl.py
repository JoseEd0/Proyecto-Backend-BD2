from rtree import index
import json
import os
import math
import uuid
from typing import List, Tuple, Dict, Any, Optional, Union


class Point:
    """Clase para representar un punto multidimensional"""

    def __init__(self, coordinates: List[float], id: Optional[str] = None):
        self.coordinates = coordinates
        self.id = id or str(uuid.uuid4())
        self.dimension = len(coordinates)

    def __str__(self):
        return f"Point(id={self.id}, coords={self.coordinates})"

    def __repr__(self):
        return self.__str__()

    def distance_to(self, other_point: 'Point') -> float:
        """Calcula la distancia euclidiana a otro punto"""
        if self.dimension != other_point.dimension:
            raise ValueError("Los puntos deben tener la misma dimensión")

        sum_squares = sum((a - b) ** 2 for a, b in zip(self.coordinates, other_point.coordinates))
        return math.sqrt(sum_squares)


class SpatialRecord:
    """Clase para representar un registro con información espacial"""

    def __init__(self, id: Union[int, str], location: Point, data: Dict[str, Any]):
        self.id = str(id)
        self.location = location
        self.data = data
        self.created_at = None
        self.updated_at = None

    def __str__(self):
        return f"SpatialRecord(id={self.id}, location={self.location}, data={self.data})"

    def __repr__(self):
        return self.__str__()

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el registro a diccionario para serialización"""
        return {
            'id': self.id,
            'location': {
                'coordinates': self.location.coordinates,
                'id': self.location.id
            },
            'data': self.data,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpatialRecord':
        """Crea un registro desde un diccionario"""
        location = Point(data['location']['coordinates'], data['location']['id'])
        record = cls(data['id'], location, data['data'])
        record.created_at = data.get('created_at')
        record.updated_at = data.get('updated_at')
        return record


class RTreeIndex:
    """Implementación de R-Tree para indexación espacial multidimensional"""

    def __init__(self, file_path: Optional[str] = None, dimension: int = 2):
        self.dimension = dimension
        self.file_path = file_path or "rtree_index"
        self.data_file = f"{self.file_path}_data.json"

        properties = index.Property()
        properties.dimension = dimension
        properties.storage = index.RT_Memory

        try:
            if os.path.exists(f"{self.file_path}.idx"):
                self.idx = index.Index(self.file_path, properties=properties)
            else:
                self.idx = index.Index(properties=properties)
        except:
            self.idx = index.Index(properties=properties)

        self.records: Dict[str, SpatialRecord] = {}
        self._next_id = 0
        self.load_data(silent=True)  # Silent para evitar errores en tests con temp dirs

    def _generate_bbox(self, point: Point) -> Tuple[float, ...]:
        """Genera bounding box para un punto"""
        coords = point.coordinates
        return tuple(coords + coords)

    def _point_to_bbox(self, coordinates: List[float]) -> Tuple[float, ...]:
        return tuple(coordinates + coordinates)

    def add(self, record: SpatialRecord) -> bool:
        try:
            if record.location.dimension != self.dimension:
                raise ValueError(f"El punto debe tener dimensión {self.dimension}")

            if not record.id:
                record.id = str(self._next_id)
                self._next_id += 1

            bbox = self._generate_bbox(record.location)
            self.idx.insert(int(record.id) if record.id.isdigit() else hash(record.id), bbox)
            self.records[record.id] = record

            if record.id.isdigit():
                self._next_id = max(self._next_id, int(record.id) + 1)

            return True

        except Exception as e:
            print(f"Error al insertar registro: {e}")
            return False

    def remove(self, record_id: str) -> bool:
        try:
            if record_id not in self.records:
                return False

            record = self.records[record_id]
            bbox = self._generate_bbox(record.location)
            numeric_id = int(record_id) if record_id.isdigit() else hash(record_id)
            self.idx.delete(numeric_id, bbox)
            del self.records[record_id]

            return True

        except Exception as e:
            print(f"Error al eliminar registro: {e}")
            return False

    def search(self, record_id: str) -> Optional[SpatialRecord]:
        return self.records.get(record_id)

    def range_search(self, center_point: Point, radius: float) -> List[SpatialRecord]:
        """Búsqueda por rango dentro de un radio"""
        try:
            if center_point.dimension != self.dimension:
                raise ValueError(f"El punto debe tener dimensión {self.dimension}")

            coords = center_point.coordinates
            bbox_coords = []

            for coord in coords:
                bbox_coords.append(coord - radius)

            for coord in coords:
                bbox_coords.append(coord + radius)

            bbox = tuple(bbox_coords)
            candidate_ids = list(self.idx.intersection(bbox))

            results = []
            for candidate_id in candidate_ids:
                record = None
                for rec_id, rec in self.records.items():
                    numeric_id = int(rec_id) if rec_id.isdigit() else hash(rec_id)
                    if numeric_id == candidate_id:
                        record = rec
                        break

                if record:
                    distance = center_point.distance_to(record.location)
                    if distance <= radius:
                        results.append(record)

            return results

        except Exception as e:
            print(f"Error en búsqueda por rango: {e}")
            return []

    def k_nearest_neighbors(self, query_point: Point, k: int) -> List[Tuple[SpatialRecord, float]]:
        """Encuentra los K vecinos más cercanos"""
        try:
            if query_point.dimension != self.dimension:
                raise ValueError(f"El punto debe tener dimensión {self.dimension}")

            distances = []

            for record in self.records.values():
                distance = query_point.distance_to(record.location)
                distances.append((record, distance))

            distances.sort(key=lambda x: x[1])
            return distances[:k]

        except Exception as e:
            print(f"Error en búsqueda KNN: {e}")
            return []

    def get_all_records(self) -> List[SpatialRecord]:
        return list(self.records.values())

    def size(self) -> int:
        return len(self.records)

    def clear(self):
        properties = index.Property()
        properties.dimension = self.dimension
        self.idx = index.Index(properties=properties)
        self.records.clear()
        self._next_id = 0

    def save_data(self, silent=False):
        try:
            data_to_save = {
                'records': {rid: rec.to_dict() for rid, rec in self.records.items()},
                'next_id': self._next_id,
                'dimension': self.dimension
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2, ensure_ascii=False)

        except Exception as e:
            if not silent:
                print(f"Error al guardar datos: {e}")

    def load_data(self, silent=False):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.records = {}
                for rid, rec_data in data.get('records', {}).items():
                    record = SpatialRecord.from_dict(rec_data)
                    self.records[rid] = record

                self._next_id = data.get('next_id', 0)
                self.dimension = data.get('dimension', self.dimension)
                self._rebuild_index()

        except Exception as e:
            if not silent:
                print(f"Error al cargar datos: {e}")

    def _rebuild_index(self):
        try:
            properties = index.Property()
            properties.dimension = self.dimension
            self.idx = index.Index(properties=properties)

            for record in self.records.values():
                bbox = self._generate_bbox(record.location)
                numeric_id = int(record.id) if record.id.isdigit() else hash(record.id)
                self.idx.insert(numeric_id, bbox)

        except Exception as e:
            print(f"Error al reconstruir índice: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'total_records': len(self.records),
            'dimension': self.dimension,
            'file_path': self.file_path,
            'next_id': self._next_id
        }

    def __del__(self):
        try:
            self.save_data(silent=True)  # Silent para evitar errores en tests
        except:
            pass


def create_point_from_coordinates(coordinates: List[float]) -> Point:
    return Point(coordinates)


def create_record(id: Union[int, str], coordinates: List[float], data: Dict[str, Any]) -> SpatialRecord:
    point = Point(coordinates)
    return SpatialRecord(id, point, data)


if __name__ == "__main__":
    rtree = RTreeIndex("test_rtree", dimension=2)

    records = [
        create_record("1", [10.0, 20.0], {"nombre": "Restaurante A", "tipo": "italiano"}),
        create_record("2", [15.0, 25.0], {"nombre": "Restaurante B", "tipo": "mexicano"}),
        create_record("3", [50.0, 80.0], {"nombre": "Restaurante C", "tipo": "chino"}),
        create_record("4", [12.0, 22.0], {"nombre": "Restaurante D", "tipo": "peruano"})
    ]

    for record in records:
        rtree.add(record)

    print("=== Estadísticas del índice ===")
    print(rtree.get_statistics())

    print("\n=== Búsqueda por rango ===")
    center = Point([12.0, 22.0])
    results = rtree.range_search(center, 10.0)
    for result in results:
        print(f"Encontrado: {result}")

    print("\n=== K-vecinos más cercanos ===")
    knn_results = rtree.k_nearest_neighbors(center, 3)
    for record, distance in knn_results:
        print(f"Distancia {distance:.2f}: {record}")

    rtree.save_data()