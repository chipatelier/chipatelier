import React from "react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "#0d1117",
            fontFamily: "sans-serif",
          }}
        >
          <div
            style={{
              maxWidth: 480,
              padding: 32,
              background: "#161b22",
              border: "1px solid #30363d",
              borderRadius: 12,
              textAlign: "center",
            }}
          >
            <h2 style={{ color: "#f85149", fontSize: 20, margin: "0 0 12px 0" }}>
              Something went wrong
            </h2>
            <p style={{ color: "#8b949e", fontSize: 14, margin: "0 0 16px 0" }}>
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <button
              onClick={this.handleReset}
              style={{
                padding: "8px 16px",
                background: "#1f6feb",
                color: "#fff",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
