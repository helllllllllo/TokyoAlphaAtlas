import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { TopBar } from "./components/TopBar";
import { useApp } from "./store";

export default function App() {
  const { status, error, load } = useApp();
  useEffect(() => { void load(); }, [load]);

  if (status === "error") {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%" }}>
        <div className="panel" style={{ padding: 32, maxWidth: 480 }}>
          <h2>データを読み込めません</h2>
          <p style={{ color: "var(--dim)" }}>{error}</p>
          <p style={{ color: "var(--faint)", fontSize: 12 }}>
            `pipeline/` で `make dev-data`（または実データで `make refresh`）を実行してから再読み込みしてください。
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <TopBar />
      <div className="screen">
        {status === "loading" ? (
          <p style={{ padding: 20, color: "var(--dim)" }}>読み込み中…</p>
        ) : (
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<p style={{ padding: 20 }}>地図（実装中）</p>} />
              <Route path="/compare" element={<p style={{ padding: 20 }}>比較（実装中）</p>} />
              <Route path="/benchmark" element={<p style={{ padding: 20 }}>査定（実装中）</p>} />
            </Routes>
          </ErrorBoundary>
        )}
      </div>
    </>
  );
}
