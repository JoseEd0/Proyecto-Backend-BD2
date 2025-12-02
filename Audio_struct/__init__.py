"""
Audio_struct - Sistema Modular de Búsqueda de Audio por Similitud

Módulos:
- feature_extractor: Extracción de MFCC (Mel-Frequency Cepstral Coefficients)
- audio_codebook: Vocabulario de audio (K-Means clustering)
- tfidf_weighting: Ponderación TF-IDF para vectores de audio
- knn_sequential: Búsqueda KNN secuencial
- knn_inverted: Búsqueda KNN con índice invertido
- AudioEngine: Motor principal que integra todos los módulos
"""

from .AudioEngine import AudioEngine, AudioConfig

__all__ = ["AudioEngine", "AudioConfig"]
