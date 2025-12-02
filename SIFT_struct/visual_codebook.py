"""
Visual Codebook Module - Diccionario Visual con K-Means

Implementación de Bag of Visual Words (BoVW) siguiendo mejores prácticas:
- Regla de Sturges/sqrt para número óptimo de clusters
- MiniBatchKMeans para escalabilidad (60K+ imágenes)
- Cálculo dinámico de K según tamaño del dataset

Referencias:
- Sivic & Zisserman (2003) "Video Google"
- Csurka et al. (2004) "Visual Categorization with BoVW"
"""

import numpy as np
import joblib
import os
from typing import Dict, Optional
from sklearn.cluster import MiniBatchKMeans


class VisualCodebook:
    """
    Diccionario Visual basado en K-Means clustering.

    Cada cluster representa una "visual word" (palabra visual).
    Los descriptores SIFT se cuantifican al centroide más cercano.

    Escalable para datasets pequeños (30 imgs) hasta muy grandes (60K+ imgs).
    """

    def __init__(
        self,
        n_clusters: int = 1000,
        random_state: int = 42,
        batch_size: int = 4096,
        max_iter: int = 300,
        n_init: int = 3,
    ):
        """
        Args:
            n_clusters: Número de clusters (visual words)
            random_state: Semilla para reproducibilidad
            batch_size: Tamaño de batch para MiniBatchKMeans
            max_iter: Iteraciones máximas
            n_init: Número de inicializaciones
        """
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.batch_size = batch_size
        self.max_iter = max_iter
        self.n_init = n_init
        self.kmeans: Optional[MiniBatchKMeans] = None
        self._is_fitted = False

    @staticmethod
    def calculate_optimal_clusters(total_descriptors: int, num_images: int) -> int:
        """
        Calcula número óptimo de clusters según mejores prácticas.

        Reglas empíricas de la literatura:
        1. sqrt(N/2) donde N = total descriptores (regla clásica)
        2. ~100 descriptores por cluster es un buen balance
        3. Escala logarítmica para datasets muy grandes

        Args:
            total_descriptors: Total de descriptores SIFT
            num_images: Número de imágenes en el dataset

        Returns:
            Número óptimo de clusters
        """
        # Para datasets pequeños: más agresivo
        if num_images < 100:
            # ~80-100 descriptores por cluster
            k_optimal = total_descriptors // 80
            k_min = 500
            k_max = 5000

        # Para datasets medianos (100-10K imágenes)
        elif num_images < 10000:
            # sqrt(N/2) es regla clásica
            k_optimal = int(np.sqrt(total_descriptors / 2))
            k_min = 1000
            k_max = 10000

        # Para datasets grandes (10K+ imágenes)
        else:
            # Escala sub-lineal para evitar overhead
            k_optimal = int(1000 * np.log10(num_images))
            k_min = 5000
            k_max = 50000

        # Aplicar límites
        k_final = max(k_min, min(k_optimal, k_max))

        # Redondear a centenas
        return ((k_final + 50) // 100) * 100

    def build(
        self, descriptors: np.ndarray, n_clusters: Optional[int] = None
    ) -> "VisualCodebook":
        """
        Construye el codebook usando MiniBatchKMeans.

        Args:
            descriptors: Array de descriptores (N, 128)
            n_clusters: Override del número de clusters

        Returns:
            self para encadenamiento
        """
        if n_clusters is not None:
            self.n_clusters = n_clusters

        # Asegurar tipo float32 para eficiencia
        if descriptors.dtype != np.float32:
            descriptors = descriptors.astype(np.float32)

        # Ajustar batch_size dinámicamente
        actual_batch = min(self.batch_size, max(100, len(descriptors) // 10))

        print(f"[CODEBOOK] Construyendo vocabulario:")
        print(f"  - Descriptores: {len(descriptors):,}")
        print(f"  - Clusters (K): {self.n_clusters:,}")

        self.kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            random_state=self.random_state,
            batch_size=actual_batch,
            n_init=self.n_init,
            max_iter=self.max_iter,
            compute_labels=False,
        )

        self.kmeans.fit(descriptors)
        self._is_fitted = True

        print(f"[CODEBOOK] ✓ Vocabulario creado: {self.n_clusters} visual words")
        return self

    def build_from_dict(
        self, descriptors_dict: Dict[str, np.ndarray]
    ) -> "VisualCodebook":
        """
        Construye codebook desde diccionario de descriptores.

        Args:
            descriptors_dict: {nombre_imagen: descriptors_array}

        Returns:
            self
        """
        all_descriptors = np.vstack(list(descriptors_dict.values()))
        num_images = len(descriptors_dict)

        optimal_k = self.calculate_optimal_clusters(len(all_descriptors), num_images)
        print(f"[CODEBOOK] K óptimo calculado: {optimal_k} para {num_images} imágenes")

        return self.build(all_descriptors, n_clusters=optimal_k)

    def assign(self, descriptors: np.ndarray) -> np.ndarray:
        """
        Asigna cada descriptor a su visual word más cercana.

        Args:
            descriptors: Array de descriptores (N, 128)

        Returns:
            Array de índices de cluster (N,)
        """
        if not self._is_fitted:
            raise ValueError("Codebook no entrenado. Llamar build() primero.")

        if descriptors.dtype != np.float32:
            descriptors = descriptors.astype(np.float32)

        return self.kmeans.predict(descriptors)

    def compute_histogram(self, descriptors: np.ndarray) -> np.ndarray:
        """
        Calcula histograma de visual words (BoVW).

        Args:
            descriptors: Descriptores de una imagen (N, 128)

        Returns:
            Histograma de frecuencias (n_clusters,)
        """
        assignments = self.assign(descriptors)
        histogram = np.bincount(assignments, minlength=self.n_clusters)
        return histogram.astype(np.float32)

    def save(self, path: str):
        """Guarda el codebook en disco."""
        if not self._is_fitted:
            raise ValueError("Codebook no entrenado.")

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

        data = {
            "kmeans": self.kmeans,
            "n_clusters": self.n_clusters,
        }
        joblib.dump(data, path)
        print(f"[CODEBOOK] Guardado: {path}")

    def load(self, path: str) -> "VisualCodebook":
        """Carga codebook desde disco."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Codebook no encontrado: {path}")

        data = joblib.load(path)
        self.kmeans = data["kmeans"]
        self.n_clusters = data.get("n_clusters", self.kmeans.n_clusters)
        self._is_fitted = True

        print(f"[CODEBOOK] Cargado: {self.n_clusters} clusters")
        return self

    @property
    def vocabulary_size(self) -> int:
        """Tamaño del vocabulario visual."""
        return self.n_clusters if self._is_fitted else 0

    @property
    def centroids(self) -> Optional[np.ndarray]:
        """Centroides del clustering."""
        if self._is_fitted and self.kmeans is not None:
            return self.kmeans.cluster_centers_
        return None
