import { Route, Routes } from "react-router-dom";
import { TopBar } from "./components/TopBar";

export default function App() {
  return (
    <>
      <TopBar />
      <div className="screen">
        <Routes>
          <Route path="/" element={<p style={{ padding: 20 }}>地図（実装中）</p>} />
          <Route path="/compare" element={<p style={{ padding: 20 }}>比較（実装中）</p>} />
          <Route path="/benchmark" element={<p style={{ padding: 20 }}>査定（実装中）</p>} />
        </Routes>
      </div>
    </>
  );
}
