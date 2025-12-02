"""
TF-IDF Weighting Module - Ponderación para Visual Words

Implementación estándar de TF-IDF para Bag of Visual Words:
- TF: Term Frequency (frecuencia en la imagen)
- IDF: Inverse Document Frequency (rareza en la colección)
- Power normalization opcional (mejora discriminación)

Referencias:
- Jégou et al. (2010) "Aggregating local descriptors into a compact image representation"
- Arandjelović & Zisserman (2012) "Three things everyone should know"
"""

import numpy as np
from typing import Dict, Optional


class TFIDFWeighter:
    """
    Ponderador TF-IDF para histogramas de visual words.

    TF-IDF asigna mayor peso a visual words que son:
    - Frecuentes en la imagen actual (TF alto)
    - Raras en la colección general (IDF alto)
    """

    def __init__(self, power_norm_alpha: float = 0.5, use_log_tf: bool = True):
        """
        Args:
            power_norm_alpha: Exponente para power normalization (0.5 = sqrt)
            use_log_tf: Usar log(1 + TF) en lugar de TF raw
        """
        self.power_norm_alpha = power_norm_alpha
        self.use_log_tf = use_log_tf
        self.idf_vector: Optional[np.ndarray] = None
        self.num_documents: int = 0
        self.vocabulary_size: int = 0

    def compute_idf(self, histograms: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Calcula vector IDF desde colección de histogramas.

        Fórmula estándar: IDF_i = log(N / df_i)
        Con suavizado: IDF_i = log((N + 1) / (df_i + 1)) + 1

        Args:
            histograms: {nombre: histogram_array}

        Returns:
            Vector IDF (vocabulary_size,)
        """
        if not histograms:
            raise ValueError("No hay histogramas para calcular IDF")

        # Determinar dimensiones
        sample = next(iter(histograms.values()))
        self.vocabulary_size = len(sample)
        self.num_documents = len(histograms)

        # Normalizar histogramas a misma dimensión
        matrix = np.zeros((self.num_documents, self.vocabulary_size), dtype=np.float32)
        for i, hist in enumerate(histograms.values()):
            length = min(len(hist), self.vocabulary_size)
            matrix[i, :length] = hist[:length]

        # Document frequency: número de docs donde aparece cada palabra
        df = np.sum(matrix > 0, axis=0).astype(np.float32)

        # IDF con suavizado estándar
        # Fórmula: log((N + 1) / (df + 1)) + 1
        # Esto evita división por cero y valores negativos
        self.idf_vector = np.log((self.num_documents + 1) / (df + 1)) + 1
        self.idf_vector = self.idf_vector.astype(np.float32)

        # Estadísticas
        active_words = np.sum(df > 0)
        print(f"[TF-IDF] IDF calculado:")
        print(f"  - Documentos: {self.num_documents}")
        print(f"  - Visual words activas: {active_words}/{self.vocabulary_size}")
        print(
            f"  - IDF rango: [{self.idf_vector.min():.2f}, {self.idf_vector.max():.2f}]"
        )

        return self.idf_vector

    def compute_tfidf(self, histogram: np.ndarray) -> np.ndarray:
        """
        Calcula vector TF-IDF para un histograma.

        Pipeline:
        1. TF: log(1 + count) o count^alpha
        2. Multiplicar por IDF
        3. L2 normalización

        Args:
            histogram: Histograma de visual words

        Returns:
            Vector TF-IDF L2-normalizado
        """
        if self.idf_vector is None:
            raise ValueError("IDF no calculado. Llamar compute_idf() primero.")

        # Ajustar dimensiones
        hist = np.zeros(self.vocabulary_size, dtype=np.float32)
        length = min(len(histogram), self.vocabulary_size)
        hist[:length] = histogram[:length]

        # Term Frequency
        if self.use_log_tf:
            # Log TF: reduce impacto de palabras muy frecuentes
            tf = np.log1p(hist)  # log(1 + count)
        else:
            # Power normalization
            tf = np.sign(hist) * np.abs(hist) ** self.power_norm_alpha

        # TF-IDF
        tfidf = tf * self.idf_vector

        # L2 normalization
        norm = np.linalg.norm(tfidf)
        if norm > 1e-7:
            tfidf = tfidf / norm

        return tfidf.astype(np.float32)

    def compute_all_tfidf(
        self, histograms: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Calcula TF-IDF para todos los histogramas.

        Args:
            histograms: {nombre: histogram_array}

        Returns:
            {nombre: tfidf_vector}
        """
        # Calcular IDF global
        self.compute_idf(histograms)

        # Aplicar a cada histograma
        return {name: self.compute_tfidf(hist) for name, hist in histograms.items()}

    def save_idf(self, path: str):
        """Guarda vector IDF en disco."""
        if self.idf_vector is None:
            raise ValueError("IDF no calculado.")
        np.save(path, self.idf_vector)

    def load_idf(self, path: str) -> "TFIDFWeighter":
        """Carga vector IDF desde disco."""
        self.idf_vector = np.load(path)
        self.vocabulary_size = len(self.idf_vector)
        return self

    def get_stats(self) -> Dict:
        """Retorna estadísticas del IDF."""
        if self.idf_vector is None:
            return {"status": "IDF no calculado"}

        return {
            "vocabulary_size": self.vocabulary_size,
            "num_documents": self.num_documents,
            "idf_min": float(np.min(self.idf_vector)),
            "idf_max": float(np.max(self.idf_vector)),
            "idf_mean": float(np.mean(self.idf_vector)),
        }


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Calcula similitud de coseno entre dos vectores.

    Args:
        vec1, vec2: Vectores a comparar

    Returns:
        Similitud en rango [-1, 1]
    """
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 < 1e-7 or norm2 < 1e-7:
        return 0.0

    return float(np.dot(vec1, vec2) / (norm1 * norm2))
