import { useState, useEffect } from "react";
import "./BoWManager.css";

interface Document {
  doc_id: number;
  filename: string;
  tokens_count: number;
}

interface Collection {
  name: string;
  has_index: boolean;
  documents_count: number;
  vocabulary_size: number;
}

interface SearchResult {
  doc_id: number;
  score: number;
  similarity_percentage: number;
}

export default function BoWManager() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string>("");
  const [newCollectionName, setNewCollectionName] = useState<string>("");
  const [uploadedDocs, setUploadedDocs] = useState<Document[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<
    "create" | "upload" | "search" | "manage"
  >("create");

  const API_BASE = "http://localhost:8000/api";

  // Cargar colecciones al montar
  useEffect(() => {
    loadCollections();
  }, []);

  const showMessage = (type: "success" | "error" | "info", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const loadCollections = async () => {
    try {
      const response = await fetch(`${API_BASE}/bow/collections`);
      const data = await response.json();
      if (data.success) {
        setCollections(data.collections);
      }
    } catch (error) {
      console.error("Error cargando colecciones:", error);
    }
  };

  const handleCreateCollection = async () => {
    if (!newCollectionName.trim()) {
      showMessage("error", "Por favor ingrese un nombre para la colección");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/bow/create-index`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ collection_name: newCollectionName }),
      });

      const data = await response.json();
      if (data.success) {
        showMessage("success", data.message);
        setNewCollectionName("");
        setSelectedCollection(newCollectionName);
        loadCollections();
      } else {
        showMessage("error", "Error creando colección");
      }
    } catch (error) {
      showMessage("error", "Error al crear colección");
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadDocuments = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedCollection) {
      showMessage("error", "Seleccione una colección primero");
      return;
    }

    const formElement = e.currentTarget;
    const fileInput = formElement.querySelector(
      'input[type="file"]'
    ) as HTMLInputElement;
    const files = fileInput?.files;

    if (!files || files.length === 0) {
      showMessage("error", "Seleccione al menos un archivo");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
      formData.append("collection_name", selectedCollection);

      const response = await fetch(`${API_BASE}/bow/upload-documents`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        showMessage(
          "success",
          `${data.processed_documents.length} documentos procesados`
        );
        setUploadedDocs(data.processed_documents);
        fileInput.value = ""; // Limpiar input
      } else {
        showMessage("error", "Error subiendo documentos");
      }
    } catch (error) {
      showMessage("error", "Error al subir documentos");
    } finally {
      setIsLoading(false);
    }
  };

  const handleBuildIndex = async () => {
    if (!selectedCollection) {
      showMessage("error", "Seleccione una colección");
      return;
    }

    if (uploadedDocs.length === 0) {
      showMessage("error", "Primero suba documentos");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("collection_name", selectedCollection);
      formData.append("total_docs", uploadedDocs.length.toString());

      const response = await fetch(`${API_BASE}/bow/build-index`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        showMessage(
          "success",
          `Índice construido: ${data.vocabulary_size} términos`
        );
        loadCollections();
      } else {
        showMessage("error", "Error construyendo índice");
      }
    } catch (error) {
      showMessage("error", "Error al construir índice");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!selectedCollection) {
      showMessage("error", "Seleccione una colección");
      return;
    }

    if (!searchQuery.trim()) {
      showMessage("error", "Ingrese una consulta");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("query", searchQuery);
      formData.append("k", "10");
      formData.append("collection_name", selectedCollection);

      const response = await fetch(`${API_BASE}/bow/search`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      if (data.success) {
        setSearchResults(data.results);
        showMessage("success", `${data.count} resultados encontrados`);
      } else {
        showMessage("error", "Error en la búsqueda");
      }
    } catch (error) {
      showMessage("error", "Error al buscar");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteCollection = async (collectionName: string) => {
    if (
      !confirm(`¿Está seguro de eliminar la colección "${collectionName}"?`)
    ) {
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/bow/collection/${collectionName}`,
        { method: "DELETE" }
      );

      const data = await response.json();
      if (data.success) {
        showMessage("success", data.message);
        if (selectedCollection === collectionName) {
          setSelectedCollection("");
        }
        loadCollections();
      } else {
        showMessage("error", "Error eliminando colección");
      }
    } catch (error) {
      showMessage("error", "Error al eliminar colección");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bow-manager">
      <div className="bow-header">
        <h1>Bag of Words Manager</h1>
        <p>Indexación y búsqueda de documentos con BOW + TF-IDF</p>
      </div>

      {/* Mensajes */}
      {message && (
        <div className={`bow-message bow-message-${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Selector de colección */}
      <div className="bow-collection-selector">
        <label>Colección Activa:</label>
        <select
          value={selectedCollection}
          onChange={(e) => setSelectedCollection(e.target.value)}
          className="bow-select"
        >
          <option value="">Seleccione una colección</option>
          {collections.map((col) => (
            <option key={col.name} value={col.name}>
              {col.name} ({col.documents_count} docs
              {col.has_index ? " ✓" : ""})
            </option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div className="bow-tabs">
        <button
          className={`bow-tab ${activeTab === "create" ? "active" : ""}`}
          onClick={() => setActiveTab("create")}
        >
          📁 Crear Colección
        </button>
        <button
          className={`bow-tab ${activeTab === "upload" ? "active" : ""}`}
          onClick={() => setActiveTab("upload")}
        >
          📤 Subir Documentos
        </button>
        <button
          className={`bow-tab ${activeTab === "search" ? "active" : ""}`}
          onClick={() => setActiveTab("search")}
        >
          🔍 Buscar
        </button>
        <button
          className={`bow-tab ${activeTab === "manage" ? "active" : ""}`}
          onClick={() => setActiveTab("manage")}
        >
          ⚙️ Gestionar
        </button>
      </div>

      {/* Contenido de tabs */}
      <div className="bow-tab-content">
        {/* TAB: Crear Colección */}
        {activeTab === "create" && (
          <div className="bow-card">
            <h2>Crear Nueva Colección</h2>
            <p className="bow-description">
              Una colección almacena documentos y su índice invertido
            </p>
            <div className="bow-form-group">
              <input
                type="text"
                placeholder="Nombre de la colección"
                value={newCollectionName}
                onChange={(e) => setNewCollectionName(e.target.value)}
                className="bow-input"
              />
              <button
                onClick={handleCreateCollection}
                disabled={isLoading}
                className="bow-button bow-button-primary"
              >
                {isLoading ? "Creando..." : "Crear Colección"}
              </button>
            </div>
          </div>
        )}

        {/* TAB: Subir Documentos */}
        {activeTab === "upload" && (
          <div className="bow-card">
            <h2>Subir Documentos</h2>
            <p className="bow-description">
              Suba archivos .txt para indexarlos en la colección seleccionada
            </p>

            <form onSubmit={handleUploadDocuments} className="bow-upload-form">
              <div className="bow-form-group">
                <input
                  type="file"
                  multiple
                  accept=".txt"
                  className="bow-file-input"
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !selectedCollection}
                className="bow-button bow-button-primary"
              >
                {isLoading ? "Subiendo..." : "Subir Documentos"}
              </button>
            </form>

            {uploadedDocs.length > 0 && (
              <div className="bow-docs-list">
                <h3>Documentos Subidos ({uploadedDocs.length})</h3>
                <table className="bow-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nombre</th>
                      <th>Tokens</th>
                    </tr>
                  </thead>
                  <tbody>
                    {uploadedDocs.map((doc) => (
                      <tr key={doc.doc_id}>
                        <td>{doc.doc_id}</td>
                        <td>{doc.filename}</td>
                        <td>{doc.tokens_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                <button
                  onClick={handleBuildIndex}
                  disabled={isLoading}
                  className="bow-button bow-button-success"
                  style={{ marginTop: "20px" }}
                >
                  {isLoading ? "Construyendo..." : "Construir Índice"}
                </button>
              </div>
            )}
          </div>
        )}

        {/* TAB: Buscar */}
        {activeTab === "search" && (
          <div className="bow-card">
            <h2>Buscar Documentos</h2>
            <p className="bow-description">
              Busque documentos similares usando consultas en lenguaje natural
            </p>

            <form onSubmit={handleSearch} className="bow-search-form">
              <div className="bow-form-group">
                <input
                  type="text"
                  placeholder="Ingrese su consulta..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bow-input"
                />
                <button
                  type="submit"
                  disabled={isLoading || !selectedCollection}
                  className="bow-button bow-button-primary"
                >
                  {isLoading ? "Buscando..." : "Buscar"}
                </button>
              </div>
            </form>

            {searchResults.length > 0 && (
              <div className="bow-results">
                <h3>Resultados ({searchResults.length})</h3>
                <div className="bow-results-grid">
                  {searchResults.map((result) => (
                    <div key={result.doc_id} className="bow-result-card">
                      <div className="bow-result-header">
                        <span className="bow-result-id">
                          Documento #{result.doc_id}
                        </span>
                        <span className="bow-result-score">
                          {result.similarity_percentage}%
                        </span>
                      </div>
                      <div className="bow-result-bar">
                        <div
                          className="bow-result-bar-fill"
                          style={{ width: `${result.similarity_percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB: Gestionar */}
        {activeTab === "manage" && (
          <div className="bow-card">
            <h2>Gestionar Colecciones</h2>
            <p className="bow-description">
              Ver y eliminar colecciones existentes
            </p>

            {collections.length === 0 ? (
              <div className="bow-empty-state">
                <p>No hay colecciones creadas</p>
              </div>
            ) : (
              <div className="bow-collections-grid">
                {collections.map((col) => (
                  <div key={col.name} className="bow-collection-card">
                    <div className="bow-collection-header">
                      <h3>{col.name}</h3>
                      <button
                        onClick={() => handleDeleteCollection(col.name)}
                        className="bow-button-delete"
                        title="Eliminar colección"
                      >
                        🗑️
                      </button>
                    </div>
                    <div className="bow-collection-stats">
                      <div className="bow-stat">
                        <span className="bow-stat-label">Documentos:</span>
                        <span className="bow-stat-value">
                          {col.documents_count}
                        </span>
                      </div>
                      <div className="bow-stat">
                        <span className="bow-stat-label">Vocabulario:</span>
                        <span className="bow-stat-value">
                          {col.vocabulary_size}
                        </span>
                      </div>
                      <div className="bow-stat">
                        <span className="bow-stat-label">Estado:</span>
                        <span
                          className={`bow-stat-badge ${
                            col.has_index
                              ? "bow-badge-success"
                              : "bow-badge-warning"
                          }`}
                        >
                          {col.has_index ? "✓ Indexado" : "⚠ Sin índice"}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
