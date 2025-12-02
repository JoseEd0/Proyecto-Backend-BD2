# Sistema Modular de Búsqueda de Imágenes por Contenido Visual (SIFT + BoVW)

## Resumen

Sistema de búsqueda de imágenes similares basado en **SIFT (Scale-Invariant Feature Transform)** y **Bag of Visual Words (BoVW)** con ponderación **TF-IDF**. La arquitectura es **modular**, separando cada responsabilidad en archivos independientes.

---

## Arquitectura Modular

```
SIFT_struct/
├── SIFTEngine.py          # Motor principal (integra todos los módulos)
├── feature_extractor.py   # Extracción de descriptores SIFT
├── visual_codebook.py     # Vocabulario visual (K-Means)
├── tfidf_weighting.py     # Ponderación TF-IDF
├── knn_sequential.py      # Búsqueda KNN secuencial
├── knn_inverted.py        # Búsqueda KNN con índice invertido
└── descriptors/           # Archivos persistentes (.npz)
```

---

## Módulos y su Propósito

### 1. `feature_extractor.py` - Extracción de Características

**Propósito:** Extraer descriptores SIFT de imágenes con transformación RootSIFT.

**Funcionamiento:**
1. Redimensiona imagen manteniendo aspect ratio (max 512px)
2. Convierte a escala de grises
3. Detecta keypoints con SIFT
4. Calcula descriptores de 128 dimensiones por keypoint
5. Aplica **RootSIFT**: normalización L1 + raíz cuadrada → mejora discriminación

**Parámetros clave:**
- `contrast_threshold=0.02`: Bajo para detectar keypoints en imágenes con fondos simples
- `edge_threshold=15`: Evita filtrar demasiados bordes
- `min_descriptors=5`: Mínimo para indexar una imagen

```python
extractor = SIFTFeatureExtractor(target_size=512, use_root_sift=True)
keypoints, descriptors = extractor.extract(image_path)
```

---

### 2. `visual_codebook.py` - Vocabulario Visual

**Propósito:** Crear diccionario de "palabras visuales" mediante clustering K-Means.

**Funcionamiento:**
1. Recolecta descriptores de todas las imágenes indexadas
2. Aplica **MiniBatchKMeans** para agrupar en K clusters
3. Cada centroide = una "palabra visual"
4. Para cada imagen, asigna cada descriptor al cluster más cercano
5. Genera histograma de frecuencias (Bag of Visual Words)

**Cálculo dinámico de K:**
```python
# K escala con sqrt del número de descriptores
K = min(max(sqrt(total_descriptors/10), 100), 2000)
# Ejemplo: 16,000 descriptores → 500 clusters
```

**Por qué K-Means:**
- Agrupa patrones visuales similares (bordes, esquinas, texturas)
- Reduce dimensionalidad: 128D × N descriptores → K palabras visuales

---

### 3. `tfidf_weighting.py` - Ponderación TF-IDF

**Propósito:** Ponderar histogramas para que palabras raras sean más discriminativas.

**Funcionamiento:**

**TF (Term Frequency):**
```
TF = log(1 + frecuencia_palabra)
```
Logaritmo suaviza diferencias entre imágenes con muchos/pocos descriptores.

**IDF (Inverse Document Frequency):**
```
IDF = log(N / df) + 1
donde:
  N = total de imágenes
  df = imágenes que contienen esa palabra visual
```
Palabras que aparecen en pocas imágenes tienen mayor peso.

**Vector final:**
```
TF-IDF = TF × IDF
Normalizado con L2 para comparación coseno
```

**Por qué TF-IDF:**
- Palabras comunes (cielo, fondo) → bajo peso
- Palabras raras (patrones únicos) → alto peso
- Mejora dramáticamente la discriminación entre categorías

---

### 4. `knn_sequential.py` - Búsqueda KNN Secuencial

**Propósito:** Encontrar K imágenes más similares recorriendo todo el índice.

**Funcionamiento:**
1. Calcula similitud coseno entre query y cada imagen indexada
2. Usa **heap de tamaño K** (min-heap) para mantener top-K eficientemente
3. Retorna lista ordenada de (imagen, similitud)

**Similitud coseno:**
```
sim(A, B) = (A · B) / (||A|| × ||B||)
```
Con vectores L2-normalizados: `sim = A · B` (producto punto)

**Complejidad:** O(N × D) donde N=imágenes, D=dimensión del vector

---

### 5. `knn_inverted.py` - Búsqueda KNN con Índice Invertido

**Propósito:** Acelerar búsqueda usando índice invertido (TAAT).

