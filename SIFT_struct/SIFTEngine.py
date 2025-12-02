"""
SIFTEngine - Motor Principal de Recuperación de Imágenes por Similitud

Integra los módulos del pipeline CBIR (Content-Based Image Retrieval):
1. feature_extractor: Extracción SIFT/RootSIFT
2. visual_codebook: Diccionario visual (K-Means)
3. tfidf_weighting: Ponderación TF-IDF
4. knn_sequential: Búsqueda KNN con heap
5. knn_inverted: Búsqueda KNN con índice invertido

Usa la estructura Heap del proyecto para almacenamiento persistente.

Escalable desde 10 hasta 60K+ imágenes.
"""

import os
import sys
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import threading

# Agregar path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importar módulos SIFT
from SIFT_struct.feature_extractor import SIFTExtractor
from SIFT_struct.visual_codebook import VisualCodebook
from SIFT_struct.tfidf_weighting import TFIDFWeighter
from SIFT_struct.knn_sequential import KNNSequentialSearch
from SIFT_struct.knn_inverted import InvertedIndex

# Importar estructura Heap del proyecto
from Heap_struct.Heap import Heap


@dataclass
class SIFTConfig:
    """Configuración del motor SIFT."""

    # Procesamiento de imagen
    image_size: int = 512
    use_root_sift: bool = True
    min_descriptors: int = 5  # Mínimo bajo para imágenes con fondos simples

    # Vocabulario
    min_images_for_vocab: int = 10
    vocab_rebuild_ratio: float = 2.0  # Reconstruir cuando imgs * ratio

    # Búsqueda
    use_inverted_index: bool = True
    default_k: int = 10


