# Sistema Modular de Búsqueda de Audio por Similitud (MFCC + BoAW)

## Resumen

Sistema de búsqueda de audios similares basado en **MFCC (Mel-Frequency Cepstral Coefficients)** y **Bag of Audio Words (BoAW)** con ponderación **TF-IDF**. Arquitectura **modular** análoga al sistema SIFT para imágenes.

---

## ¿Qué es MFCC?

**Mel-Frequency Cepstral Coefficients** son características que representan el espectro de audio de forma compacta, simulando la percepción auditiva humana.

### Pipeline de Extracción MFCC:

```
Audio → Pre-énfasis → Framing (25ms) → FFT → Mel Filterbank → Log → DCT → MFCCs
```

1. **Pre-énfasis**: Realza frecuencias altas (compensar atenuación de voz)
2. **Framing**: Divide audio en ventanas de 25ms con overlap
3. **FFT**: Transforma cada frame a frecuencia
4. **Mel Filterbank**: Aplica escala Mel (perceptual humana)
5. **Log**: Compresión de rango dinámico
6. **DCT**: Decorrelaciona coeficientes → MFCCs finales

### Resultado:
- Cada **frame** (25ms) → vector de **13 MFCCs** (+ 13 delta + 13 delta-delta = **39 dimensiones**)
- Un audio de 3 segundos → ~150 frames → matriz 150×39

---

## Arquitectura Modular

```
Audio_struct/
├── AudioEngine.py         # Motor principal (integra todos los módulos)
├── feature_extractor.py   # Extracción de MFCC + delta + delta-delta
├── audio_codebook.py      # Vocabulario de audio (K-Means)
├── tfidf_weighting.py     # Ponderación TF-IDF
├── knn_sequential.py      # Búsqueda KNN secuencial
├── knn_inverted.py        # Búsqueda KNN con índice invertido
└── descriptors/           # Archivos persistentes (.npz, .npy)
```

---

## Módulos y su Propósito

### 1. `feature_extractor.py` - Extracción MFCC

**Propósito:** Extraer características MFCC de archivos de audio.

**Funcionamiento:**
1. Carga audio con librosa (mono, 22050 Hz)
2. Extrae MFCCs (13 coeficientes por frame)
3. Calcula **delta** (velocidad) y **delta-delta** (aceleración)
4. Concatena: [MFCC | delta | delta-delta] = 39 dimensiones
5. Normaliza con z-score por frame

**Parámetros clave:**
```python
sample_rate: 22050      # Frecuencia estándar
n_mfcc: 13              # Coeficientes MFCC
n_fft: 2048             # Ventana FFT (~93ms)
hop_length: 512         # Salto entre frames (~23ms)
n_mels: 128             # Filtros Mel
duration: 30.0          # Máximo segundos a procesar
```

**¿Por qué delta y delta-delta?**
- MFCCs capturan espectro estático
- Delta: velocidad de cambio temporal
- Delta-delta: aceleración
- Juntos capturan dinámica del audio (transiciones, ritmo)

---

### 2. `audio_codebook.py` - Vocabulario de Audio

**Propósito:** Crear diccionario de "palabras de audio" mediante K-Means.

**Funcionamiento:**
1. Recolecta frames MFCC de todos los audios
2. Aplica **MiniBatchKMeans** para agrupar en K clusters
3. Cada centroide = una "palabra de audio" (patrón sonoro)
4. Para cada audio, asigna frames a clusters → histograma

**Cálculo dinámico de K:**
```python
# K más pequeño que en imágenes (audio es más homogéneo)
K = min(max(sqrt(total_frames / 20), 32), 512)
# Ejemplo: 10,000 frames → 256 clusters
```

**¿Por qué menos clusters que SIFT?**
- Audio tiene menos variabilidad que imágenes
- Patrones sonoros son más continuos
- 64-256 clusters suelen ser suficientes

---

### 3. `tfidf_weighting.py` - Ponderación TF-IDF

**Propósito:** Ponderar histogramas para discriminar mejor.

**Funcionamiento:**
- **TF**: log(1 + frecuencia) - suaviza diferencias
- **IDF**: log(N / df) + 1 - penaliza palabras comunes
- Normalización L2 para similitud coseno

**¿Por qué TF-IDF para audio?**
- Palabras de audio comunes (silencio, ruido de fondo) → bajo peso
- Patrones distintivos (instrumentos específicos, voces) → alto peso

---

### 4. `knn_sequential.py` - Búsqueda KNN Secuencial

