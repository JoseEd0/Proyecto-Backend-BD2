"""
AudioEngine - Motor Principal de Recuperación de Audio por Similitud

Integra los módulos del pipeline CBIR para audio:
1. feature_extractor: Extracción MFCC
2. audio_codebook: Diccionario de audio (K-Means)
3. tfidf_weighting: Ponderación TF-IDF
4. knn_sequential: Búsqueda KNN con heap
5. knn_inverted: Búsqueda KNN con índice invertido

Usa la estructura Heap del proyecto para almacenamiento persistente.
"""

import os
import sys
import json
import shutil
import threading
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

# Agregar path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importar módulos Audio
from Audio_struct.feature_extractor import MFCCExtractor
from Audio_struct.audio_codebook import AudioCodebook
from Audio_struct.tfidf_weighting import AudioTFIDFWeighter
from Audio_struct.knn_sequential import KNNSequentialSearch
from Audio_struct.knn_inverted import InvertedIndex

# Importar estructura Heap del proyecto
from Heap_struct.Heap import Heap


@dataclass
class AudioConfig:
    """Configuración del motor de Audio."""

    # Procesamiento de audio
    sample_rate: int = 22050
    n_mfcc: int = 13
    include_delta: bool = True  # Incluir delta y delta-delta
    duration: Optional[float] = 30.0  # Máximo 30 segundos (None = completo)
    min_frames: int = 10  # Mínimo de frames para indexar

    # Vocabulario
    min_audios_for_vocab: int = 5  # Mínimo para crear vocabulario
    vocab_rebuild_ratio: float = 2.0

    # Búsqueda
    use_inverted_index: bool = True
    default_k: int = 10


