"""
knn_inverted.py - Búsqueda KNN con Índice Invertido para Audio

Estructura de índice invertido:
    palabra_audio_i -> [(audio_id_1, peso), (audio_id_2, peso), ...]

Algoritmo TAAT (Term-At-A-Time):
1. Para cada palabra de audio en la query con peso > 0
2. Recorrer posting list de esa palabra
3. Acumular scores: score[audio] += query_weight * doc_weight
4. Ordenar por score y retornar top-K

Ventaja: Solo procesa audios que comparten palabras de audio con la query.
"""

import numpy as np
import heapq
from typing import Dict, List, Tuple, Optional
from collections import defaultdict


class InvertedIndex:
    """Índice invertido para búsqueda eficiente de audio."""

    def __init__(self):
        # palabra_id -> [(doc_idx, weight), ...]
        self.posting_lists: Dict[int, List[Tuple[int, float]]] = {}
        self.index_map: List[str] = []  # doc_idx -> nombre
        self.n_documents = 0

    def build_index(self, tfidf_vectors: Dict[str, np.ndarray], index_map: List[str]):
        """
        Construye índice invertido desde vectores TF-IDF.

        Args:
            tfidf_vectors: {nombre: vector_tfidf}
            index_map: Lista ordenada de nombres
        """
        self.posting_lists = defaultdict(list)
        self.index_map = index_map
        self.n_documents = len(index_map)

        for doc_idx, name in enumerate(index_map):
            if name not in tfidf_vectors:
                continue

            vector = tfidf_vectors[name]

            # Agregar a posting lists para cada palabra con peso > 0
            for word_idx, weight in enumerate(vector):
                if weight > 1e-6:  # Umbral mínimo
                    self.posting_lists[word_idx].append((doc_idx, float(weight)))

        # Convertir defaultdict a dict normal
        self.posting_lists = dict(self.posting_lists)

        print(f"[InvertedIndex] Construido: {len(self.posting_lists)} palabras activas")

    def search(
        self, query_vector: np.ndarray, k: int = 10
    ) -> List[Tuple[int, float, str]]:
        """
        Busca los k audios más similares usando TAAT.

        Args:
            query_vector: Vector TF-IDF de la query
            k: Número de resultados

        Returns:
            Lista de (posición, similitud, nombre)
        """
        if not self.posting_lists:
            return []

        # Normalizar query
        query_norm = np.linalg.norm(query_vector)
        if query_norm > 0:
            query_vector = query_vector / query_norm

        # Acumular scores
        scores = defaultdict(float)

        # TAAT: para cada palabra en la query
        for word_idx, query_weight in enumerate(query_vector):
            if query_weight < 1e-6:
                continue

            if word_idx not in self.posting_lists:
                continue

            # Recorrer posting list
            for doc_idx, doc_weight in self.posting_lists[word_idx]:
                scores[doc_idx] += query_weight * doc_weight

        if not scores:
            return []

        # Top-K con heap
        heap = []
        for doc_idx, score in scores.items():
            if len(heap) < k:
                heapq.heappush(heap, (score, doc_idx))
            elif score > heap[0][0]:
                heapq.heapreplace(heap, (score, doc_idx))

        # Extraer resultados
        results = []
        while heap:
            score, doc_idx = heapq.heappop(heap)
            name = self.index_map[doc_idx] if doc_idx < len(self.index_map) else ""
            results.append((doc_idx, float(score), name))

        # Invertir para mayor score primero
        results.reverse()

        return results

    def get_stats(self) -> Dict:
        """Retorna estadísticas del índice."""
        if not self.posting_lists:
            return {"n_documents": 0, "n_terms": 0, "avg_posting_length": 0}

        posting_lengths = [len(pl) for pl in self.posting_lists.values()]

        return {
            "n_documents": self.n_documents,
            "n_terms": len(self.posting_lists),
            "avg_posting_length": np.mean(posting_lengths) if posting_lengths else 0,
            "max_posting_length": max(posting_lengths) if posting_lengths else 0,
        }
