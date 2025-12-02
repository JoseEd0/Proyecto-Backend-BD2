import { useState, useEffect, useRef } from "react";
import {
  Upload,
  Search,
  Image as ImageIcon,
  Trash2,
  RefreshCw,
} from "lucide-react";
import "./SIFTManager.css";

interface ImageItem {
  id: number;
  name: string;
  path: string;
}

interface QueueItem {
  file: File;
  id: string;
  status: "waiting" | "processing" | "success" | "error";
  progress: number;
  imageId?: number;
  message?: string;
  preview?: string; // URL de previsualización
}

export default function SIFTManager() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isIndexing, setIsIndexing] = useState(false);
  const [queryFile, setQueryFile] = useState<File | null>(null);
  const [queryPreview, setQueryPreview] = useState<string | null>(null);
  const [kValue, setKValue] = useState(10);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [imageTimestamp, setImageTimestamp] = useState(Date.now());
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      const res = await fetch("/api/sift/images");
      const data = await res.json();
      console.log("Backend response:", data); // Debug

      // El backend devuelve {success, images, count}
      if (data.success && Array.isArray(data.images)) {
        // Mapear campos del backend (nombre, ruta) al frontend (name, path)
        const mappedImages = data.images
          .filter((img: any) => img.id !== null && img.id !== undefined) // Filtrar IDs inválidos
          .map((img: any) => {
            console.log("Mapping image:", img); // Debug
            return {
              id: img.id,
              name: img.nombre || img.name || "",
              path: img.ruta || img.path || "",
            };
          });
        console.log("Mapped images:", mappedImages); // Debug
        setImages(mappedImages);
        setImageTimestamp(Date.now()); // Actualizar timestamp para forzar recarga
      } else {
        console.error("Invalid response format:", data);
        setImages([]);
      }
    } catch (error) {
      console.error("Error loading images:", error);
      setImages([]);
    }
  };

  const handleFilesSelect = (files: FileList | null) => {
    if (!files) return;

    const newItems: QueueItem[] = Array.from(files).map((file) => ({
      file,
      id: Date.now() + Math.random() + "",
      status: "waiting",
      progress: 0,
      preview: URL.createObjectURL(file), // Crear URL de previsualización
    }));

    setQueue((prev) => [...prev, ...newItems]);
  };

  const startBatchIndexing = async () => {
    if (queue.length === 0 || isIndexing) return;

    setIsIndexing(true);

    for (const item of queue) {
      setQueue((prev) =>
        prev.map((q) =>
          q.id === item.id ? { ...q, status: "processing", progress: 50 } : q
        )
      );

      try {
        const formData = new FormData();
        formData.append("file", item.file);

        const res = await fetch("/api/sift/upload-image", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();

        if (res.ok) {
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? {
                    ...q,
                    status: "success",
                    progress: 100,
                    imageId: data.image_id,
                    message: data.has_vocabulary
                      ? `ID: ${data.image_id}`
                      : `${data.image_id} (${data.images_count}/10)`,
                  }
                : q
            )
          );
        } else {
          throw new Error(data.detail);
        }
      } catch (error: any) {
        setQueue((prev) =>
          prev.map((q) =>
            q.id === item.id
              ? { ...q, status: "error", message: error.message }
              : q
          )
        );
      }

      await new Promise((resolve) => setTimeout(resolve, 200));
    }

    setIsIndexing(false);
    loadImages();

    // Clear successful items after 2 seconds
    setTimeout(() => {
      setQueue((prev) => prev.filter((q) => q.status !== "success"));
    }, 2000);
  };

  const clearQueue = () => {
    if (!isIndexing) {
      // Revocar URLs para liberar memoria
      queue.forEach((item) => {
        if (item.preview) {
          URL.revokeObjectURL(item.preview);
        }
      });
      setQueue([]);
    }
  };

  const handleQueryFileSelect = (file: File | null) => {
    if (!file) return;

    setQueryFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setQueryPreview(e.target?.result as string);
    reader.readAsDataURL(file);
  };

  const searchSimilar = async () => {
    if (!queryFile) return;

    setSearching(true);
    setSearchResults(null);

    try {
      const formData = new FormData();
      // El backend espera 'file' no 'query_image'
      formData.append("file", queryFile);
      formData.append("k", kValue.toString());

      const res = await fetch("/api/sift/search-similar", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      console.log("[DEBUG] Search response:", data); // Debug

      if (res.ok && data.success) {
        console.log("[DEBUG] Search results:", data.results); // Debug
        setSearchResults(data.results);
      } else {
        throw new Error(data.detail || "Error en la búsqueda");
      }
    } catch (error) {
      console.error("Error searching:", error);
      alert("Error al buscar imágenes similares");
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="sift-manager">
      <div className="sift-header">
        <h1>SIFT Image Manager</h1>
        <p>Index and search images using SIFT + BoVW + TF-IDF</p>
      </div>

      <div className="sift-container">
        {/* Panel de Indexación */}
        <div className="index-panel">
          <div className="panel-header">
            <h2>
              <Upload size={20} /> Indexar Imágenes
            </h2>
          </div>

          <div
            className="upload-drop-zone"
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              handleFilesSelect(e.dataTransfer.files);
            }}
          >
            <ImageIcon size={48} />
            <p>Arrastra imágenes aquí</p>
            <span>o haz click para seleccionar</span>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            style={{ display: "none" }}
            onChange={(e) => handleFilesSelect(e.target.files)}
          />

          <div className="index-controls">
            <button
              className="btn btn-primary"
              onClick={startBatchIndexing}
              disabled={queue.length === 0 || isIndexing}
            >
              🚀 Indexar {queue.length} imágenes
            </button>
            <button
              className="btn"
              onClick={clearQueue}
              disabled={queue.length === 0 || isIndexing}
            >
              <Trash2 size={16} /> Limpiar
            </button>
          </div>

          {queue.length > 0 && (
            <div className="queue-list">
              {queue.map((item) => (
                <div key={item.id} className={`queue-item ${item.status}`}>
                  {item.preview && (
                    <img
                      src={item.preview}
                      alt={item.file.name}
                      className="queue-preview"
                    />
                  )}
                  <div className="queue-status">
                    {item.status === "waiting" && "⏳"}
                    {item.status === "processing" && "⚙️"}
                    {item.status === "success" && "✓"}
                    {item.status === "error" && "✗"}
                  </div>
                  <div className="queue-info">
                    <span className="queue-name">{item.file.name}</span>
                    {item.message && (
                      <span className="queue-message">{item.message}</span>
                    )}
                  </div>
                  <div className="queue-progress">
                    <div
                      className="queue-progress-bar"
                      style={{ width: `${item.progress}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Panel de Búsqueda */}
        <div className="search-panel">
          <div className="panel-header">
            <h2>
              <Search size={20} /> Buscar Similares
            </h2>
          </div>

          {!queryPreview ? (
            <div
              className="query-upload-area"
              onClick={() => queryInputRef.current?.click()}
            >
              <Search size={36} />
              <p>Sube una imagen query</p>
            </div>
          ) : (
            <div className="query-preview-container">
              <img src={queryPreview} alt="Query" className="query-preview" />
              <button
                className="btn"
                onClick={() => {
                  setQueryFile(null);
                  setQueryPreview(null);
                  setSearchResults(null);
                }}
              >
                Cambiar imagen
              </button>
            </div>
          )}

          <input
            ref={queryInputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={(e) =>
              e.target.files && handleQueryFileSelect(e.target.files[0])
            }
          />

          <div className="search-controls">
            <div className="k-control">
              <label>K Vecinos:</label>
              <input
                type="number"
                min="1"
                max="50"
                value={kValue}
                onChange={(e) => setKValue(Number(e.target.value))}
              />
            </div>
            <button
              className="btn btn-primary"
              onClick={searchSimilar}
              disabled={!queryFile || searching}
            >
              <Search size={16} />
              {searching ? "Buscando..." : "Buscar"}
            </button>
          </div>

          {searching && (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Analizando imagen...</p>
            </div>
          )}

          {searchResults && (
            <div className="search-results">
              <h3>Resultados ({searchResults.length})</h3>
              <div className="results-grid">
                {searchResults.map((result, idx) => (
                  <div key={idx} className="result-item">
                    <img
                      src={`/api/sift/image-file/${result.id}?t=${imageTimestamp}`}
                      alt={result.nombre || "Resultado"}
                      onError={(e) => {
                        console.error(
                          `Error loading result image ${result.id}`
                        );
                        e.currentTarget.src =
                          'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text x="50%" y="50%" text-anchor="middle">Error</text></svg>';
                      }}
                    />
                    <div className="result-info">
                      <span className="result-name">
                        {result.nombre || `Imagen ${result.id}`}
                      </span>
                      <span className="result-score">
                        {(result.similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Panel de Galería */}
        <div className="gallery-panel">
          <div className="panel-header">
            <h2>
              <ImageIcon size={20} /> Índice ({images.length})
            </h2>
            <button className="btn-icon" onClick={loadImages}>
              <RefreshCw size={16} />
            </button>
          </div>

          <div className="gallery-grid">
            {Array.isArray(images) &&
              images.map((image) => (
                <div key={image.id} className="gallery-item">
                  <img
                    src={`/api/sift/image-file/${image.id}?t=${imageTimestamp}`}
                    alt={image.name}
                    loading="lazy"
                    onError={(e) => {
                      console.error(`Error loading image ${image.id}`);
                      e.currentTarget.style.display = "none";
                    }}
                  />
                  <div className="gallery-info">
                    <span>{image.name}</span>
                    <span className="gallery-id">ID: {image.id}</span>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