class SIFTEngine:
    """
    Motor de Recuperación de Imágenes basado en SIFT + BoVW + TF-IDF.

    Pipeline completo:
    1. Imagen → SIFT descriptors
    2. Descriptors → Visual words (cuantificación)
    3. Visual words → Histogram (BoVW)
    4. Histogram → TF-IDF vector
    5. TF-IDF → KNN search

    Ejemplo:
        engine = SIFTEngine(base_dir=".", data_dir="api/data/sift")
        engine.add_image(1, "gato.jpg", "/path/to/gato.jpg")
        results = engine.search("/path/to/query.jpg", k=5)
    """

    def __init__(
        self,
        base_dir: str,
        data_dir: str = "api/data/sift",
        config: Optional[SIFTConfig] = None,
        force_create: bool = False,
    ):
        """
        Inicializa el motor SIFT.

        Args:
            base_dir: Directorio base del proyecto
            data_dir: Subdirectorio para datos SIFT
            config: Configuración (opcional)
            force_create: Si True, reinicia todos los datos
        """
        self.base_dir = os.path.abspath(base_dir)
        self.config = config or SIFTConfig()

        # Configurar directorios
        self.data_dir = os.path.join(self.base_dir, data_dir)
        self.desc_dir = os.path.join(self.base_dir, "SIFT_struct", "descriptors")
        self.img_dir = os.path.join(self.base_dir, "SIFT_struct", "processed_images")

        for d in [self.data_dir, self.desc_dir, self.img_dir]:
            os.makedirs(d, exist_ok=True)

        # Configurar rutas de archivos
        self._setup_paths()

        # Lock para thread safety
        self._lock = threading.Lock()

        # Estado
        self._vocab_images_count = 0

        # Inicializar componentes
        self.extractor = SIFTExtractor(
            target_size=self.config.image_size,
            use_root_sift=self.config.use_root_sift,
        )
        self.codebook = VisualCodebook()
        self.tfidf = TFIDFWeighter()

        # Índices de búsqueda (se cargan después)
        self.knn_sequential: Optional[KNNSequentialSearch] = None
        self.inverted_index: Optional[InvertedIndex] = None

        if force_create:
            self._clear_all()

        self._initialize()

    def _setup_paths(self):
        """Configura rutas de archivos."""
        self.heap_path = os.path.join(self.data_dir, "images.heap")
        self.descriptors_path = os.path.join(self.desc_dir, "all_descriptors.npz")
        self.codebook_path = os.path.join(self.desc_dir, "codebook.pkl")
        self.idf_path = os.path.join(self.desc_dir, "idf_vector.npy")
        self.vectors_path = os.path.join(self.desc_dir, "tfidf_vectors.npy")
        self.index_map_path = os.path.join(self.desc_dir, "index_map.json")
        self.state_path = os.path.join(self.desc_dir, "state.json")

    def _initialize(self):
        """Inicializa Heap y carga estado."""
        # Heap para metadatos de imágenes usando estructura del proyecto
        table_format = {"id": "i", "nombre": "100s", "ruta": "200s"}
        self.images_heap = Heap(table_format, "id", self.heap_path, force_create=False)

        # Cargar estado persistido
        self._load_state()

        # Cargar componentes
        self._load_components()

    def _load_state(self):
        """Carga estado desde disco."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r") as f:
                    state = json.load(f)
                self._vocab_images_count = state.get("vocab_images_count", 0)
            except Exception:
                pass

    def _save_state(self):
        """Guarda estado en disco."""
        state = {
            "vocab_images_count": self._vocab_images_count,
            "vocabulary_size": self.codebook.vocabulary_size,
        }
        with open(self.state_path, "w") as f:
            json.dump(state, f)

    def _load_components(self):
        """Carga componentes desde disco."""
        # Cargar codebook
        if os.path.exists(self.codebook_path):
            try:
                self.codebook.load(self.codebook_path)
            except Exception as e:
                print(f"[SIFT] Error cargando codebook: {e}")

        # Cargar IDF
        if os.path.exists(self.idf_path):
            try:
                self.tfidf.load_idf(self.idf_path)
            except Exception as e:
                print(f"[SIFT] Error cargando IDF: {e}")

        # Cargar índices de búsqueda
        self._load_search_indices()

    def _load_search_indices(self):
        """Carga índices de búsqueda."""
        if not os.path.exists(self.vectors_path):
            return
        if not os.path.exists(self.index_map_path):
            return

        try:
            # Cargar vectores
            vectors_matrix = np.load(self.vectors_path)

            # Cargar mapeo
            with open(self.index_map_path, "r") as f:
                index_map = json.load(f)

            # Construir metadata desde Heap
            metadata = {}
            records = self.images_heap.scan_all()
            for pos, record in enumerate(records):
                metadata[pos] = self._record_to_dict(record)

            # Inicializar KNN secuencial
            self.knn_sequential = KNNSequentialSearch(vectors_matrix, metadata)

            # Inicializar índice invertido
            if self.config.use_inverted_index:
                tfidf_dict = {
                    pos: vectors_matrix[pos] for pos in range(len(vectors_matrix))
                }
                self.inverted_index = InvertedIndex()
                self.inverted_index.build(tfidf_dict, metadata)

        except Exception as e:
            print(f"[SIFT] Error cargando índices: {e}")

    def _record_to_dict(self, record: list) -> Dict[str, Any]:
        """Convierte registro del Heap a diccionario."""

        def decode(val):
            if isinstance(val, bytes):
                return val.decode("utf-8").strip().rstrip("\x00")
            return str(val).strip()

        return {
            "id": record[0],
            "nombre": decode(record[1]),
            "ruta": decode(record[2]),
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

        # Limpiar imágenes procesadas
        if os.path.exists(self.img_dir):
            for f in os.listdir(self.img_dir):
                os.remove(os.path.join(self.img_dir, f))

    # API PÚBLICA

    def add_image(
        self, image_id: int, image_name: str, image_path: str
    ) -> Dict[str, Any]:
        """
        Agrega una imagen al índice.

        Args:
            image_id: ID único
            image_name: Nombre descriptivo
            image_path: Ruta al archivo

        Returns:
            Dict con resultado de la operación
        """
        with self._lock:
            # Nombre base para archivos
            base_name = f"{os.path.splitext(image_name)[0]}_{image_id}"

            # Extraer descriptores SIFT
            descriptors, processed_path = self.extractor.process_and_extract(
                image_path,
                self.img_dir,
                base_name,
                min_descriptors=self.config.min_descriptors,
            )

            if descriptors is None:
                return {
                    "success": False,
                    "error": f"Muy pocos descriptores (mínimo: {self.config.min_descriptors})",
                }

            # Insertar en Heap
            record = [image_id, image_name, image_path]
            position = self.images_heap.insert(record)

            # Guardar descriptores
            self._save_descriptors(base_name, descriptors)

            # Verificar si construir/reconstruir vocabulario
            num_images = self._count_images()

            if self._should_rebuild_vocab(num_images):
                print(f"[SIFT] Reconstruyendo vocabulario ({num_images} imágenes)...")
                if self._build_vocabulary():
                    self._rebuild_all_vectors()
                    return {
                        "success": True,
                        "status": "indexed_with_vocab_rebuild",
                        "position": position,
                        "descriptors": len(descriptors),
                        "vocabulary_size": self.codebook.vocabulary_size,
                        "has_vocabulary": True,
                    }

            # Si hay vocabulario, indexar esta imagen
            if os.path.exists(self.codebook_path):
                self._update_single_image(base_name, descriptors, position)
                return {
                    "success": True,
                    "status": "indexed",
                    "position": position,
                    "descriptors": len(descriptors),
                    "has_vocabulary": True,
                }

            # Sin vocabulario aún
            return {
                "success": True,
                "status": "pending_vocabulary",
                "position": position,
                "descriptors": len(descriptors),
                "images_needed": self.config.min_images_for_vocab - num_images,
                "has_vocabulary": False,
            }

    def search(
        self, query_path: str, k: int = 10, use_inverted: Optional[bool] = None
    ) -> List[Tuple[int, float, Dict]]:
        """
        Busca las k imágenes más similares.

        Args:
            query_path: Ruta a la imagen de búsqueda
            k: Número de resultados
            use_inverted: Usar índice invertido (None = config default)

        Returns:
            Lista de (posición, similitud, info)
        """
        if not os.path.exists(self.codebook_path):
            raise ValueError(
                f"Vocabulario no disponible. Mínimo {self.config.min_images_for_vocab} imágenes."
            )

        # Crear imagen temporal procesada
        temp_path = os.path.join(self.img_dir, "__query_temp__.jpg")

        if not self.extractor.resize_image(query_path, temp_path):
            raise ValueError("Error procesando imagen de consulta")

        try:
            # Extraer descriptores
            descriptors = self.extractor.extract(temp_path)
            if descriptors is None:
                raise ValueError("No se pudieron extraer características")

            # Calcular histograma y TF-IDF
            histogram = self.codebook.compute_histogram(descriptors)
            query_tfidf = self.tfidf.compute_tfidf(histogram)

            # Decidir método de búsqueda
            use_inv = (
                use_inverted
                if use_inverted is not None
                else self.config.use_inverted_index
            )

            if use_inv and self.inverted_index is not None:
                raw_results = self.inverted_index.search(query_tfidf, k)
                results = [
                    (doc_id, sim, self._get_image_info(doc_id) or {})
                    for doc_id, sim in raw_results
                ]
            elif self.knn_sequential is not None:
                raw_results = self.knn_sequential.search_with_metadata(query_tfidf, k)
                results = [(idx, sim, meta) for idx, sim, meta in raw_results]
            else:
                raise ValueError("No hay índice de búsqueda disponible")

            return results

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def get_all_images(self) -> List[Dict[str, Any]]:
        """Obtiene todas las imágenes indexadas."""
        records = self.images_heap.scan_all()
        return [
            {**self._record_to_dict(r), "position": i} for i, r in enumerate(records)
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del índice."""
        num_images = self.images_heap.count()
        num_descriptors = 0

        if os.path.exists(self.descriptors_path):
            try:
                with np.load(self.descriptors_path) as data:
                    num_descriptors = sum(len(data[k]) for k in data.files)
            except Exception:
                pass

        stats = {
            "num_images": num_images,
            "num_descriptors": num_descriptors,
            "vocabulary_size": self.codebook.vocabulary_size,
            "has_vocabulary": os.path.exists(self.codebook_path),
            "has_idf": self.tfidf.idf_vector is not None,
            "search_method": (
                "inverted_index" if self.config.use_inverted_index else "sequential"
            ),
        }

        if self.inverted_index:
            stats["inverted_index"] = self.inverted_index.get_stats()

        return stats

    def rebuild_index(self) -> Dict[str, Any]:
        """Reconstruye completamente el índice."""
        print("[SIFT] Reconstruyendo índice completo...")

        if not os.path.exists(self.descriptors_path):
            return {"success": False, "error": "No hay descriptores"}

        # Eliminar vocabulario existente
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
            with np.load(self.descriptors_path) as data:
                descs = dict(data)
        else:
            descs = {}

        descs[name] = descriptors
        np.savez_compressed(self.descriptors_path, **descs)

    def _count_images(self) -> int:
        """Cuenta imágenes con descriptores."""
        if os.path.exists(self.descriptors_path):
            with np.load(self.descriptors_path) as data:
                return len(data.files)
        return 0

    def _should_rebuild_vocab(self, current_images: int) -> bool:
        """Determina si reconstruir vocabulario."""
        # Primera construcción
        if not os.path.exists(self.codebook_path):
            return current_images >= self.config.min_images_for_vocab

        # Reconstruir si duplicamos imágenes
        if self._vocab_images_count > 0:
            ratio = current_images / self._vocab_images_count
            return ratio >= self.config.vocab_rebuild_ratio

        return False

    def _build_vocabulary(self) -> bool:
        """Construye vocabulario visual."""
        if not os.path.exists(self.descriptors_path):
            return False

        with np.load(self.descriptors_path) as data:
            if len(data.files) < self.config.min_images_for_vocab:
                return False
            descriptors_dict = {key: data[key] for key in data.files}

        # Construir codebook
        self.codebook.build_from_dict(descriptors_dict)
        self.codebook.save(self.codebook_path)

        # Actualizar estado
        self._vocab_images_count = len(descriptors_dict)
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
            for key in data.files:
                histograms[key] = self.codebook.compute_histogram(data[key])

        if not histograms:
            return False

        # Calcular TF-IDF
        tfidf_vectors = self.tfidf.compute_all_tfidf(histograms)
        self.tfidf.save_idf(self.idf_path)

        # Guardar matriz de vectores
        self._save_vectors_matrix(tfidf_vectors)

        # Recargar índices
        self._load_search_indices()

        print(f"[SIFT] ✓ {len(tfidf_vectors)} vectores reconstruidos")
        return True

    def _save_vectors_matrix(self, tfidf_vectors: Dict[str, np.ndarray]):
        """Guarda vectores como matriz numpy alineada con Heap."""
        records = self.images_heap.scan_all()
        vec_dim = self.codebook.vocabulary_size

        vectors_list = []
        index_map = {}

        for pos, record in enumerate(records):
            info = self._record_to_dict(record)
            nombre_base = os.path.splitext(info["nombre"])[0] + f"_{info['id']}"

            if nombre_base in tfidf_vectors:
                vectors_list.append(tfidf_vectors[nombre_base])
            else:
                vectors_list.append(np.zeros(vec_dim, dtype=np.float32))

            index_map[str(pos)] = nombre_base

        if vectors_list:
            np.save(self.vectors_path, np.array(vectors_list))

        with open(self.index_map_path, "w") as f:
            json.dump(index_map, f)

    def _update_single_image(self, name: str, descriptors: np.ndarray, pos: int):
        """Actualiza índice para una sola imagen (reconstruye todo por simplicidad)."""
        self._rebuild_all_vectors()

    def _get_image_info(self, pos: int) -> Optional[Dict[str, Any]]:
        """Obtiene info de imagen por posición."""
        try:
            records = self.images_heap.scan_all()
            if pos < len(records):
                return self._record_to_dict(records[pos])
        except Exception:
            pass
        return None
