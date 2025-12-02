"""
KNN Inverted Index Module - Búsqueda con Índice Invertido

Implementación de búsqueda eficiente usando índice invertido,
análogo a motores de búsqueda textual.

Ventajas sobre búsqueda secuencial:
- Solo considera documentos que comparten al menos una visual word
- Eficiente para queries sparse (pocas visual words activas)
- Escala mejor con colecciones grandes

Complejidad: O(L * P) donde:
- L: número de términos en la query
- P: longitud promedio de posting lists
"""

import numpy as np
import heapq
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict


class InvertedIndex:
    """
    Índice Invertido para Visual Words.

    Estructura: {visual_word_id: [(doc_id, weight), ...]}

    Permite búsqueda eficiente solo en documentos relevantes.
    """

    def __init__(self):
        self.index: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
        self.doc_norms: Dict[int, float] = {}
        self.doc_metadata: Dict[int, Any] = {}
        self.vocabulary_size: int = 0
        self.num_documents: int = 0

    def build(
        self,
        tfidf_vectors: Dict[int, np.ndarray],
        metadata: Optional[Dict[int, Any]] = None,
    ) -> "InvertedIndex":
        """
        Construye índice invertido desde vectores TF-IDF.

        Args:
            tfidf_vectors: {doc_id: tfidf_vector}
            metadata: {doc_id: info} opcional

        Returns:
            self
        """
        self.index.clear()
        self.doc_norms.clear()

        if not tfidf_vectors:
            return self

        # Determinar dimensiones
        sample = next(iter(tfidf_vectors.values()))
        self.vocabulary_size = len(sample)
        self.num_documents = len(tfidf_vectors)
        self.doc_metadata = metadata or {}

        print(f"[INVERTED INDEX] Construyendo:")
        print(f"  - Documentos: {self.num_documents}")
        print(f"  - Vocabulario: {self.vocabulary_size}")

        # Construir posting lists
        for doc_id, vector in tfidf_vectors.items():
            # Guardar norma del documento
            self.doc_norms[doc_id] = float(np.linalg.norm(vector))

            # Agregar a posting lists (solo términos no-cero)
            for word_id, weight in enumerate(vector):
                if weight > 1e-7:
                    self.index[word_id].append((doc_id, float(weight)))

        # Ordenar posting lists por peso (optimización para early termination)
        for word_id in self.index:
            self.index[word_id].sort(key=lambda x: -x[1])

        active_terms = len([k for k in self.index if len(self.index[k]) > 0])
        print(f"[INVERTED INDEX] ✓ Construido: {active_terms} términos activos")

        return self

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[int, float]]:
        """
        Búsqueda KNN usando índice invertido.

        Algoritmo Term-at-a-Time (TAAT):
        1. Para cada término en la query
        2. Acumular scores de documentos en posting list
        3. Calcular similitud final
        4. Retornar top-K

        Args:
            query: Vector TF-IDF de la query
            k: Número de resultados

        Returns:
            Lista de (doc_id, similitud) ordenada descendentemente
        """
        if not self.index:
            return []

        # Ajustar dimensiones
        if len(query) < self.vocabulary_size:
            query = np.pad(query, (0, self.vocabulary_size - len(query)))
        elif len(query) > self.vocabulary_size:
            query = query[: self.vocabulary_size]

        query_norm = np.linalg.norm(query)
        if query_norm < 1e-7:
            return []

        # Acumular scores (dot product parcial)
        scores: Dict[int, float] = defaultdict(float)

        for word_id, query_weight in enumerate(query):
            if query_weight < 1e-7:
                continue

            if word_id not in self.index:
                continue

            for doc_id, doc_weight in self.index[word_id]:
                scores[doc_id] += query_weight * doc_weight

        if not scores:
            return []

        # Calcular similitud de coseno final y usar heap para top-K
        top_k: List[Tuple[float, int]] = []

        for doc_id, dot_product in scores.items():
            doc_norm = self.doc_norms.get(doc_id, 1.0)
            if doc_norm < 1e-7:
                continue

            similarity = dot_product / (query_norm * doc_norm)

            if len(top_k) < k:
                heapq.heappush(top_k, (similarity, doc_id))
            elif similarity > top_k[0][0]:
                heapq.heapreplace(top_k, (similarity, doc_id))

        # Extraer resultados ordenados
        results = []
        while top_k:
            sim, doc_id = heapq.heappop(top_k)
            results.append((doc_id, float(sim)))

        results.reverse()
        return results

    def search_with_metadata(
        self, query: np.ndarray, k: int = 10
    ) -> List[Tuple[int, float, Any]]:
        """
        Búsqueda incluyendo metadata.

        Args:
            query: Vector TF-IDF
            k: Número de resultados

        Returns:
            Lista de (doc_id, similitud, metadata)
        """
        results = self.search(query, k)
        return [
            (doc_id, sim, self.doc_metadata.get(doc_id, {})) for doc_id, sim in results
        ]

    def get_posting_list(self, word_id: int) -> List[Tuple[int, float]]:
        """Obtiene posting list de una visual word."""
        return self.index.get(word_id, [])

    def get_stats(self) -> Dict:
        """Retorna estadísticas del índice."""
        if not self.index:
            return {"status": "empty"}

        posting_lengths = [len(pl) for pl in self.index.values()]

        return {
            "num_documents": self.num_documents,
            "vocabulary_size": self.vocabulary_size,
            "active_terms": len([k for k in self.index if len(self.index[k]) > 0]),
            "avg_posting_length": (
                float(np.mean(posting_lengths)) if posting_lengths else 0
            ),
            "max_posting_length": max(posting_lengths) if posting_lengths else 0,
            "total_postings": sum(posting_lengths),
        }

    def __repr__(self) -> str:
        return f"InvertedIndex(docs={self.num_documents}, vocab={self.vocabulary_size})"


class KNNInvertedSearch:
    """Wrapper de alto nivel para búsqueda con índice invertido."""

    def __init__(self):
        self.index = InvertedIndex()
        self.metadata: Dict[int, Any] = {}

    def build(
        self,
        tfidf_vectors: Dict[int, np.ndarray],
        metadata: Optional[Dict[int, Any]] = None,
    ) -> "KNNInvertedSearch":
        """Construye el índice."""
        self.index.build(tfidf_vectors, metadata)
        self.metadata = metadata or {}
        return self

    def search(self, query: np.ndarray, k: int = 10) -> List[Tuple[int, float, Any]]:
        """Búsqueda KNN con metadata."""
        return self.index.search_with_metadata(query, k)

    def get_stats(self) -> Dict:
        """Estadísticas del índice."""
        return self.index.get_stats()
