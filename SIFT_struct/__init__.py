"""
SIFT_struct - Sistema Modular de Recuperación de Imágenes por Similitud

Pipeline CBIR (Content-Based Image Retrieval):
1. feature_extractor: Extracción SIFT/RootSIFT
2. visual_codebook: Diccionario visual (K-Means)
3. tfidf_weighting: Ponderación TF-IDF
4. knn_sequential: Búsqueda KNN con heap
5. knn_inverted: Búsqueda KNN con índice invertido
6. SIFTEngine: Motor que integra todo

Uso:
    from SIFT_struct import SIFTEngine, SIFTConfig

    engine = SIFTEngine(base_dir=".", data_dir="api/data/sift")
    engine.add_image(1, "foto.jpg", "/path/to/foto.jpg")
    results = engine.search("/path/to/query.jpg", k=10)
"""

from SIFT_struct.SIFTEngine import SIFTEngine, SIFTConfig
from SIFT_struct.feature_extractor import SIFTExtractor
from SIFT_struct.visual_codebook import VisualCodebook
from SIFT_struct.tfidf_weighting import TFIDFWeighter
from SIFT_struct.knn_sequential import KNNSequentialSearch
from SIFT_struct.knn_inverted import InvertedIndex

__all__ = [
    "SIFTEngine",
    "SIFTConfig",
    "SIFTExtractor",
    "VisualCodebook",
    "TFIDFWeighter",
    "KNNSequentialSearch",
    "InvertedIndex",
]
