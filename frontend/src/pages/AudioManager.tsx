import { useState, useEffect, useRef } from "react";
import {
  Upload,
  Search,
  Music,
  RefreshCw,
  Play,
  Pause,
  Volume2,
  X,
  Mic,
} from "lucide-react";
import "./AudioManager.css";

interface AudioItem {
  id: number;
  nombre: string;
  ruta: string;
  duracion: number;
}

interface QueueItem {
  file: File;
  id: string;
  status: "waiting" | "processing" | "success" | "error";
  progress: number;
  audioId?: number;
  message?: string;
  previewUrl?: string;
}

export default function AudioManager() {
  const [audios, setAudios] = useState<AudioItem[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [isIndexing, setIsIndexing] = useState(false);
  const [queryFile, setQueryFile] = useState<File | null>(null);
  const [queryPreviewUrl, setQueryPreviewUrl] = useState<string | null>(null);
  const [kValue, setKValue] = useState(10);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [playingQueueId, setPlayingQueueId] = useState<string | null>(null);
  const [isPlayingQuery, setIsPlayingQuery] = useState(false);
  const [stats, setStats] = useState<any>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryInputRef = useRef<HTMLInputElement>(null);
  const audioPlayerRef = useRef<HTMLAudioElement>(null);
  const queuePlayerRef = useRef<HTMLAudioElement>(null);
  const queryPlayerRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    loadAudios();
    loadStats();
  }, []);

  useEffect(() => {
    return () => {
      queue.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      if (queryPreviewUrl) URL.revokeObjectURL(queryPreviewUrl);
    };
  }, []);

  const loadAudios = async () => {
    try {
      const res = await fetch("/api/audio/list");
      const data = await res.json();

      if (data.success && Array.isArray(data.audios)) {
        const mappedAudios = data.audios
          .filter((a: any) => a.id !== null && a.id !== undefined)
          .map((a: any) => ({
            id: a.id,
            nombre: a.nombre || a.name || "",
            ruta: a.ruta || a.path || "",
            duracion: a.duracion || 0,
          }));
        setAudios(mappedAudios);
      } else {
        setAudios([]);
      }
    } catch (error) {
      console.error("Error loading audios:", error);
      setAudios([]);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch("/api/audio/stats");
      const data = await res.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error("Error loading stats:", error);
    }
  };

  const handleFilesSelect = (files: FileList | null) => {
    if (!files) return;

    const newItems: QueueItem[] = Array.from(files).map((file) => ({
      file,
      id: Date.now() + Math.random() + "",
      status: "waiting",
      progress: 0,
      previewUrl: URL.createObjectURL(file),
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

        const res = await fetch("/api/audio/upload", {
          method: "POST",
          body: formData,
        });

        const data = await res.json();

        if (res.ok && data.success) {
          setQueue((prev) =>
            prev.map((q) =>
              q.id === item.id
                ? {
                    ...q,
                    status: "success",
                    progress: 100,
                    audioId: data.audio_id,
                    message: data.has_vocabulary
                      ? "✓ Indexado"
                      : `Guardado (${data.audios_count}/5)`,
                  }
                : q
            )
          );
        } else {
          throw new Error(data.detail || data.error);
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

      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    setIsIndexing(false);
    loadAudios();
    loadStats();

    setTimeout(() => {
      setQueue((prev) => {
        prev
          .filter((q) => q.status === "success")
          .forEach((q) => {
            if (q.previewUrl) URL.revokeObjectURL(q.previewUrl);
          });
        return prev.filter((q) => q.status !== "success");
      });
    }, 2000);
  };

  const clearQueue = () => {
    if (!isIndexing) {
      queue.forEach((item) => {
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      });
      setQueue([]);
    }
  };

  const removeFromQueue = (id: string) => {
    setQueue((prev) => {
      const item = prev.find((q) => q.id === id);
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl);
      return prev.filter((q) => q.id !== id);
    });
    if (playingQueueId === id) {
      queuePlayerRef.current?.pause();
      setPlayingQueueId(null);
    }
  };

  const playQueueItem = (item: QueueItem) => {
    if (playingQueueId === item.id) {
      queuePlayerRef.current?.pause();
      setPlayingQueueId(null);
    } else {
      if (queuePlayerRef.current && item.previewUrl) {
        queuePlayerRef.current.src = item.previewUrl;
        queuePlayerRef.current.play();
        setPlayingQueueId(item.id);
        setPlayingId(null);
        setIsPlayingQuery(false);
      }
    }
  };

  const handleQueryFileSelect = (file: File | null) => {
    if (!file) return;
    if (queryPreviewUrl) URL.revokeObjectURL(queryPreviewUrl);
    setQueryFile(file);
    setQueryPreviewUrl(URL.createObjectURL(file));
    setSearchResults(null);
  };

  const clearQuery = () => {
    if (queryPreviewUrl) URL.revokeObjectURL(queryPreviewUrl);
    setQueryFile(null);
    setQueryPreviewUrl(null);
    setSearchResults(null);
    setIsPlayingQuery(false);
    queryPlayerRef.current?.pause();
  };

  const playQuery = () => {
    if (isPlayingQuery) {
      queryPlayerRef.current?.pause();
      setIsPlayingQuery(false);
    } else {
      if (queryPlayerRef.current && queryPreviewUrl) {
        queryPlayerRef.current.src = queryPreviewUrl;
        queryPlayerRef.current.play();
        setIsPlayingQuery(true);
        setPlayingId(null);
        setPlayingQueueId(null);
      }
    }
  };

  const searchSimilar = async () => {
    if (!queryFile) return;

    setSearching(true);
    setSearchResults(null);

    try {
      const formData = new FormData();
      formData.append("file", queryFile);
      formData.append("k", kValue.toString());

      const res = await fetch("/api/audio/search", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();

      if (res.ok && data.success) {
        setSearchResults(data.results);
      } else {
        throw new Error(data.detail || "Error en la búsqueda");
      }
    } catch (error) {
      console.error("Error searching:", error);
      alert("Error al buscar audios similares");
    } finally {
      setSearching(false);
    }
  };

  const playAudio = (audioId: number) => {
    if (playingId === audioId) {
      audioPlayerRef.current?.pause();
      setPlayingId(null);
    } else {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.src = `/api/audio/file/${audioId}`;
        audioPlayerRef.current.play();
        setPlayingId(audioId);
        setPlayingQueueId(null);
        setIsPlayingQuery(false);
      }
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="audio-manager">
      {/* Hidden audio players */}
      <audio ref={audioPlayerRef} onEnded={() => setPlayingId(null)} />
      <audio ref={queuePlayerRef} onEnded={() => setPlayingQueueId(null)} />
      <audio ref={queryPlayerRef} onEnded={() => setIsPlayingQuery(false)} />

      {/* Header */}
      <div className="audio-header">
        <div className="header-content">
          <div className="header-icon">
            <Mic size={32} />
          </div>
          <div className="header-text">
            <h1>Audio Similarity Search</h1>
            <p>Búsqueda por contenido usando MFCC + Bag of Audio Words + TF-IDF</p>
          </div>
        </div>

        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-value">{stats.num_audios}</span>
              <span className="stat-label">Audios</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.num_frames?.toLocaleString()}</span>
              <span className="stat-label">Frames MFCC</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.vocabulary_size}</span>
              <span className="stat-label">Vocabulario</span>
            </div>
            <div className="stat-card">
              <span className={`stat-status ${stats.has_vocabulary ? "ready" : "pending"}`}>
                {stats.has_vocabulary ? "✓ Listo" : "⏳ Pendiente"}
              </span>
              <span className="stat-label">Índice</span>
            </div>
          </div>
        )}
      </div>

      <div className="audio-container">
        {/* Panel de Indexación */}
        <div className="panel index-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Upload size={20} />
              <h2>Indexar Audios</h2>
            </div>
            {queue.length > 0 && (
              <span className="panel-badge">{queue.length}</span>
            )}
          </div>

          <div className="panel-content">
            <div
              className="drop-zone"
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add("drag-over");
              }}
              onDragLeave={(e) => e.currentTarget.classList.remove("drag-over")}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove("drag-over");
                handleFilesSelect(e.dataTransfer.files);
              }}
            >
              <div className="drop-icon">
                <Music size={32} />
              </div>
              <p className="drop-text">Arrastra archivos de audio aquí</p>
              <span className="drop-hint">o haz click para seleccionar</span>
              <span className="drop-formats">MP3 • WAV • OGG • FLAC • M4A</span>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="audio/*"
              multiple
              style={{ display: "none" }}
              onChange={(e) => handleFilesSelect(e.target.files)}
            />

            {queue.length > 0 && (
              <>
                <div className="queue-header">
                  <span>Cola de indexación</span>
                  <button
                    className="btn-text"
                    onClick={clearQueue}
                    disabled={isIndexing}
                  >
                    Limpiar todo
                  </button>
                </div>

                <div className="queue-list">
                  {queue.map((item) => (
                    <div key={item.id} className={`queue-item status-${item.status}`}>
                      <button
                        className="queue-play-btn"
                        onClick={() => playQueueItem(item)}
                        disabled={item.status === "processing"}
                      >
                        {playingQueueId === item.id ? (
                          <Pause size={16} />
                        ) : (
                          <Play size={16} />
                        )}
                      </button>

                      <div className="queue-info">
                        <span className="queue-name">{item.file.name}</span>
                        <span className="queue-meta">
                          {item.status === "waiting" && "En espera"}
                          {item.status === "processing" && "Procesando..."}
                          {item.status === "success" && item.message}
                          {item.status === "error" && `Error: ${item.message}`}
                        </span>
                      </div>

                      {item.status === "processing" && (
                        <div className="queue-spinner" />
                      )}

                      {item.status === "waiting" && (
                        <button
                          className="queue-remove-btn"
                          onClick={() => removeFromQueue(item.id)}
                        >
                          <X size={14} />
                        </button>
                      )}

                      {item.status === "success" && (
                        <span className="queue-check">✓</span>
                      )}

                      {item.status === "error" && (
                        <span className="queue-error">✗</span>
                      )}
                    </div>
                  ))}
                </div>

                <button
                  className="btn btn-primary btn-full"
                  onClick={startBatchIndexing}
                  disabled={queue.length === 0 || isIndexing}
                >
                  {isIndexing ? (
                    <>
                      <div className="btn-spinner" />
                      Indexando...
                    </>
                  ) : (
                    <>
                      <Upload size={18} />
                      Indexar {queue.length} audio{queue.length !== 1 ? "s" : ""}
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>

        {/* Panel de Búsqueda */}
        <div className="panel search-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Search size={20} />
              <h2>Buscar Similares</h2>
            </div>
          </div>

          <div className="panel-content">
            {!queryFile ? (
              <div
                className="drop-zone query-zone"
                onClick={() => queryInputRef.current?.click()}
              >
                <div className="drop-icon">
                  <Search size={32} />
                </div>
                <p className="drop-text">Sube un audio para buscar</p>
                <span className="drop-hint">Encontraremos los más similares</span>
              </div>
            ) : (
              <div className="query-card">
                <div className="query-visual">
                  <div className="audio-wave">
                    {[...Array(20)].map((_, i) => (
                      <div
                        key={i}
                        className={`wave-bar ${isPlayingQuery ? "playing" : ""}`}
                        style={{ animationDelay: `${i * 0.05}s` }}
                      />
                    ))}
                  </div>
                </div>

                <div className="query-info">
                  <span className="query-name">{queryFile.name}</span>
                  <span className="query-size">
                    {(queryFile.size / 1024 / 1024).toFixed(2)} MB
                  </span>
                </div>

                <div className="query-controls">
                  <button className="play-btn-lg" onClick={playQuery}>
                    {isPlayingQuery ? <Pause size={24} /> : <Play size={24} />}
                  </button>
                  <button className="btn-icon-sm" onClick={clearQuery}>
                    <X size={18} />
                  </button>
                </div>
              </div>
            )}

            <input
              ref={queryInputRef}
              type="file"
              accept="audio/*"
              style={{ display: "none" }}
              onChange={(e) =>
                e.target.files && handleQueryFileSelect(e.target.files[0])
              }
            />

            <div className="search-options">
              <div className="k-selector">
                <label>Resultados (K):</label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  value={kValue}
                  onChange={(e) => setKValue(Number(e.target.value))}
                />
                <span className="k-value">{kValue}</span>
              </div>

              <button
                className="btn btn-primary btn-full"
                onClick={searchSimilar}
                disabled={!queryFile || searching}
              >
                {searching ? (
                  <>
                    <div className="btn-spinner" />
                    Analizando...
                  </>
                ) : (
                  <>
                    <Search size={18} />
                    Buscar similares
                  </>
                )}
              </button>
            </div>

            {searchResults && searchResults.length > 0 && (
              <div className="results-section">
                <h3 className="results-title">
                  {searchResults.length} resultado{searchResults.length !== 1 ? "s" : ""} encontrado{searchResults.length !== 1 ? "s" : ""}
                </h3>

                <div className="results-list">
                  {searchResults.map((result, idx) => (
                    <div
                      key={idx}
                      className={`result-card ${playingId === result.id ? "playing" : ""}`}
                    >
                      <div className="result-rank">#{idx + 1}</div>

                      <button
                        className="result-play-btn"
                        onClick={() => playAudio(result.id)}
                      >
                        {playingId === result.id ? (
                          <Pause size={18} />
                        ) : (
                          <Play size={18} />
                        )}
                      </button>

                      <div className="result-info">
                        <span className="result-name">{result.nombre}</span>
                        <span className="result-duration">
                          <Volume2 size={12} />
                          {formatDuration(result.duracion || 0)}
                        </span>
                      </div>

                      <div className="result-score">
                        <div className="score-bar">
                          <div
                            className="score-fill"
                            style={{ width: `${result.similarity * 100}%` }}
                          />
                        </div>
                        <span className="score-value">
                          {(result.similarity * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Panel del Índice */}
        <div className="panel gallery-panel">
          <div className="panel-header">
            <div className="panel-title">
              <Music size={20} />
              <h2>Índice de Audios</h2>
            </div>
            <div className="panel-actions">
              <span className="panel-count">{audios.length}</span>
              <button
                className="btn-icon-sm"
                onClick={() => {
                  loadAudios();
                  loadStats();
                }}
              >
                <RefreshCw size={16} />
              </button>
            </div>
          </div>

          <div className="audio-list">
            {audios.length === 0 ? (
              <div className="empty-state">
                <Music size={48} />
                <p>No hay audios indexados</p>
                <span>Sube audios para comenzar</span>
              </div>
            ) : (
              audios.map((audio) => (
                <div
                  key={audio.id}
                  className={`audio-card ${playingId === audio.id ? "playing" : ""}`}
                >
                  <button
                    className="audio-play-btn"
                    onClick={() => playAudio(audio.id)}
                  >
                    {playingId === audio.id ? (
                      <Pause size={16} />
                    ) : (
                      <Play size={16} />
                    )}
                  </button>

                  <div className="audio-details">
                    <span className="audio-name">{audio.nombre}</span>
                    <span className="audio-meta">
                      {formatDuration(audio.duracion || 0)}
                    </span>
                  </div>

                  <span className="audio-id">#{audio.id}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
