import csv
import json
from typing import List, Dict, Any

# Datos de restaurantes(coordenadas reales de Lima)

SAMPLE_RESTAURANTS = [
    {
        "id": 1,
        "nombre": "Central Restaurante",
        "tipo_cocina": "peruana_contemporanea",
        "fechaRegistro": "2024-01-15",
        "ubicacion": [-12.1211, -77.0316],  # Barranco
        "rating": 4.8,
        "precio_promedio": 350.0,
        "telefono": "01-2428515"
    },
    {
        "id": 2,
        "nombre": "Maido",
        "tipo_cocina": "nikkei",
        "fechaRegistro": "2024-01-20",
        "ubicacion": [-12.1098, -77.0370],  # Miraflores
        "rating": 4.9,
        "precio_promedio": 320.0,
        "telefono": "01-4466220"
    },
    {
        "id": 3,
        "nombre": "Astrid y Gastón",
        "tipo_cocina": "peruana_fusion",
        "fechaRegistro": "2024-02-05",
        "ubicacion": [-12.0886, -77.0531],  # San Isidro
        "rating": 4.7,
        "precio_promedio": 280.0,
        "telefono": "01-4442777"
    },
    {
        "id": 4,
        "nombre": "La Mar",
        "tipo_cocina": "cevicheria",
        "fechaRegistro": "2024-02-10",
        "ubicacion": [-12.1044, -77.0364],  # Miraflores
        "rating": 4.6,
        "precio_promedio": 85.0,
        "telefono": "01-4213365"
    },
    {
        "id": 5,
        "nombre": "Isolina Taberna Peruana",
        "tipo_cocina": "criolla",
        "fechaRegistro": "2024-02-15",
        "ubicacion": [-12.1201, -77.0301],  # Barranco
        "rating": 4.5,
        "precio_promedio": 65.0,
        "telefono": "01-2477002"
    },
    {
        "id": 6,
        "nombre": "Osaka",
        "tipo_cocina": "nikkei",
        "fechaRegistro": "2024-02-20",
        "ubicacion": [-12.1089, -77.0441],  # Miraflores
        "rating": 4.4,
        "precio_promedio": 120.0,
        "telefono": "01-2428628"
    },
    {
        "id": 7,
        "nombre": "Panchita",
        "tipo_cocina": "parrillas",
        "fechaRegistro": "2024-03-01",
        "ubicacion": [-12.1067, -77.0378],  # Miraflores
        "rating": 4.3,
        "precio_promedio": 95.0,
        "telefono": "01-2424957"
    },
    {
        "id": 8,
        "nombre": "La Lucha Sanguchería",
        "tipo_cocina": "sandwiches",
        "fechaRegistro": "2024-03-05",
        "ubicacion": [-12.1156, -77.0247],  # Barranco
        "rating": 4.2,
        "precio_promedio": 25.0,
        "telefono": "01-2477108"
    },
    {
        "id": 9,
        "nombre": "Chez Wong",
        "tipo_cocina": "chifa",
        "fechaRegistro": "2024-03-10",
        "ubicacion": [-12.0951, -77.0364],  # San Isidro
        "rating": 4.1,
        "precio_promedio": 45.0,
        "telefono": "01-4406314"
    },
    {
        "id": 10,
        "nombre": "El Mercado",
        "tipo_cocina": "mediterranea",
        "fechaRegistro": "2024-03-15",
        "ubicacion": [-12.1078, -77.0369],  # Miraflores
        "rating": 4.0,
        "precio_promedio": 110.0,
        "telefono": "01-2214562"
    },
    {
        "id": 11,
        "nombre": "Siete Sopas",
        "tipo_cocina": "criolla",
        "fechaRegistro": "2024-03-20",
        "ubicacion": [-12.1189, -77.0286],  # Barranco
        "rating": 4.3,
        "precio_promedio": 40.0,
        "telefono": "01-2525300"
    },
    {
        "id": 12,
        "nombre": "Tanta",
        "tipo_cocina": "peruana_moderna",
        "fechaRegistro": "2024-03-25",
        "ubicacion": [-12.1098, -77.0334],  # Miraflores
        "rating": 4.2,
        "precio_promedio": 75.0,
        "telefono": "01-4217708"
    }
]

# Datos de puntos de interés adicionales
SAMPLE_POI = [
    {
        "id": 101,
        "nombre": "Parque Kennedy",
        "tipo": "parque",
        "ubicacion": [-12.1062, -77.0362],
        "area_m2": 12000
    },
    {
        "id": 102,
        "nombre": "Malecón de Miraflores",
        "tipo": "mirador",
        "ubicacion": [-12.1156, -77.0247],
        "longitud_m": 2500
    },
    {
        "id": 103,
        "nombre": "Centro Comercial Larcomar",
        "tipo": "centro_comercial",
        "ubicacion": [-12.1314, -77.0217],
        "tiendas": 120
    },
    {
        "id": 104,
        "nombre": "Puente de los Suspiros",
        "tipo": "monumento",
        "ubicacion": [-12.1204, -77.0283],
        "año_construccion": 1876
    }
]