**Estructura del índice:**
```python
inverted_index = {
    palabra_visual_0: [(img_id_1, peso), (img_id_5, peso), ...],
    palabra_visual_1: [(img_id_2, peso), (img_id_3, peso), ...],
    ...
}
```

**Algoritmo TAAT (Term-At-A-Time):**
1. Para cada palabra visual presente en la query:
   - Recorre su posting list
   - Acumula score: `scores[img_id] += query_weight × doc_weight`
2. Ordena por score y retorna top-K

**Ventaja:** Solo procesa imágenes que comparten palabras visuales con la query.

**Complejidad:** O(|Q| × L) donde |Q|=palabras en query, L=longitud promedio de posting lists

---

### 6. `SIFTEngine.py` - Motor Principal

**Propósito:** Integrar todos los módulos y gestionar persistencia con Heap.

**Responsabilidades:**
1. **Configuración:** `SIFTConfig` con parámetros ajustables
2. **Persistencia:** Usa `Heap_struct` del proyecto para almacenar metadatos
3. **Indexación:** Coordina extracción → vocabulario → TF-IDF → índice invertido
4. **Búsqueda:** Enruta a KNN secuencial o invertido según configuración
5. **Reconstrucción:** Detecta cuándo reconstruir vocabulario (ratio de imágenes)

**Flujo de indexación:**
```
imagen → SIFTFeatureExtractor → descriptores
         ↓
         VisualCodebook → histograma BoW
         ↓
         TFIDFWeighting → vector TF-IDF normalizado
         ↓
         Heap + InvertedIndexSearch → persistencia
```

**Flujo de búsqueda:**
```
query_imagen → extractor → histograma → TF-IDF
              ↓
              InvertedIndexSearch.search() o SequentialKNN.search()
              ↓
              top-K resultados con similitud
```

---

## Persistencia

El sistema guarda su estado en archivos `.npz`:

| Archivo | Contenido |
|---------|-----------|
| `codebook.npz` | Centroides K-Means (vocabulario visual) |
| `index.npz` | IDF, índice invertido, vectores TF-IDF |
| `images.heap` | Metadatos de imágenes (Heap_struct) |
| `images_index.heap` | Índice del Heap |

---

## Configuración

```python
@dataclass
class SIFTConfig:
    image_size: int = 512          # Tamaño máximo de imagen
    use_root_sift: bool = True     # Usar RootSIFT
    min_descriptors: int = 5       # Mínimo para indexar (bajo para fondos simples)
    min_images_for_vocab: int = 10 # Mínimo para crear vocabulario
    use_inverted_index: bool = True
    default_k: int = 10
```

---

## Uso desde API

```python
from SIFT_struct.SIFTEngine import SIFTEngine, SIFTConfig

# Inicializar
engine = SIFTEngine(data_dir="api/data/sift")

# Indexar imagen
result = engine.index_image("/path/to/image.jpg")
# {"id": 1, "filename": "image.jpg", "n_descriptors": 342}

# Buscar similares
results = engine.search(query_image_path, k=5)
# [{"id": 3, "filename": "similar.jpg", "similarity": 0.85}, ...]

# Información del índice
info = engine.get_index_info()
# {"n_images": 30, "vocab_size": 500, "has_inverted_index": True}
```

---

## Justificación de Diseño

### ¿Por qué SIFT?
- Invariante a escala, rotación e iluminación
- Robusto para matching de objetos
- Estado del arte para características locales

### ¿Por qué Bag of Visual Words?
- Permite comparar imágenes con diferente número de descriptores
- Vector de tamaño fijo (K dimensiones)
- Análogo a representación de documentos de texto

### ¿Por qué TF-IDF?
- Reduce impacto de patrones comunes (fondos, bordes simples)
- Amplifica patrones discriminativos únicos
- Probado efectivo en recuperación de información

### ¿Por qué RootSIFT?
- Mejora discriminación en comparación de distancias
- Hellinger kernel → más robusto que Euclidean

### ¿Por qué Índice Invertido?
- Escalabilidad: evita comparar con todas las imágenes
- Solo procesa imágenes que comparten palabras visuales
- Eficiente para vocabularios grandes

---

## Métricas de Rendimiento

Con 30 imágenes de prueba (carros, gatos, herramientas):

| Métrica | Valor |
|---------|-------|
| Vocabulario (K) | ~500 palabras visuales |
| Promedio descriptores/imagen | ~500-600 |
| Tiempo indexación | ~0.5s por imagen |
| Tiempo búsqueda (invertido) | <100ms |
| Precisión top-5 | Imágenes misma categoría |

---

## Dependencias

```
opencv-python>=4.5.0
numpy>=1.20.0
scikit-learn>=0.24.0
```
