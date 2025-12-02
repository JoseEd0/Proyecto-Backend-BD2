import { useState, useEffect } from "react";
import { Play, Trash2, Download, Upload, Clock } from "lucide-react";
import "./SQLConsole.css";

interface QueryResult {
  success: boolean;
  result?: any;
  parsed_query?: any;
  execution_time_ms: number;
  errors?: string[];
  query_type?: string;
}

export default function SQLConsole() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      // Backend devuelve {history: [], total_queries}
      if (data.history && Array.isArray(data.history)) {
        setHistory(data.history.slice(-10).reverse());
      } else {
        setHistory([]);
      }
    } catch (error) {
      console.error("Error loading history:", error);
      setHistory([]);
    }
  };

  const executeQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch("/api/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql: query, should_validate: true }),
      });

      const data = await response.json();
      setResult(data);

      if (data.success) {
        loadHistory();
      }
    } catch (error: any) {
      setResult({
        success: false,
        errors: [error.message],
        execution_time_ms: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const renderResult = () => {
    if (!result) return null;

    if (!result.success) {
      return (
        <div className="result-error">
          <h3>❌ Error</h3>
          {result.errors?.map((err, i) => (
            <p key={i}>{err}</p>
          ))}
        </div>
      );
    }

    const data = result.result;

    if (Array.isArray(data)) {
      if (data.length === 0) {
        return <div className="result-empty">No hay resultados</div>;
      }

      return (
        <div className="result-table-container">
          <table className="result-table">
            <thead>
              <tr>
                {Object.keys(data[0]).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, i) => (
                <tr key={i}>
                  {Object.values(row).map((val: any, j) => (
                    <td key={j}>{JSON.stringify(val)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (typeof data === "object") {
      return (
        <div className="result-json">
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      );
    }

    return (
      <div className="result-message">
        <p>{String(data)}</p>
      </div>
    );
  };

  return (
    <div className="sql-console">
      <div className="console-header">
        <h1>SQL Console</h1>
        <p>
          Execute SQL queries on multiple structures (Sequential, B+Tree, ISAM,
          Hash)
        </p>
      </div>

      <div className="console-container">
        <div className="editor-section">
          <div className="editor-toolbar">
            <button
              className="btn btn-primary"
              onClick={executeQuery}
              disabled={loading}
            >
              <Play size={16} />
              {loading ? "Ejecutando..." : "Ejecutar"}
            </button>
            <button className="btn" onClick={() => setQuery("")}>
              <Trash2 size={16} />
              Limpiar
            </button>
            <button className="btn">
              <Upload size={16} />
              Importar CSV
            </button>
          </div>

          <textarea
            className="sql-editor"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Escribe tu consulta SQL aquí...&#10;&#10;Ejemplo:&#10;SELECT * FROM usuarios WHERE edad > 25"
            spellCheck={false}
          />

          {result && (
            <div className="result-info">
              <Clock size={14} />
              <span>Tiempo: {result.execution_time_ms.toFixed(2)}ms</span>
              {result.query_type && (
                <span className="query-type">{result.query_type}</span>
              )}
            </div>
          )}
        </div>

        <div className="results-section">
          <h2>Resultados</h2>
          {loading ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Ejecutando consulta...</p>
            </div>
          ) : (
            renderResult() || (
              <div className="result-placeholder">
                <p>Los resultados aparecerán aquí</p>
              </div>
            )
          )}
        </div>
      </div>

      <div className="history-section">
        <h2>Historial Reciente</h2>
        <div className="history-list">
          {history.map((q, i) => (
            <div key={i} className="history-item" onClick={() => setQuery(q)}>
              <code>{q}</code>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