def create_sample_csv(filename: str = "restaurantes_lima.csv"):
    """Crea un archivo CSV con los datos de ejemplo"""

    fieldnames = [
        'id', 'nombre', 'tipo_cocina', 'fechaRegistro',
        'ubicacion', 'rating', 'precio_promedio', 'telefono'
    ]

    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for restaurant in SAMPLE_RESTAURANTS:
            # Convertir ubicación a string para CSV
            row = restaurant.copy()
            row['ubicacion'] = f"[{restaurant['ubicacion'][0]}, {restaurant['ubicacion'][1]}]"
            writer.writerow(row)

    print(f"Archivo CSV creado: {filename}")
    return filename


def create_sample_json(filename: str = "restaurantes_lima.json"):
    """Crea un archivo JSON con los datos de ejemplo"""

    data = {
        "restaurantes": SAMPLE_RESTAURANTS,
        "puntos_interes": SAMPLE_POI,
        "metadata": {
            "ciudad": "Lima",
            "pais": "Peru",
            "total_restaurantes": len(SAMPLE_RESTAURANTS),
            "total_poi": len(SAMPLE_POI),
            "coordenadas_centro": [-12.1067, -77.0378],  # Centro aproximado Miraflores
            "radio_cobertura_km": 5.0
        }
    }

    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    print(f"Archivo JSON creado: {filename}")
    return filename


def get_sample_queries():
    """Retorna consultas de ejemplo para testing"""

    queries = [
        {
            "descripcion": "Crear tabla de restaurantes con índice espacial",
            "sql": """
                CREATE TABLE Restaurantes (
                    id INT KEY INDEX SEQ,
                    nombre VARCHAR[50] INDEX BTree,
                    tipo_cocina VARCHAR[30],
                    fechaRegistro DATE,
                    ubicacion ARRAY[FLOAT] INDEX RTree,
                    rating FLOAT,
                    precio_promedio FLOAT,
                    telefono VARCHAR[20]
                )
            """
        },
        {
            "descripcion": "Insertar restaurante Central",
            "sql": "INSERT INTO Restaurantes VALUES (1, 'Central Restaurante', 'peruana_contemporanea', '2024-01-15', [-12.1211, -77.0316], 4.8, 350.0, '01-2428515')"
        },
        {
            "descripcion": "Buscar restaurantes cerca del Parque Kennedy (radio 500m)",
            "sql": "SELECT * FROM Restaurantes WHERE ubicacion IN ([-12.1062, -77.0362], 0.005)",
            "comentario": "Radio 0.005 grados ≈ 500 metros"
        },
        {
            "descripcion": "Buscar 3 restaurantes más cercanos a Larcomar",
            "sql": "SELECT KNN(3) FROM Restaurantes WHERE ubicacion NEAR [-12.1314, -77.0217]",
            "comentario": "Consulta K-NN (requiere extensión del parser)"
        },
        {
            "descripcion": "Buscar restaurantes por rango de precio",
            "sql": "SELECT * FROM Restaurantes WHERE precio_promedio BETWEEN 50 AND 150"
        },
        {
            "descripcion": "Buscar restaurantes nikkei",
            "sql": "SELECT * FROM Restaurantes WHERE tipo_cocina = 'nikkei'"
        },
        {
            "descripcion": "Eliminar restaurante por ID",
            "sql": "DELETE FROM Restaurantes WHERE id = 8"
        }
    ]

    return queries