class AudioEngine:
    """
    Motor de Recuperación de Audio basado en MFCC + BoAW + TF-IDF.

    Pipeline:
    1. Audio → MFCC frames
    2. Frames → Audio words (cuantificación)
    3. Audio words → Histogram (BoAW)
    4. Histogram → TF-IDF vector
    5. TF-IDF → KNN search

    Ejemplo:
        engine = AudioEngine(base_dir=".", data_dir="api/data/audio")
        engine.add_audio(1, "song.mp3", "/path/to/song.mp3")
        results = engine.search("/path/to/query.mp3", k=5)
    """

    def __init__(
        self,
        base_dir: str,
        data_dir: str = "api/data/audio",
        config: Optional[AudioConfig] = None,
        force_create: bool = False,
    ):
        """
        Inicializa el motor de Audio.

        Args:
            base_dir: Directorio base del proyecto
            data_dir: Subdirectorio para datos de audio
            config: Configuración (opcional)
            force_create: Si True, reinicia todos los datos
        """
        self.base_dir = os.path.abspath(base_dir)
        self.config = config or AudioConfig()

        # Configurar directorios
        self.data_dir = os.path.join(self.base_dir, data_dir)
        self.desc_dir = os.path.join(self.base_dir, "Audio_struct", "descriptors")
        self.audio_dir = os.path.join(self.data_dir, "uploaded_audios")

        for d in [self.data_dir, self.desc_dir, self.audio_dir]:
            os.makedirs(d, exist_ok=True)

        # Configurar rutas de archivos
        self._setup_paths()

        # Lock para thread safety
        self._lock = threading.Lock()

        # Estado
        self._vocab_audios_count = 0

        # Inicializar componentes
        self.extractor = MFCCExtractor(
            sample_rate=self.config.sample_rate,
            n_mfcc=self.config.n_mfcc,
            include_delta=self.config.include_delta,
            duration=self.config.duration,
        )
        self.codebook = AudioCodebook()
        self.tfidf = AudioTFIDFWeighter()

        # Índices de búsqueda
        self.knn_sequential: Optional[KNNSequentialSearch] = None
        self.inverted_index: Optional[InvertedIndex] = None

        if force_create:
            self._clear_all()

        self._initialize()

    def _setup_paths(self):
        """Configura rutas de archivos."""
        self.heap_path = os.path.join(self.data_dir, "audios.heap")
        self.descriptors_path = os.path.join(self.desc_dir, "all_descriptors.npz")
        self.codebook_path = os.path.join(self.desc_dir, "codebook.pkl")
        self.idf_path = os.path.join(self.desc_dir, "idf_vector.npy")
        self.vectors_path = os.path.join(self.desc_dir, "tfidf_vectors.npy")
        self.index_map_path = os.path.join(self.desc_dir, "index_map.json")
        self.state_path = os.path.join(self.desc_dir, "state.json")

    def _initialize(self):
        """Inicializa Heap y carga estado."""
        # Heap para metadatos de audios
        table_format = {"id": "i", "nombre": "100s", "ruta": "200s", "duracion": "f"}
        self.audios_heap = Heap(table_format, "id", self.heap_path, force_create=False)

        # Cargar estado persistido
        self._load_state()

        # Cargar componentes
        self._load_components()

    def _load_state(self):
        """Carga estado desde disco."""
        if os.path.exists(self.state_path):
            with open(self.state_path, "r") as f:
                state = json.load(f)
                self._vocab_audios_count = state.get("vocab_audios_count", 0)

    def _save_state(self):
        """Guarda estado en disco."""
        state = {
            "vocab_audios_count": self._vocab_audios_count,
            "vocabulary_size": self.codebook.vocabulary_size,
        }
        with open(self.state_path, "w") as f:
            json.dump(state, f)

    def _load_components(self):
        """Carga componentes desde disco."""
        # Cargar codebook
        if os.path.exists(self.codebook_path):
            self.codebook.load(self.codebook_path)

        # Cargar IDF
        if os.path.exists(self.idf_path):
            self.tfidf.load_idf(self.idf_path)

        # Cargar índices de búsqueda
        self._load_search_indices()

    def _load_search_indices(self):
        """Carga índices de búsqueda."""
        if not os.path.exists(self.vectors_path):
            return
        if not os.path.exists(self.index_map_path):
            return

        try:
            vectors = np.load(self.vectors_path)
            with open(self.index_map_path, "r") as f:
                index_map = json.load(f)

            # Reconstruir diccionario de vectores
            tfidf_dict = {}
            for idx, name in enumerate(index_map):
                if idx < len(vectors):
                    tfidf_dict[name] = vectors[idx]

            # Construir índices
            self.knn_sequential = KNNSequentialSearch()
            self.knn_sequential.build_index(tfidf_dict, index_map)

            self.inverted_index = InvertedIndex()
            self.inverted_index.build_index(tfidf_dict, index_map)

            print(f"[AudioEngine] Índices cargados: {len(index_map)} audios")

        except Exception as e:
            print(f"[AudioEngine] Error cargando índices: {e}")

    def _record_to_dict(self, record: list) -> Dict[str, Any]:
        """Convierte registro del Heap a diccionario."""

        def decode(val):
            if isinstance(val, bytes):
                return val.decode("utf-8").rstrip("\x00")
            return val

        return {
            "id": record[0],
            "nombre": decode(record[1]),
            "ruta": decode(record[2]),
            "duracion": record[3] if len(record) > 3 else 0,
        }

    def _clear_all(self):
        """Limpia todos los datos."""
        files = [
            self.heap_path,
            self.descriptors_path,
            self.codebook_path,
            self.idf_path,
            self.vectors_path,
            self.index_map_path,
            self.state_path,
        ]
        for f in files:
            if os.path.exists(f):
                os.remove(f)

        if os.path.exists(self.audio_dir):
            shutil.rmtree(self.audio_dir)
            os.makedirs(self.audio_dir)

    # API
    def add_audio(
        self, audio_id: int, audio_name: str, audio_path: str
    ) -> Dict[str, Any]:
        """
        Agrega un audio al índice.

        Args:
            audio_id: ID único
            audio_name: Nombre descriptivo
            audio_path: Ruta al archivo

        Returns:
            Dict con resultado de la operación
        """
        with self._lock:
            return self._add_audio_internal(audio_id, audio_name, audio_path)

    def _add_audio_internal(
        self, audio_id: int, audio_name: str, audio_path: str
    ) -> Dict[str, Any]:
        """Implementación interna de add_audio."""
        if not os.path.exists(audio_path):
            return {"success": False, "error": f"Archivo no encontrado: {audio_path}"}

        # Extraer características MFCC
        descriptors, metadata = self.extractor.extract(audio_path)

        if descriptors is None:
            return {
                "success": False,
                "error": metadata.get("error", "Error extrayendo MFCC"),
            }

        n_frames = descriptors.shape[0]
        if n_frames < self.config.min_frames:
            return {
                "success": False,
                "error": f"Muy pocos frames ({n_frames}), mínimo: {self.config.min_frames}",
            }

        # Copiar audio a directorio de uploads
        ext = os.path.splitext(audio_path)[1]
        dest_path = os.path.join(self.audio_dir, f"{audio_id}{ext}")
        if audio_path != dest_path:
            shutil.copy2(audio_path, dest_path)

        # Guardar en Heap
        duration = metadata.get("duration", 0)
        record = [audio_id, audio_name, dest_path, duration]
        pos = self.audios_heap.insert(record)

        # Guardar descriptores
        base_name = f"audio_{audio_id}"
        self._save_descriptors(base_name, descriptors)

        # Verificar si necesitamos construir/reconstruir vocabulario
        current_count = self._count_audios()

        if self._should_rebuild_vocab(current_count):
            print(f"[AudioEngine] Reconstruyendo vocabulario ({current_count} audios)")
            self._build_vocabulary()
            self._rebuild_all_vectors()
        elif os.path.exists(self.codebook_path):
            # Solo actualizar este audio
            self._update_single_audio(base_name, descriptors, pos)

        return {
            "success": True,
            "id": audio_id,
            "nombre": audio_name,
            "n_frames": n_frames,
            "duration": duration,
            "has_vocabulary": os.path.exists(self.codebook_path),
            "audios_count": current_count,
        }

    def search(
        self, query_path: str, k: int = 10, use_inverted: Optional[bool] = None
    ) -> List[Tuple[int, float, Dict]]:
        """
        Busca los k audios más similares.

        Args:
            query_path: Ruta al audio de búsqueda
            k: Número de resultados
            use_inverted: Usar índice invertido (None = config default)

        Returns:
            Lista de (posición, similitud, info)
        """
        if not os.path.exists(self.codebook_path):
            return {
                "success": False,
                "error": f"Vocabulario no construido. Mínimo {self.config.min_audios_for_vocab} audios.",
            }

        try:
            # Extraer características de query
            descriptors, metadata = self.extractor.extract(query_path)

            if descriptors is None:
                return {"success": False, "error": metadata.get("error", "Error")}

            # Obtener histograma
            histogram = self.codebook.get_histogram(descriptors)

            # Aplicar TF-IDF
            if self.tfidf.idf_vector is None:
                return {"success": False, "error": "IDF no calculado"}

            query_vector = self.tfidf.compute_tfidf(histogram)

            # Buscar
            use_inv = (
                use_inverted
                if use_inverted is not None
                else self.config.use_inverted_index
            )

            if use_inv and self.inverted_index is not None:
                raw_results = self.inverted_index.search(query_vector, k)
            elif self.knn_sequential is not None:
                raw_results = self.knn_sequential.search(query_vector, k)
            else:
                return {"success": False, "error": "No hay índice de búsqueda"}

            # Enriquecer resultados con información del Heap
            results = []
            for pos, similarity, name in raw_results:
                info = self._get_audio_info_by_name(name)
                if info:
                    info["similarity"] = round(similarity, 4)
                    results.append(info)

            return {
                "success": True,
                "results": results,
                "query_duration": metadata.get("duration", 0),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_audios(self) -> List[Dict[str, Any]]:
        """Obtiene todos los audios indexados."""
        records = self.audios_heap.scan_all()
        return [
            {**self._record_to_dict(r), "position": i} for i, r in enumerate(records)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del índice."""
        num_audios = self.audios_heap.count()
        num_frames = 0

        if os.path.exists(self.descriptors_path):
            with np.load(self.descriptors_path) as data:
                for key in data.files:
                    num_frames += len(data[key])

        stats = {
            "num_audios": num_audios,
            "num_frames": num_frames,
            "vocabulary_size": self.codebook.vocabulary_size,
            "has_vocabulary": os.path.exists(self.codebook_path),
            "has_idf": self.tfidf.idf_vector is not None,
            "search_method": (
                "inverted_index" if self.config.use_inverted_index else "sequential"
            ),
        }

        if self.inverted_index:
            stats["inverted_stats"] = self.inverted_index.get_stats()

        return stats

    def rebuild_index(self) -> Dict[str, Any]:
        """Reconstruye completamente el índice."""
        print("[AudioEngine] Reconstruyendo índice completo...")

        if not os.path.exists(self.descriptors_path):
            return {"success": False, "error": "No hay descriptores"}

        if os.path.exists(self.codebook_path):
            os.remove(self.codebook_path)

        if not self._build_vocabulary():
            return {"success": False, "error": "Error construyendo vocabulario"}

        if not self._rebuild_all_vectors():
            return {"success": False, "error": "Error reconstruyendo vectores"}

        return {"success": True, "stats": self.get_stats()}

    def clear_all(self) -> Dict[str, Any]:
        """Limpia todos los datos."""
        self._clear_all()
        self._initialize()
        return {"success": True, "message": "Índice limpiado"}

    # MÉTODOS INTERNOS

    def _save_descriptors(self, name: str, descriptors: np.ndarray):
        """Guarda descriptores de forma incremental."""
        if os.path.exists(self.descriptors_path):
            descs = dict(np.load(self.descriptors_path))
        else:
            descs = {}

        descs[name] = descriptors
        np.savez_compressed(self.descriptors_path, **descs)

    def _count_audios(self) -> int:
        """Cuenta audios con descriptores."""
        if os.path.exists(self.descriptors_path):
            with np.load(self.descriptors_path) as data:
                return len(data.files)
        return 0

    def _should_rebuild_vocab(self, current_audios: int) -> bool:
        """Determina si reconstruir vocabulario."""
        if not os.path.exists(self.codebook_path):
            return current_audios >= self.config.min_audios_for_vocab

        if self._vocab_audios_count > 0:
            return (
                current_audios
                >= self._vocab_audios_count * self.config.vocab_rebuild_ratio
            )

        return False

    def _build_vocabulary(self) -> bool:
        """Construye vocabulario de audio."""
        if not os.path.exists(self.descriptors_path):
            return False

        with np.load(self.descriptors_path) as data:
            descriptors_dict = {key: data[key] for key in data.files}

        self.codebook.build_from_dict(descriptors_dict)
        self.codebook.save(self.codebook_path)

        self._vocab_audios_count = len(descriptors_dict)
        self._save_state()

        return True

    def _rebuild_all_vectors(self) -> bool:
        """Reconstruye todos los vectores TF-IDF."""
        if not os.path.exists(self.codebook_path):
            return False
        if not os.path.exists(self.descriptors_path):
            return False

        # Calcular histogramas
        histograms = {}
        with np.load(self.descriptors_path) as data:
            for name in data.files:
                histograms[name] = self.codebook.get_histogram(data[name])

        if not histograms:
            return False

        # Calcular TF-IDF
        tfidf_vectors = self.tfidf.compute_all_tfidf(histograms)
        self.tfidf.save_idf(self.idf_path)

        # Guardar vectores y mapa
        self._save_vectors_matrix(tfidf_vectors)

        return True

    def _save_vectors_matrix(self, tfidf_vectors: Dict[str, np.ndarray]):
        """Guarda matriz de vectores y mapa de índices."""
        index_map = sorted(tfidf_vectors.keys())

        vectors_matrix = np.array([tfidf_vectors[name] for name in index_map])
        np.save(self.vectors_path, vectors_matrix)

        with open(self.index_map_path, "w") as f:
            json.dump(index_map, f)

        # Reconstruir índices de búsqueda
        self.knn_sequential = KNNSequentialSearch()
        self.knn_sequential.build_index(tfidf_vectors, index_map)

        self.inverted_index = InvertedIndex()
        self.inverted_index.build_index(tfidf_vectors, index_map)

    def _update_single_audio(self, name: str, descriptors: np.ndarray, pos: int):
        """Actualiza un solo audio en el índice."""
        # No implementado para audio simple - requiere rebuild
        pass

    def _get_audio_info_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtiene información de audio por nombre de descriptor."""
        # Extraer ID del nombre (formato: audio_ID)
        try:
            audio_id = int(name.replace("audio_", ""))
        except ValueError:
            return None

        # Buscar en Heap
        records = self.audios_heap.scan_all()
        for i, record in enumerate(records):
            info = self._record_to_dict(record)
            if info["id"] == audio_id:
                info["position"] = i
                return info

        return None
