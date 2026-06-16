import { lazy, Suspense, useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { SearchBox } from "./components/SearchBox";
import { TopBar } from "./components/TopBar";
import { MapScreen } from "./screens/MapScreen";
import { useApp } from "./store";

const CompareScreen = lazy(() =>
  import("./screens/CompareScreen").then(m => ({ default: m.CompareScreen })),
);
const BenchmarkScreen = lazy(() =>
  import("./screens/BenchmarkScreen").then(m => ({ default: m.BenchmarkScreen })),
);
const DiscoverScreen = lazy(() =>
  import("./screens/DiscoverScreen").then(m => ({ default: m.DiscoverScreen })),
);

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
      <TopBar>{status === "ready" ? <SearchBox /> : undefined}</TopBar>
      <div className="screen">
        {status === "loading" ? (
          <p style={{ padding: 20, color: "var(--dim)" }}>読み込み中…</p>
        ) : (
          <ErrorBoundary>
            <Suspense fallback={<div style={{ padding: 20, color: "var(--dim)" }}>読み込み中…</div>}>
              <Routes>
                <Route path="/" element={<MapScreen />} />
                <Route path="/discover" element={<DiscoverScreen />} />
                <Route path="/compare" element={<CompareScreen />} />
                <Route path="/benchmark" element={<BenchmarkScreen />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        )}
      </div>
    </>
  );
}
