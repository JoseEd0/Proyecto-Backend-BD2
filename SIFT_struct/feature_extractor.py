"""
Feature Extractor Module - Extracción de características SIFT

Implementación robusta siguiendo mejores prácticas:
- Normalización de imagen antes de extracción
- RootSIFT para mejor discriminación
- Manejo de imágenes de cualquier tamaño

Referencias:
- Lowe (2004) "Distinctive Image Features from Scale-Invariant Keypoints"
- Arandjelović & Zisserman (2012) "Three things everyone should know to improve BoVW"
"""

import cv2
import numpy as np
import os
from typing import Optional, Tuple


class SIFTExtractor:
    """
    Extractor de características SIFT con preprocesamiento.

    Características:
    - Resize automático manteniendo aspect ratio
    - RootSIFT opcional (mejor discriminación)
    - Normalización de descriptores
    """

    def __init__(
        self,
        target_size: int = 512,
        use_root_sift: bool = True,
        n_features: int = 0,  # 0 = sin límite
        contrast_threshold: float = 0.02,  # Más bajo = más keypoints en imágenes simples
        edge_threshold: float = 15,  # Más alto = menos filtrado de bordes
    ):
        """
        Args:
            target_size: Tamaño máximo de la imagen (el lado mayor)
            use_root_sift: Aplicar transformación RootSIFT
            n_features: Máximo de keypoints (0 = ilimitado)
            contrast_threshold: Umbral de contraste para SIFT (menor = más keypoints)
            edge_threshold: Umbral de bordes para SIFT (mayor = menos filtrado)
        """
        self.target_size = target_size
        self.use_root_sift = use_root_sift

        # Crear detector SIFT con parámetros ajustados para imágenes variadas
        self.sift = cv2.SIFT_create(
            nfeatures=n_features,
            contrastThreshold=contrast_threshold,
            edgeThreshold=edge_threshold,
        )

    def extract(self, image_path: str) -> Optional[np.ndarray]:
        """
        Extrae descriptores SIFT de una imagen.

        Args:
            image_path: Ruta a la imagen

        Returns:
            Array de descriptores (N, 128) o None si falla
        """
        # Leer imagen
        image = cv2.imread(image_path)
        if image is None:
            print(f"[SIFT] Error leyendo imagen: {image_path}")
            return None

        # Convertir a escala de grises
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Detectar keypoints y extraer descriptores
        keypoints, descriptors = self.sift.detectAndCompute(gray, None)

        if descriptors is None or len(descriptors) == 0:
            print(f"[SIFT] Sin descriptores: {image_path}")
            return None

        # Aplicar RootSIFT si está habilitado
        if self.use_root_sift:
            descriptors = self._apply_root_sift(descriptors)

        return descriptors.astype(np.float32)

    def extract_from_array(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extrae descriptores de un array numpy.

        Args:
            image: Imagen como numpy array (BGR o grayscale)

        Returns:
            Descriptores o None
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        keypoints, descriptors = self.sift.detectAndCompute(gray, None)

        if descriptors is None or len(descriptors) == 0:
            return None

        if self.use_root_sift:
            descriptors = self._apply_root_sift(descriptors)

        return descriptors.astype(np.float32)

    def _apply_root_sift(self, descriptors: np.ndarray) -> np.ndarray:
        """
        Aplica transformación RootSIFT.

        RootSIFT: L1-normalización + sqrt
        Mejora significativamente la discriminación según literatura.

        Args:
            descriptors: Descriptores SIFT originales

        Returns:
            Descriptores transformados
        """
        # L1 normalize
        descriptors = descriptors.astype(np.float32)
        l1_norms = np.linalg.norm(descriptors, ord=1, axis=1, keepdims=True)
        l1_norms = np.maximum(l1_norms, 1e-7)  # Evitar división por cero
        descriptors = descriptors / l1_norms

        # Square root
        descriptors = np.sqrt(descriptors)

        return descriptors

    def resize_image(self, input_path: str, output_path: str) -> bool:
        """
        Redimensiona imagen manteniendo aspect ratio.

        Args:
            input_path: Ruta imagen original
            output_path: Ruta imagen redimensionada

        Returns:
            True si exitoso
        """
        image = cv2.imread(input_path)
        if image is None:
            return False

        h, w = image.shape[:2]

        # Solo redimensionar si es más grande que target
        if max(h, w) > self.target_size:
            if h > w:
                new_h = self.target_size
                new_w = int(w * (self.target_size / h))
            else:
                new_w = self.target_size
                new_h = int(h * (self.target_size / w))

            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        return cv2.imwrite(output_path, image)

    def process_and_extract(
        self, image_path: str, output_dir: str, name: str, min_descriptors: int = 10
    ) -> Tuple[Optional[np.ndarray], Optional[str]]:
        """
        Procesa imagen (resize) y extrae descriptores.

        Args:
            image_path: Ruta imagen original
            output_dir: Directorio para imagen procesada
            name: Nombre base para la imagen
            min_descriptors: Mínimo de descriptores requeridos

        Returns:
            (descriptores, ruta_procesada) o (None, None) si falla
        """
        # Crear ruta de salida
        ext = os.path.splitext(image_path)[1] or ".jpg"
        output_path = os.path.join(output_dir, f"{name}_processed{ext}")

        # Redimensionar
        if not self.resize_image(image_path, output_path):
            # Intentar usar original
            output_path = image_path

        # Extraer descriptores
        descriptors = self.extract(output_path)

        if descriptors is None or len(descriptors) < min_descriptors:
            print(
                f"[SIFT] Pocos descriptores ({len(descriptors) if descriptors is not None else 0} < {min_descriptors})"
            )
            return None, None

        return descriptors, output_path

    def __repr__(self) -> str:
        root = "RootSIFT" if self.use_root_sift else "SIFT"
        return f"SIFTExtractor({root}, target_size={self.target_size})"
