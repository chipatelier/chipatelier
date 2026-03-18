import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register, login, getMe } from "../api/auth";
import { useStore } from "../store";

const PAGE_BG: React.CSSProperties = {
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  background: "#0d1117",
};

const CARD: React.CSSProperties = {
  width: "100%",
  maxWidth: 420,
  background: "#161b22",
  borderRadius: 12,
  border: "1px solid #30363d",
  padding: 32,
};

const HEADING: React.CSSProperties = {
  fontSize: 22,
  fontWeight: 700,
  color: "#e6edf3",
  marginBottom: 24,
};

const ERROR_BOX: React.CSSProperties = {
  marginBottom: 16,
  borderRadius: 6,
  background: "#3d1f1f",
  border: "1px solid #6e3630",
  color: "#f85149",
  padding: "12px 16px",
  fontSize: 13,
};

const LABEL: React.CSSProperties = {
  display: "block",
  fontSize: 13,
  fontWeight: 500,
  color: "#8b949e",
  marginBottom: 4,
};

const HINT: React.CSSProperties = {
  color: "#6e7681",
};

const INPUT: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  border: "1px solid #30363d",
  background: "#0d1117",
  color: "#e6edf3",
  padding: "8px 12px",
  fontSize: 14,
  outline: "none",
  boxSizing: "border-box",
};

const BUTTON: React.CSSProperties = {
  width: "100%",
  borderRadius: 6,
  background: "#238636",
  color: "#ffffff",
  padding: "10px 16px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
};

const BUTTON_DISABLED: React.CSSProperties = {
  ...BUTTON,
  opacity: 0.5,
  cursor: "not-allowed",
};

const FOOTER: React.CSSProperties = {
  marginTop: 16,
  fontSize: 13,
  textAlign: "center",
  color: "#8b949e",
};

const LINK: React.CSSProperties = {
  color: "#58a6ff",
  textDecoration: "none",
};

export default function RegisterPage(): React.ReactElement {
  const navigate = useNavigate();
  const setAuth = useStore((s) => s.setAuth);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await register(email, password, displayName || undefined);
      const tokenResp = await login(email, password);
      const user = await getMe();
      setAuth(user, tokenResp.access_token);
      navigate("/projects");
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr?.response?.status === 409) {
        setError("Email already taken. Please sign in or use a different email.");
      } else {
        setError("Registration failed. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={PAGE_BG}>
      <div style={CARD}>
        <h1 style={HEADING}>Create your account</h1>

        {error && <div style={ERROR_BOX}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label htmlFor="displayName" style={LABEL}>
              Display name <span style={HINT}>(optional)</span>
            </label>
            <input
              id="displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoComplete="name"
              style={INPUT}
            />
          </div>

          <div>
            <label htmlFor="email" style={LABEL}>
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              style={INPUT}
            />
          </div>

          <div>
            <label htmlFor="password" style={LABEL}>
              Password <span style={HINT}>(min 8 characters)</span>
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              style={INPUT}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={loading ? BUTTON_DISABLED : BUTTON}
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p style={FOOTER}>
          Already have an account?{" "}
          <Link to="/login" style={LINK}>
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