def get_test_scenarios():
    """Retorna escenarios de prueba para validar el R-Tree"""

    scenarios = [
        {
            "nombre": "Test básico de inserción y búsqueda",
            "descripcion": "Insertar 5 restaurantes y buscar por ID",
            "pasos": [
                "Crear tabla",
                "Insertar 5 registros",
                "Buscar por ID = 3",
                "Verificar resultado correcto"
            ]
        },
        {
            "nombre": "Test de búsqueda espacial por radio",
            "descripcion": "Buscar restaurantes en radio de 1km desde el centro",
            "centro": [-12.1067, -77.0378],
            "radio": 0.01,  # ~1km
            "resultados_esperados": ["Maido", "La Mar", "Panchita", "El Mercado", "Tanta"]
        },
        {
            "nombre": "Test K-NN en diferentes ubicaciones",
            "descripcion": "Verificar K vecinos más cercanos desde varios puntos",
            "puntos_consulta": [
                {
                    "punto": [-12.1211, -77.0316],  # Central Restaurante
                    "k": 3,
                    "esperados": ["Isolina", "Siete Sopas", "La Lucha"]
                },
                {
                    "punto": [-12.1044, -77.0364],  # La Mar
                    "k": 2,
                    "esperados": ["Maido", "Panchita"]
                }
            ]
        },
        {
            "nombre": "Test de eliminación y consistencia",
            "descripcion": "Eliminar registros y verificar que no aparecen en búsquedas",
            "pasos": [
                "Insertar 10 restaurantes",
                "Eliminar 3 restaurantes específicos",
                "Verificar que búsquedas no los incluyen",
                "Verificar integridad del índice"
            ]
        },
        {
            "nombre": "Test de persistencia",
            "descripcion": "Verificar guardado y carga de datos",
            "pasos": [
                "Crear índice con datos",
                "Guardar en archivo",
                "Crear nuevo índice vacío",
                "Cargar desde archivo",
                "Verificar datos idénticos"
            ]
        },
        {
            "nombre": "Test de rendimiento",
            "descripcion": "Medir rendimiento con dataset grande",
            "tamaño_dataset": 10000,
            "operaciones": [
                "Inserción masiva",
                "Búsqueda por radio",
                "K-NN con k=100",
                "Eliminación múltiple"
            ],
            "metricas": ["tiempo_insercion", "tiempo_busqueda", "memoria_utilizada"]
        }
    ]

    return scenarios


def generate_performance_data(n_records: int = 1000) -> List[Dict[str, Any]]:
    """Genera datos sintéticos para pruebas de rendimiento"""

    import random

    # Coordenadas de Lima (bounding box)
    lima_bbox = {
        'min_lat': -12.25,
        'max_lat': -11.95,
        'min_lon': -77.15,
        'max_lon': -76.95
    }

    cocinas = ['peruana', 'italiana', 'china', 'japonesa', 'mexicana', 'francesa',
               'española', 'argentina', 'brasileña', 'tailandesa']

    performance_data = []

    for i in range(n_records):
        lat = random.uniform(lima_bbox['min_lat'], lima_bbox['max_lat'])
        lon = random.uniform(lima_bbox['min_lon'], lima_bbox['max_lon'])

        record = {
            'id': i + 1000,  # Evitar conflictos con datos de ejemplo
            'nombre': f'Restaurante_{i + 1}',
            'tipo_cocina': random.choice(cocinas),
            'fechaRegistro': f'2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}',
            'ubicacion': [lat, lon],
            'rating': round(random.uniform(3.0, 5.0), 1),
            'precio_promedio': round(random.uniform(20, 400), 2),
            'telefono': f'01-{random.randint(2000000, 9999999)}'
        }

        performance_data.append(record)

    return performance_data


if __name__ == "__main__":
    print("=== GENERADOR DE DATOS DE PRUEBA PARA R-TREE ===")

    # Crear archivos de datos
    csv_file = create_sample_csv()
    json_file = create_sample_json()

    # Mostrar consultas de ejemplo
    print("\n=== CONSULTAS DE EJEMPLO ===")
    queries = get_sample_queries()
    for i, query in enumerate(queries, 1):
        print(f"\n{i}. {query['descripcion']}")
        print(f"   SQL: {query['sql'].strip()}")
        if 'comentario' in query:
            print(f"   Nota: {query['comentario']}")

    # Mostrar escenarios de testing
    print("\n=== ESCENARIOS DE PRUEBA ===")
    scenarios = get_test_scenarios()
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['nombre']}")
        print(f"   {scenario['descripcion']}")

    # Generar datos de rendimiento
    print("\n=== GENERANDO DATOS DE RENDIMIENTO ===")
    perf_data = generate_performance_data(100)  # 100 registros para demo

    perf_file = "performance_data.json"
    with open(perf_file, 'w', encoding='utf-8') as f:
        json.dump(perf_data, f, indent=2, ensure_ascii=False)

    print(f"Datos de rendimiento generados: {perf_file}")
    print(f"Total archivos creados: {csv_file}, {json_file}, {perf_file}")

    print("\n=== RESUMEN DE DATOS GENERADOS ===")
    print(f"- Restaurantes reales: {len(SAMPLE_RESTAURANTS)}")
    print(f"- Puntos de interés: {len(SAMPLE_POI)}")
    print(f"- Datos de rendimiento: {len(perf_data)}")
    print(f"- Consultas de ejemplo: {len(queries)}")
    print(f"- Escenarios de prueba: {len(scenarios)}")