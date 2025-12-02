# 🖼️ Búsqueda de Imágenes con SIFT - Guía de Uso

## 📋 Descripción

Se ha integrado completamente el sistema de **búsqueda de imágenes por similitud usando SIFT** (Scale-Invariant Feature Transform) al API y frontend del gestor de base de datos.

### Características Principales

- ✅ **Indexación automática con SIFT**: Extrae descriptores visuales de cada imagen
- ✅ **Búsqueda por similitud**: Encuentra las K imágenes más similares usando TF-IDF + Cosine Similarity
- ✅ **Interfaz moderna y responsive**: Drag & drop, galería visual, resultados en tiempo real
- ✅ **API REST completa**: Endpoints para crear, subir, buscar y listar imágenes
- ✅ **Almacenamiento eficiente**: Usa Heap Files para datos e índice SIFT

---

## 🚀 Cómo Usar

### 1. Iniciar el Servidor

```bash
cd api
python main.py
```

O usando el script de inicio:

```bash
cd api
python start.py
```

El servidor estará disponible en:
- **Frontend Principal**: http://localhost:8000/
- **Búsqueda de Imágenes**: http://localhost:8000/static/images.html
- **API Docs**: http://localhost:8000/docs

### 2. Acceder a la Interfaz de Imágenes

Desde el **SQL Console** (página principal), haz click en el botón:
```
🖼️ Búsqueda de Imágenes
```

O navega directamente a: http://localhost:8000/static/images.html

### 3. Flujo de Trabajo

#### Paso 1: Inicializar el Sistema
1. Haz click en **"⚡ Crear Tabla de Imágenes"**
2. Esto crea:
   - Tabla principal (Heap) para almacenar metadatos de imágenes
   - Índice SIFT para búsquedas rápidas
   - Carpeta para imágenes subidas

#### Paso 2: Cargar Imágenes
1. Arrastra una imagen o haz click para seleccionar
2. Ingresa un **ID único** (número entero)
3. Ingresa un **nombre** (opcional)
4. Click en **"⬆️ Subir e Indexar Imagen"**

El sistema automáticamente:
- Redimensiona la imagen a 256x256
- Extrae descriptores SIFT
- Calcula histograma BoVW
- Genera vector TF-IDF
- Indexa en el sistema

#### Paso 3: Ver Galería
- Las imágenes aparecen automáticamente en la galería
- Haz click en cualquier imagen para seleccionarla
- La imagen seleccionada se marca con borde verde

#### Paso 4: Buscar Similares
1. Selecciona una imagen de la galería (o ingresa su ID)
2. Establece el número de resultados (K) - por defecto 10
3. Click en **"🔎 Buscar Imágenes Similares"**

Verás:
- La imagen de consulta
- Las K imágenes más similares ordenadas por similitud
- Tiempo de búsqueda
- Ranking de resultados

---

## 🔌 API Endpoints

### Crear Tabla de Imágenes
```http
POST /api/sift/create-table?table_name=ImagenesMultimedia
```

**Response:**
```json
{
  "success": true,
  "message": "Tabla 'ImagenesMultimedia' creada exitosamente",
  "sift_config": {
    "image_size": 256,
    "clusters": 100
  }
}
```

### Subir Imagen
```http
POST /api/sift/upload-image
Content-Type: multipart/form-data

file: [archivo de imagen]
image_id: 1
image_name: "torre_eiffel"
```

**Response:**
```json
{
  "success": true,
  "message": "Imagen subida e indexada exitosamente",
  "image_id": 1,
  "position": 0
}
```

### Buscar Imágenes Similares
```http
POST /api/sift/search-similar?image_id=1&k=10
```

**Response:**
```json
{
  "success": true,
  "query_image": {
    "id": 1,
    "nombre": "torre_eiffel",
    "ruta": "api/data/sift/uploaded_images/torre_eiffel_1.jpg"
  },
  "similar_images": [
    {
      "id": 5,
      "nombre": "torre_pisa",
      "ruta": "api/data/sift/uploaded_images/torre_pisa_5.jpg",
      "position": 4
    },
    ...
  ],
  "count": 10
}
```

### Listar Todas las Imágenes
```http
GET /api/sift/images
```

**Response:**
```json
{
  "success": true,
  "images": [
    {
      "id": 1,
      "nombre": "torre_eiffel",
      "ruta": "...",
      "position": 0
    }
  ],
  "count": 1
}
```

### Obtener Imagen por ID
```http
GET /api/sift/image/{image_id}
```

### Obtener Archivo de Imagen
```http
GET /api/sift/image-file/{image_id}
```
Retorna el archivo de imagen directamente (JPEG)

