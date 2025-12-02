import { useState, useEffect } from "react";
import { Table, RefreshCw, Database } from "lucide-react";
import "./TablesView.css";

interface TableInfo {
  name: string;
  structure: string;
  record_count?: number;
}

export default function TablesView() {
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadTables();
  }, []);

  const loadTables = async () => {
    try {
      const res = await fetch("/api/tables");
      const data = await res.json();
      setTables(data);
    } catch (error) {
      console.error("Error loading tables:", error);
    }
  };

  const loadTableData = async (tableName: string) => {
    setLoading(true);
    setSelectedTable(tableName);
    setTableData(null);

    try {
      const res = await fetch(`/api/table-data/${tableName}`);
      const data = await res.json();
      setTableData(data.data || []);
    } catch (error) {
      console.error("Error loading table data:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="tables-view">
      <div className="tables-header">
        <h1>Tables View</h1>
        <p>Explore all tables in your database</p>
      </div>

      <div className="tables-container">
        <div className="tables-list-panel">
          <div className="panel-header">
            <h2>
              <Database size={18} /> Tables ({tables.length})
            </h2>
            <button className="btn-icon" onClick={loadTables}>
              <RefreshCw size={16} />
            </button>
          </div>

          <div className="tables-list">
            {tables.map((table) => (
              <div
                key={table}
                className={`table-item ${
                  selectedTable === table ? "active" : ""
                }`}
                onClick={() => loadTableData(table)}
              >
                <Table size={16} />
                <span>{table}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="table-data-panel">
          {!selectedTable ? (
            <div className="empty-state">
              <Table size={64} />
              <p>Selecciona una tabla para ver su contenido</p>
            </div>
          ) : loading ? (
            <div className="loading-container">
              <div className="spinner"></div>
              <p>Cargando datos...</p>
            </div>
          ) : tableData && tableData.length > 0 ? (
            <div className="table-data-container">
              <div className="table-data-header">
                <h2>{selectedTable}</h2>
                <span>{tableData.length} registros</span>
              </div>
              <div className="data-table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      {Object.keys(tableData[0]).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.map((row, i) => (
                      <tr key={i}>
                        {Object.values(row).map((val: any, j) => (
                          <td key={j}>{JSON.stringify(val)}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="empty-state">
              <p>Tabla vacía</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
