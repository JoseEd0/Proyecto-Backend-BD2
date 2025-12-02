export default function BoWManager() {
  return (
    <div style={{ padding: "30px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ marginBottom: "30px" }}>
        <h1
          style={{
            fontSize: "32px",
            fontWeight: 700,
            color: "white",
            marginBottom: "8px",
          }}
        >
          Bag of Words Manager
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
          Index and search documents using BoW + TF-IDF
        </p>
      </div>

      <div
        style={{
          background: "var(--bg-secondary)",
          border: "1px solid var(--border-color)",
          borderRadius: "8px",
          padding: "60px 20px",
          textAlign: "center",
        }}
      >
        <p style={{ fontSize: "18px", color: "var(--text-secondary)" }}>
          🚧 Módulo en desarrollo
        </p>
        <p
          style={{
            fontSize: "14px",
            color: "var(--text-secondary)",
            marginTop: "10px",
          }}
        >
          Este módulo estará disponible próximamente
        </p>
      </div>
    </div>
  );
}
