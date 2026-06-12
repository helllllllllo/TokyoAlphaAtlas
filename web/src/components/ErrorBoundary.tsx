import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error == null) return this.props.children;
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100%" }}>
        <div className="panel" style={{ padding: 32, maxWidth: 480 }}>
          <h2>エラーが発生しました</h2>
          <p style={{ color: "var(--dim)" }}>{this.state.error.message}</p>
          <button className="primary" onClick={() => window.location.reload()}>
            再読み込み
          </button>
        </div>
      </div>
    );
  }
}