---

## 🔧 Configuración Técnica

### Parámetros SIFT
- **Tamaño de imagen**: 256x256 pixels
- **Número de clusters (BoVW)**: 100
- **Algoritmo**: SIFT (OpenCV)
- **Similitud**: Cosine Similarity sobre vectores TF-IDF

### Estructura de Archivos
```
api/
├── data/
│   └── sift/
│       ├── uploaded_images/          # Imágenes subidas
│       ├── ImagenesMultimedia.heap   # Heap principal (id, nombre, ruta)
│       └── ImagenesMultimedia_index.heap  # Índice SIFT (pos, nombre, tfidf)
├── static/
│   ├── index.html                   # SQL Console
│   └── images.html                  # Interfaz de Imágenes
└── main.py                          # API con endpoints SIFT

SIFT_struct/
├── InvertVisualFile.py              # Gestor principal
├── SIFT.py                          # Extracción de descriptores
├── BoVW.py                          # Bag of Visual Words
├── KNN.py                           # TF-IDF y similitud
└── descriptors/
    ├── all_descriptors.npz          # Descriptores SIFT
    ├── visual_dictionary.pkl        # Diccionario visual
    ├── all_histograms.npz           # Histogramas BoVW
    └── all_tfidf.npz                # Vectores TF-IDF
```

---

## 📊 Estadísticas y Métricas

La interfaz muestra en tiempo real:
- **Imágenes Indexadas**: Total de imágenes en el sistema
- **Último Tiempo de Búsqueda**: Tiempo de la última consulta KNN
- **Tamaño de Imagen**: Resolución normalizada (256x256)
- **Clusters SIFT**: Número de palabras visuales (100)

---

## 🎨 Características de la Interfaz

### Galería de Imágenes
- Grid responsive que se adapta al tamaño de pantalla
- Hover effects con animaciones suaves
- Selección visual con borde verde
- Auto-fill del ID de búsqueda al seleccionar

### Drag & Drop
- Arrastra imágenes directamente desde tu explorador
- Validación de tipo y tamaño de archivo
- Feedback visual durante el drag

### Resultados de Búsqueda
- Muestra la imagen consultada destacada
- Grid de resultados ordenados por similitud
- Ranking numerado (#1, #2, #3...)
- Tiempo de búsqueda en segundos

---

## 🧪 Testing

### Test Manual
1. Sube 5-10 imágenes diferentes
2. Selecciona una imagen
3. Busca similares con K=5
4. Verifica que los resultados sean coherentes

### Test con Imágenes de Ejemplo
Las imágenes del proyecto Multi están en:
```
Multi/SIFT_struct/test_images/
```

Puedes copiarlas a tu carpeta y subirlas para testing.

---

## 💡 Tips y Mejores Prácticas

1. **IDs Únicos**: Asegúrate de usar IDs únicos para cada imagen
2. **Nombres Descriptivos**: Usa nombres que describan el contenido
3. **Imágenes Claras**: Mejores resultados con imágenes nítidas
4. **K Apropiado**: Para datasets pequeños, usa K < total_images
5. **Tipos de Archivo**: JPG, PNG, BMP funcionan mejor

---

## 🐛 Troubleshooting

### Error: "No hay tabla de imágenes creada"
**Solución**: Haz click en "Crear Tabla de Imágenes" primero

### Error: "ID duplicado"
**Solución**: Usa un ID diferente para cada imagen

### Error: "No se pudieron extraer descriptores"
**Solución**: La imagen puede ser muy simple o uniforme. Usa imágenes con más detalles

### Imágenes no se cargan en la galería
**Solución**: Verifica que el servidor esté corriendo y revisa la consola del navegador

---

## 📚 Referencias Técnicas

- **SIFT**: Lowe, D.G. (2004). "Distinctive Image Features from Scale-Invariant Keypoints"
- **Bag of Visual Words**: Csurka et al. (2004)
- **TF-IDF**: Salton & McGill (1983)
- **Cosine Similarity**: Para medir similitud entre vectores

---

## ✅ Checklist de Integración Completada

- [x] Endpoints API SIFT implementados
- [x] Gestor de imágenes con MultimediaImageRetrieval
- [x] Interfaz HTML/CSS/JS completa
- [x] Drag & drop funcional
- [x] Galería de imágenes responsive
- [x] Búsqueda KNN con visualización
- [x] Integración con sistema existente
- [x] Manejo de errores robusto
- [x] Documentación completa

---

## 🎉 ¡Listo para Usar!

El sistema de búsqueda de imágenes está completamente integrado y funcional. Disfruta explorando la similitud visual con SIFT!
