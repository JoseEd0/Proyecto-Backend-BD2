"""
KNN Sequential Search Module - Búsqueda por fuerza bruta con Heap

Implementación de KNN usando cola de prioridad (heapq) para
mantener eficientemente los K mejores resultados.

Complejidad: O(N * D + N * log(K))
- N: número de vectores en la base de datos
- D: dimensionalidad de los vectores
- K: número de resultados a retornar
"""

import numpy as np
import heapq
from typing import List, Tuple, Dict, Any, Optional


class KNNSequentialSearch:
    """
    Búsqueda KNN secuencial optimizada con cola de prioridad.

    Usa un min-heap para mantener los K elementos más similares
    de forma eficiente durante la búsqueda lineal.
    """

    def __init__(self, vectors: np.ndarray, metadata: Optional[Dict[int, Any]] = None):
        """
        Args:
            vectors: Matriz de vectores TF-IDF (N, D)
            metadata: Diccionario opcional {índice: información}
        """
        self.vectors = vectors.astype(np.float32)
        self.metadata = metadata or {}
        self.n_vectors, self.dim = vectors.shape

        # Pre-calcular normas para similitud de coseno
        self.norms = np.linalg.norm(vectors, axis=1)
        self.norms = np.maximum(self.norms, 1e-7)  # Evitar división por cero

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """
        Busca los K vectores más similares usando heap.

        Args:
            query: Vector de consulta (D,)
            k: Número de resultados

        Returns:
            Lista de (índice, similitud) ordenada descendentemente
        """
        # Ajustar dimensiones si es necesario
        if len(query) != self.dim:
            if len(query) < self.dim:
                query = np.pad(query, (0, self.dim - len(query)))
            else:
                query = query[: self.dim]

        query = query.astype(np.float32)
        query_norm = np.linalg.norm(query)

        if query_norm < 1e-7:
            return []

        # Calcular similitudes de coseno vectorizadas
        # similarities = (vectors @ query) / (norms * query_norm)
        dot_products = self.vectors @ query
        similarities = dot_products / (self.norms * query_norm)

        # Usar heap para encontrar top-K
        # heapq es min-heap, así que usamos -similarity
        top_k: List[Tuple[float, int]] = []

        for idx, sim in enumerate(similarities):
            if len(top_k) < k:
                heapq.heappush(top_k, (sim, idx))
            elif sim > top_k[0][0]:
                heapq.heapreplace(top_k, (sim, idx))

        # Extraer y ordenar resultados (mayor similitud primero)
        results = []
        while top_k:
            sim, idx = heapq.heappop(top_k)
            results.append((idx, float(sim)))

        results.reverse()
        return results

    def search_with_metadata(
        self, query: np.ndarray, k: int = 10
    ) -> List[Tuple[int, float, Any]]:
        """
        Búsqueda KNN incluyendo metadata.

        Args:
            query: Vector de consulta
            k: Número de resultados

        Returns:
            Lista de (índice, similitud, metadata)
        """
        results = self.search(query, k)
        return [(idx, sim, self.metadata.get(idx, {})) for idx, sim in results]

    def range_search(
        self, query: np.ndarray, threshold: float = 0.5, max_results: int = 100
    ) -> List[Tuple[int, float]]:
        """
        Búsqueda por rango de similitud.

        Args:
            query: Vector de consulta
            threshold: Similitud mínima
            max_results: Máximo de resultados

        Returns:
            Lista de (índice, similitud) con sim >= threshold
        """
        if len(query) != self.dim:
            if len(query) < self.dim:
                query = np.pad(query, (0, self.dim - len(query)))
            else:
                query = query[: self.dim]

        query = query.astype(np.float32)
        query_norm = np.linalg.norm(query)

        if query_norm < 1e-7:
            return []

        # Calcular similitudes
        dot_products = self.vectors @ query
        similarities = dot_products / (self.norms * query_norm)

        # Filtrar por threshold
        results = [
            (idx, float(sim))
            for idx, sim in enumerate(similarities)
            if sim >= threshold
        ]

        # Ordenar y limitar
        results.sort(key=lambda x: -x[1])
        return results[:max_results]

    def __len__(self) -> int:
        return self.n_vectors

    def __repr__(self) -> str:
        return f"KNNSequentialSearch(vectors={self.n_vectors}, dim={self.dim})"
