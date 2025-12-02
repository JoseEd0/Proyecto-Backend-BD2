"""
feature_extractor.py - Extracción de Características de Audio con MFCC

MFCC (Mel-Frequency Cepstral Coefficients):
- Representación compacta del espectro de audio
- Simula la percepción auditiva humana (escala Mel)
- Estándar en reconocimiento de voz y audio

Pipeline:
1. Cargar audio → mono, sample rate fijo
2. Pre-énfasis → realza frecuencias altas
3. Framing → divide en ventanas de 25ms
4. FFT → espectro de frecuencias
5. Mel filterbank → escala perceptual
6. Log → compresión dinámica
7. DCT → coeficientes cepstrales (MFCCs)

Cada frame genera un vector de N_MFCC coeficientes.
Un audio de 3 segundos genera ~100-150 frames.
"""

import numpy as np
import os
from typing import Tuple, Optional, List, Dict


class MFCCExtractor:
    """Extractor de características MFCC para audio."""

    def __init__(
        self,
        sample_rate: int = 22050,
        n_mfcc: int = 13,
        n_fft: int = 2048,
        hop_length: int = 512,
        n_mels: int = 128,
        duration: Optional[float] = None,  # None = audio completo
        include_delta: bool = True,  # Incluir derivadas
    ):
        """
        Args:
            sample_rate: Frecuencia de muestreo objetivo
            n_mfcc: Número de coeficientes MFCC (típico: 13-20)
            n_fft: Tamaño de ventana FFT
            hop_length: Salto entre frames
            n_mels: Número de filtros Mel
            duration: Duración máxima en segundos (None = completo)
            include_delta: Incluir delta y delta-delta MFCCs
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.duration = duration
        self.include_delta = include_delta

        # Dimensión del descriptor por frame
        # Si include_delta: MFCC + delta + delta-delta = 3 * n_mfcc
        self.descriptor_dim = n_mfcc * 3 if include_delta else n_mfcc

    def extract(self, audio_path: str) -> Tuple[Optional[np.ndarray], dict]:
        """
        Extrae características MFCC de un archivo de audio.

        Args:
            audio_path: Ruta al archivo de audio

        Returns:
            Tuple de (descriptors, metadata)
            - descriptors: np.ndarray de shape (n_frames, descriptor_dim)
            - metadata: dict con información del audio
        """
        try:
            import librosa
        except ImportError:
            raise ImportError("librosa es requerido. Instalar con: pip install librosa")

        if not os.path.exists(audio_path):
            return None, {"error": f"Archivo no encontrado: {audio_path}"}

        try:
            # Cargar audio
            y, sr = librosa.load(
                audio_path,
                sr=self.sample_rate,
                mono=True,
                duration=self.duration,
            )

            if len(y) == 0:
                return None, {"error": "Audio vacío"}

            # Calcular duración real
            duration = len(y) / sr

            # Extraer MFCCs
            mfccs = librosa.feature.mfcc(
                y=y,
                sr=sr,
                n_mfcc=self.n_mfcc,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
                n_mels=self.n_mels,
            )

            # mfccs shape: (n_mfcc, n_frames)
            # Transponer a (n_frames, n_mfcc)
            mfccs = mfccs.T

            if self.include_delta:
                # Calcular delta (velocidad) y delta-delta (aceleración)
                delta = librosa.feature.delta(mfccs.T).T
                delta2 = librosa.feature.delta(mfccs.T, order=2).T

                # Concatenar: [MFCC, delta, delta-delta]
                descriptors = np.hstack([mfccs, delta, delta2])
            else:
                descriptors = mfccs

            # Normalizar por frame (z-score)
            descriptors = self._normalize(descriptors)

            metadata = {
                "sample_rate": sr,
                "duration": duration,
                "n_frames": descriptors.shape[0],
                "descriptor_dim": descriptors.shape[1],
                "original_path": audio_path,
            }

            return descriptors.astype(np.float32), metadata

        except Exception as e:
            return None, {"error": str(e)}

    def _normalize(self, features: np.ndarray) -> np.ndarray:
        """Normaliza features con z-score."""
        mean = np.mean(features, axis=0, keepdims=True)
        std = np.std(features, axis=0, keepdims=True) + 1e-8
        return (features - mean) / std

    def extract_mean_std(self, audio_path: str) -> Tuple[Optional[np.ndarray], dict]:
        """
        Extrae vector resumen (media + std) de MFCCs.

        Útil para comparación rápida sin clustering.
        Genera un solo vector por audio.

        Returns:
            Tuple de (vector, metadata)
            - vector: np.ndarray de shape (2 * descriptor_dim,)
        """
        descriptors, metadata = self.extract(audio_path)

        if descriptors is None:
            return None, metadata

        # Calcular estadísticas globales
        mean = np.mean(descriptors, axis=0)
        std = np.std(descriptors, axis=0)

        # Concatenar media y desviación estándar
        summary_vector = np.concatenate([mean, std])

        metadata["vector_dim"] = len(summary_vector)
        return summary_vector.astype(np.float32), metadata

    def get_spectrogram(
        self, audio_path: str
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Genera espectrograma Mel para visualización.

        Returns:
            Tuple de (spectrogram, times)
        """
        try:
            import librosa
        except ImportError:
            return None, None

        try:
            y, sr = librosa.load(
                audio_path, sr=self.sample_rate, mono=True, duration=self.duration
            )

            mel_spec = librosa.feature.melspectrogram(
                y=y,
                sr=sr,
                n_mels=self.n_mels,
                n_fft=self.n_fft,
                hop_length=self.hop_length,
            )

            # Convertir a dB
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            times = librosa.times_like(mel_spec_db, sr=sr, hop_length=self.hop_length)

            return mel_spec_db, times

        except Exception:
            return None, None


# Alias para consistencia con SIFT
AudioFeatureExtractor = MFCCExtractor
