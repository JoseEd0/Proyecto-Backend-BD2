# BD2 Frontend - React + TypeScript

Frontend moderno para el gestor de base de datos multi-estructura.

## 🚀 Características

- **SQL Console**: Ejecuta consultas SQL en múltiples estructuras (Sequential, B+Tree, ISAM, Hash)
- **SIFT Manager**: Indexa y busca imágenes usando SIFT + BoVW + TF-IDF
- **BoW Manager**: Indexa y busca documentos de texto (en desarrollo)
- **Tables View**: Explora el contenido de todas las tablas

## 📦 Instalación

```bash
# Desde el directorio frontend
npm install
```

## 🛠️ Desarrollo

```bash
# Modo desarrollo con hot reload
npm run dev
```

El frontend estará disponible en `http://localhost:5173` y se conectará automáticamente al backend en `http://localhost:8000`.

## 🏗️ Build para producción

```bash
# Construir para producción
npm run build
```

Los archivos compilados se generarán en `../api/static/dist` y podrán ser servidos directamente por FastAPI.

## 🎨 Stack Tecnológico

- **React 18**: Biblioteca UI moderna
- **TypeScript**: Type safety y mejor DX
- **Vite**: Build tool ultrarrápido
- **React Router**: Navegación SPA
- **Lucide React**: Iconos modernos y ligeros

## 📁 Estructura

```
frontend/
├── src/
│   ├── components/      # Componentes reutilizables
│   │   ├── Layout.tsx   # Layout principal
│   │   └── Sidebar.tsx  # Navegación lateral
│   ├── pages/           # Páginas de la aplicación
│   │   ├── SQLConsole.tsx
│   │   ├── SIFTManager.tsx
│   │   ├── BoWManager.tsx
│   │   └── TablesView.tsx
│   ├── App.tsx          # Configuración de rutas
│   ├── main.tsx         # Punto de entrada
│   └── index.css        # Estilos globales
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 🔌 Conexión con el Backend

El frontend se comunica con el backend FastAPI a través de las siguientes APIs:

### SQL
- `POST /api/execute` - Ejecutar consulta SQL
- `GET /api/tables` - Listar tablas
- `GET /api/history` - Historial de consultas

### SIFT
- `POST /api/sift/upload-image` - Subir imagen
- `POST /api/sift/search-similar` - Buscar similares
- `GET /api/sift/images` - Listar imágenes
- `GET /api/sift/image-file/{id}` - Obtener archivo de imagen

### Tables
- `GET /api/table-data/{table_name}` - Obtener datos de tabla

## 🎨 Temas y Estilos

El frontend usa un tema oscuro profesional tipo VS Code con:
- Colores personalizados via CSS variables
- Animaciones sutiles
- Diseño responsive
- Scrollbars personalizados

## 🚀 Despliegue

Para desplegar en producción:

1. Build del frontend:
   ```bash
   npm run build
   ```

2. Los archivos en `../api/static/dist` son servidos automáticamente por FastAPI

3. Accede a través del servidor FastAPI en `http://localhost:8000`
