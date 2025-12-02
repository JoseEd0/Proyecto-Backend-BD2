"""
knn_sequential.py - Búsqueda KNN Secuencial para Audio

Búsqueda exhaustiva usando heap para top-K eficiente.
Compara query contra todos los audios indexados.
"""

import numpy as np
import heapq
from typing import List, Tuple, Dict, Optional


class KNNSequentialSearch:
    """Búsqueda KNN secuencial con similitud coseno."""

    def __init__(self):
        self.vectors: Optional[np.ndarray] = None  # Matriz de vectores TF-IDF
        self.index_map: List[str] = []  # Mapeo índice -> nombre

    def build_index(self, tfidf_vectors: Dict[str, np.ndarray], index_map: List[str]):
        """
        Construye índice para búsqueda.

        Args:
            tfidf_vectors: {nombre: vector_tfidf}
            index_map: Lista ordenada de nombres
        """
        if not tfidf_vectors:
            return

        self.index_map = index_map

        # Construir matriz de vectores en orden del index_map
        vectors_list = []
        for name in index_map:
            if name in tfidf_vectors:
                vectors_list.append(tfidf_vectors[name])
            else:
                # Vector cero si no existe
                dim = next(iter(tfidf_vectors.values())).shape[0]
                vectors_list.append(np.zeros(dim))

        self.vectors = np.array(vectors_list)

    def search(
        self, query_vector: np.ndarray, k: int = 10
    ) -> List[Tuple[int, float, str]]:
        """
        Busca los k audios más similares.

        Args:
            query_vector: Vector TF-IDF de la query
            k: Número de resultados

        Returns:
            Lista de (posición, similitud, nombre)
        """
        if self.vectors is None or len(self.vectors) == 0:
            return []

        # Asegurar que query está normalizado
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector = query_vector / query_norm

        # Calcular similitud coseno con todos los vectores
        # Como están normalizados, similitud = dot product
        similarities = np.dot(self.vectors, query_vector)

        # Usar heap para top-K eficiente
        # heapq es min-heap, usamos negativos para obtener máximos
        heap = []

        for idx, sim in enumerate(similarities):
            if len(heap) < k:
                heapq.heappush(heap, (sim, idx))
            elif sim > heap[0][0]:
                heapq.heapreplace(heap, (sim, idx))

        # Extraer resultados ordenados de mayor a menor similitud
        results = []
        while heap:
            sim, idx = heapq.heappop(heap)
            name = self.index_map[idx] if idx < len(self.index_map) else ""
            results.append((idx, float(sim), name))

        # Invertir para tener mayor similitud primero
        results.reverse()

        return results

    def load_from_files(self, vectors_path: str, index_map: List[str]) -> bool:
        """Carga vectores desde archivo."""
        try:
            self.vectors = np.load(vectors_path)
            self.index_map = index_map
            return True
        except Exception:
            return False
