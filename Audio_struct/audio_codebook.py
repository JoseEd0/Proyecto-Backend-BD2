"""
audio_codebook.py - Vocabulario de Audio (Bag of Audio Words)

Similar a Visual Codebook en imágenes:
- Agrupa frames MFCC similares en clusters (K-Means)
- Cada cluster = "palabra de audio" (sonido característico)
- Permite representar cualquier audio como histograma de palabras

Pipeline:
1. Recolectar MFCCs de todos los audios
2. Aplicar MiniBatchKMeans para encontrar K centroides
3. Cada audio → asignar frames a clusters → histograma
"""

import numpy as np
import os
import pickle
from typing import Dict, Optional, List
from sklearn.cluster import MiniBatchKMeans


class AudioCodebook:
    """Diccionario de palabras de audio usando K-Means."""

    def __init__(
        self,
        n_clusters: int = 256,  # Menos clusters que SIFT (audio es más homogéneo)
        batch_size: int = 1024,
        random_state: int = 42,
    ):
        """
        Args:
            n_clusters: Número de palabras de audio
            batch_size: Tamaño de batch para MiniBatchKMeans
            random_state: Semilla para reproducibilidad
        """
        self.n_clusters = n_clusters
        self.batch_size = batch_size
        self.random_state = random_state
        self.kmeans: Optional[MiniBatchKMeans] = None
        self.vocabulary_size = 0

    def build_from_dict(self, descriptors_dict: Dict[str, np.ndarray]) -> bool:
        """
        Construye vocabulario desde diccionario de descriptores.

        Args:
            descriptors_dict: {nombre_audio: matriz_mfcc}

        Returns:
            True si exitoso
        """
        if not descriptors_dict:
            print("[AudioCodebook] No hay descriptores")
            return False

        # Apilar todos los descriptores
        all_descriptors = []
        for name, descs in descriptors_dict.items():
            if descs is not None and len(descs) > 0:
                all_descriptors.append(descs)

        if not all_descriptors:
            return False

        all_descriptors = np.vstack(all_descriptors)
        print(f"[AudioCodebook] Total frames: {len(all_descriptors)}")

        # Calcular K óptimo
        optimal_k = self._calculate_optimal_k(
            len(all_descriptors), len(descriptors_dict)
        )
        self.n_clusters = optimal_k

        print(f"[AudioCodebook] Construyendo vocabulario con K={optimal_k}")

        # Entrenar K-Means
        self.kmeans = MiniBatchKMeans(
            n_clusters=self.n_clusters,
            batch_size=min(self.batch_size, len(all_descriptors)),
            random_state=self.random_state,
            n_init=3,
        )
        self.kmeans.fit(all_descriptors)
        self.vocabulary_size = self.n_clusters

        print(
            f"[AudioCodebook] Vocabulario construido: {self.vocabulary_size} palabras"
        )
        return True

    def _calculate_optimal_k(self, total_frames: int, n_audios: int) -> int:
        """
        Calcula K óptimo basado en cantidad de datos.

        Para audio:
        - Menos clusters que imágenes (sonidos más homogéneos)
        - K entre 64 y 512
        """
        # Regla: sqrt(total_frames / 20)
        k = int(np.sqrt(total_frames / 20))

        # Límites
        min_k = max(32, n_audios * 2)  # Mínimo 2 clusters por audio
        max_k = min(512, total_frames // 50)  # Máximo: al menos 50 frames por cluster

        k = max(min_k, min(k, max_k))
        return k

    def get_histogram(self, descriptors: np.ndarray) -> np.ndarray:
        """
        Genera histograma de palabras de audio.

        Args:
            descriptors: MFCCs de un audio (n_frames, dim)

        Returns:
            Histograma de frecuencias (vocabulary_size,)
        """
        if self.kmeans is None:
            raise ValueError("Vocabulario no construido")

        if descriptors is None or len(descriptors) == 0:
            return np.zeros(self.vocabulary_size)

        # Asignar cada frame al cluster más cercano
        labels = self.kmeans.predict(descriptors)

        # Contar frecuencias
        histogram = np.bincount(labels, minlength=self.vocabulary_size)

        return histogram.astype(np.float32)

    def save(self, path: str):
        """Guarda vocabulario en disco."""
        data = {
            "kmeans": self.kmeans,
            "n_clusters": self.n_clusters,
            "vocabulary_size": self.vocabulary_size,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        print(f"[AudioCodebook] Guardado en {path}")

    def load(self, path: str) -> bool:
        """Carga vocabulario desde disco."""
        if not os.path.exists(path):
            return False

        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.kmeans = data["kmeans"]
            self.n_clusters = data["n_clusters"]
            self.vocabulary_size = data["vocabulary_size"]
            print(f"[AudioCodebook] Cargado: {self.vocabulary_size} palabras")
            return True
        except Exception as e:
            print(f"[AudioCodebook] Error cargando: {e}")
            return False


# Alias
VisualCodebook = AudioCodebook