**Propósito:** Encontrar K audios más similares recorriendo todo el índice.

**Funcionamiento:**
1. Calcula similitud coseno con todos los vectores
2. Usa heap de tamaño K para top-K eficiente
3. Retorna lista ordenada (audio, similitud)

**Complejidad:** O(N × D)

---

### 5. `knn_inverted.py` - Búsqueda KNN con Índice Invertido

**Propósito:** Acelerar búsqueda usando índice invertido.

**Algoritmo TAAT:**
1. Para cada palabra de audio en query:
   - Recorre posting list
   - Acumula scores
2. Ordena por score y retorna top-K

**Ventaja:** Solo procesa audios que comparten palabras de audio.

---

### 6. `AudioEngine.py` - Motor Principal

**Propósito:** Integrar todos los módulos y gestionar persistencia.

**Responsabilidades:**
1. Configuración con `AudioConfig`
2. Persistencia con `Heap_struct`
3. Coordina pipeline: MFCC → Codebook → TF-IDF → KNN
4. Reconstrucción automática de vocabulario

---

## Flujo Completo

### Indexación:
```
audio.mp3 → MFCCExtractor → frames (N×39)
            ↓
            AudioCodebook → histograma (K dims)
            ↓
            TFIDFWeighter → vector TF-IDF normalizado
            ↓
            Heap + InvertedIndex → persistencia
```

### Búsqueda:
```
query.mp3 → extractor → frames → histograma → TF-IDF
            ↓
            InvertedIndex.search() o KNNSequential.search()
            ↓
            top-K audios con similitud
```

---

## Configuración

```python
@dataclass
class AudioConfig:
    sample_rate: int = 22050       # Hz
    n_mfcc: int = 13               # Coeficientes MFCC
    include_delta: bool = True     # Incluir derivadas
    duration: float = 30.0         # Máximo segundos
    min_frames: int = 10           # Mínimo para indexar
    min_audios_for_vocab: int = 5  # Mínimo para crear vocabulario
    use_inverted_index: bool = True
    default_k: int = 10
```

---

## Uso desde API

```python
from Audio_struct.AudioEngine import AudioEngine, AudioConfig

# Inicializar
engine = AudioEngine(base_dir=".", data_dir="api/data/audio")

# Indexar audio
result = engine.add_audio(1, "song.mp3", "/path/to/song.mp3")
# {"success": True, "id": 1, "n_frames": 1500, "duration": 30.0}

# Buscar similares
results = engine.search("/path/to/query.mp3", k=5)
# [{"id": 3, "nombre": "similar.mp3", "similarity": 0.85}, ...]

# Estadísticas
stats = engine.get_stats()
# {"num_audios": 50, "vocabulary_size": 256, ...}
```

---

## Endpoints API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/audio/upload` | Subir y indexar audio |
| POST | `/api/audio/search` | Buscar audios similares |
| GET | `/api/audio/list` | Listar todos los audios |
| GET | `/api/audio/file/{id}` | Obtener archivo de audio |
| GET | `/api/audio/stats` | Estadísticas del índice |
| POST | `/api/audio/rebuild` | Reconstruir índice |
| DELETE | `/api/audio/clear` | Limpiar índice |

---

## Comparación SIFT vs MFCC

| Aspecto | SIFT (Imágenes) | MFCC (Audio) |
|---------|-----------------|--------------|
| Descriptor | 128 dims | 39 dims (13×3) |
| Unidad | Keypoint | Frame (25ms) |
| Invariancia | Escala, rotación | Tempo (parcial) |
| Clusters típicos | 500-2000 | 64-512 |
| Datos por item | ~500 keypoints | ~150 frames/seg |

---

## Casos de Uso

1. **Búsqueda de música similar**: Encontrar canciones con características similares
2. **Detección de duplicados**: Identificar audios idénticos o casi idénticos
3. **Clasificación de géneros**: Agrupar audios por características sonoras
4. **Búsqueda por tarareado**: Encontrar canciones tarareando una melodía

---

## Dependencias

```
librosa>=0.9.0
numpy>=1.20.0
scikit-learn>=0.24.0
```

Instalar: `pip install librosa numpy scikit-learn`

---

## Métricas de Rendimiento

Con 30 audios de prueba (música variada):

| Métrica | Valor |
|---------|-------|
| Vocabulario (K) | ~128-256 palabras |
| Frames/audio | ~150-3000 (depende duración) |
| Tiempo indexación | ~1-2s por audio |
| Tiempo búsqueda | <200ms |
| Precisión top-5 | Similar género/artista |
