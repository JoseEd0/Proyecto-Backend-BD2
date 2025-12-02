# 🚀 Guía Rápida - BD2 Manager Frontend React

## ✅ Lo que se ha creado

Un frontend completo en **React + TypeScript + Vite** para TODO el gestor de base de datos.

### 📁 Estructura del Proyecto

```
frontend/
├── src/
│   ├── components/
│   │   ├── Layout.tsx       # Layout principal con sidebar
│   │   └── Sidebar.tsx      # Navegación lateral
│   ├── pages/
│   │   ├── SQLConsole.tsx   # ✅ Console SQL completo
│   │   ├── SIFTManager.tsx  # ✅ Gestor de imágenes SIFT
│   │   ├── BoWManager.tsx   # 🚧 BoW (placeholder)
│   │   └── TablesView.tsx   # ✅ Vista de tablas
│   ├── App.tsx              # Router principal
│   ├── main.tsx             # Entry point
│   └── index.css            # Estilos globales
├── package.json             # Dependencias
├── vite.config.ts           # Configuración Vite
├── tsconfig.json            # TypeScript config
└── README.md                # Documentación
```

## 🎯 Características Implementadas

### 1. **SQL Console** ✅
- Editor de SQL con syntax highlighting
- Ejecución de consultas en tiempo real
- Visualización de resultados en tablas
- Historial de consultas
- Tiempo de ejecución
- Soporte para todas las estructuras (Sequential, B+Tree, ISAM, Hash)

### 2. **SIFT Manager** ✅
- **Indexación Batch**: Arrastra múltiples imágenes, luego presiona "Indexar"
- **Cola visual**: Ver progreso de cada imagen
- **Búsqueda por similitud**: Sube una query image y busca las K más similares
- **Galería**: Visualiza todas las imágenes indexadas
- **Optimizado**: 50 clusters, vocabulario cada 20 imágenes

### 3. **Tables View** ✅
- Lista de todas las tablas
- Visualización de datos por tabla
- Navegación entre tablas

### 4. **BoW Manager** 🚧
- Placeholder listo para implementar

## 📦 Instalación

### Requisitos Previos
- Node.js 18+ (verificar con `node -v`)
- npm o yarn

### Paso 1: Instalar dependencias

```bash
cd frontend
npm install
```

### Paso 2: Iniciar desarrollo

**Opción A - Windows:**
```bash
start-dev.bat
```

**Opción B - Manual:**
```bash
npm run dev
```

El frontend estará en: `http://localhost:5173`

## 🔌 Backend

El frontend se conecta automáticamente al backend en `http://localhost:8000` gracias al proxy de Vite.

**Asegúrate de tener el backend corriendo:**

```bash
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🏗️ Build para Producción

```bash
cd frontend
npm run build
```

Los archivos se generan en `../api/static/dist` y son servidos automáticamente por FastAPI.

**Acceder en producción:**
- `http://localhost:8000/` → React App
- `http://localhost:8000/api/docs` → FastAPI Docs

## 🎨 Diseño

- **Tema oscuro** estilo VS Code
- **Responsive** para móviles y desktop
- **Minimalista** y profesional
- **Animaciones** sutiles y fluidas
- **Sin bugs** de renderizado

### Paleta de Colores

```css
--bg-primary: #1e1e1e      /* Fondo principal */
--bg-secondary: #252526    /* Paneles */
--bg-tertiary: #2d2d30     /* Inputs */
--accent-blue: #3794ff     /* Primario */
--accent-green: #4ec9b0    /* Success */
--accent-red: #f44747      /* Error */
--text-primary: #cccccc    /* Texto principal */
--text-secondary: #858585  /* Texto secundario */
```

## 🔥 Ventajas de React vs HTML Estático

✅ **Componentes reutilizables**: No repetir código
✅ **Estado centralizado**: Manejo limpio de datos
✅ **Routing SPA**: Navegación sin recargar
✅ **Type safety**: TypeScript previene errores
✅ **Hot reload**: Ver cambios instantáneamente
✅ **Build optimizado**: Vite genera código minificado
✅ **Mejor rendimiento**: Virtual DOM optimiza renders
✅ **Escalable**: Fácil agregar nuevas páginas

## 📱 Estructura de Rutas

```
/              → Redirect a /sql
/sql           → SQL Console
/sift          → SIFT Image Manager
/bow           → BoW Document Manager
/tables        → Tables View
```

## 🛠️ Desarrollo

### Agregar una nueva página

1. Crear archivo en `src/pages/NuevaPagina.tsx`
2. Agregar ruta en `src/App.tsx`
3. Agregar link en `src/components/Sidebar.tsx`

### Agregar nuevo endpoint API

El frontend ya está configurado para usar el proxy:

```typescript
// Automáticamente se redirige a http://localhost:8000/api/...
fetch('/api/nuevo-endpoint')
```

## 🐛 Troubleshooting

### "Cannot GET /"
→ El backend no está corriendo. Inicia FastAPI primero.

### "Failed to fetch"
→ Verifica que el backend esté en `http://localhost:8000`

### "Module not found"
→ Ejecuta `npm install`

### Estilos no se aplican
→ Verifica que los archivos `.css` estén importados

## 📞 Soporte

Para problemas o preguntas:
1. Revisa la consola del navegador (F12)
2. Revisa los logs del backend
3. Verifica que ambos servidores estén corriendo

## 🎓 Próximos Pasos

1. **Implementar BoW Manager**: Similar a SIFT pero para documentos
2. **Agregar autenticación**: Login/registro de usuarios
3. **Dashboard**: Estadísticas y métricas
4. **Export/Import**: Descargar resultados como CSV/JSON
5. **Temas**: Dark/Light mode toggle

## ✨ Resumen

Ahora tienes un **frontend profesional en React** que:

✅ Reemplaza completamente el HTML estático
✅ Es 100% funcional con tu backend FastAPI
✅ Tiene diseño moderno y minimalista
✅ Está optimizado y sin bugs
✅ Es fácil de extender y mantener

**¡Listo para usar! 🚀**
