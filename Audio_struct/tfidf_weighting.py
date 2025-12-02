"""
tfidf_weighting.py - Ponderación TF-IDF para Audio

Mismo principio que en imágenes/texto:
- TF: Frecuencia de cada palabra de audio (normalizada con log)
- IDF: Penaliza palabras comunes en muchos audios
- Resultado: Palabras distintivas tienen mayor peso

Mejora discriminación entre géneros/tipos de audio.
"""

import numpy as np
from typing import Dict, Optional


class AudioTFIDFWeighter:
    """Calcula y aplica ponderación TF-IDF a histogramas de audio."""

    def __init__(self):
        self.idf_vector: Optional[np.ndarray] = None
        self.n_documents = 0

    def compute_idf(self, histograms: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Calcula vector IDF desde histogramas.

        IDF_i = log(N / df_i) + 1
        donde:
            N = número de documentos
            df_i = documentos que contienen palabra i

        Args:
            histograms: {nombre: histograma}

        Returns:
            Vector IDF
        """
        if not histograms:
            raise ValueError("No hay histogramas")

        # Apilar histogramas
        hist_matrix = np.array(list(histograms.values()))
        self.n_documents = len(hist_matrix)

        # Calcular document frequency (cuántos audios tienen cada palabra)
        # df_i = número de documentos donde histogram[i] > 0
        df = np.sum(hist_matrix > 0, axis=0) + 1  # +1 para evitar división por 0

        # IDF con suavizado
        self.idf_vector = np.log(self.n_documents / df) + 1

        return self.idf_vector

    def compute_tfidf(self, histogram: np.ndarray) -> np.ndarray:
        """
        Calcula vector TF-IDF para un histograma.

        TF = log(1 + frecuencia)
        TF-IDF = TF * IDF, normalizado L2

        Args:
            histogram: Histograma de palabras de audio

        Returns:
            Vector TF-IDF normalizado
        """
        if self.idf_vector is None:
            raise ValueError("IDF no calculado. Llamar compute_idf primero.")

        # TF con suavizado logarítmico
        tf = np.log1p(histogram)

        # TF-IDF
        tfidf = tf * self.idf_vector

        # Normalización L2
        norm = np.linalg.norm(tfidf)
        if norm > 0:
            tfidf = tfidf / norm

        return tfidf.astype(np.float32)

    def compute_all_tfidf(
        self, histograms: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Calcula TF-IDF para todos los histogramas.

        Args:
            histograms: {nombre: histograma}

        Returns:
            {nombre: vector_tfidf}
        """
        # Primero calcular IDF global
        self.compute_idf(histograms)

        # Luego TF-IDF para cada audio
        tfidf_vectors = {}
        for name, hist in histograms.items():
            tfidf_vectors[name] = self.compute_tfidf(hist)

        return tfidf_vectors

    def save_idf(self, path: str):
        """Guarda vector IDF."""
        if self.idf_vector is not None:
            np.save(path, self.idf_vector)

    def load_idf(self, path: str) -> bool:
        """Carga vector IDF."""
        try:
            self.idf_vector = np.load(path)
            return True
        except Exception:
            return False


# Alias para consistencia
TFIDFWeighter = AudioTFIDFWeighter
