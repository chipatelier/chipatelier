import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { resetPassword } from "../api/auth";

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
  marginBottom: 8,
};

const SUBTITLE: React.CSSProperties = {
  fontSize: 13,
  color: "#8b949e",
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

export default function ResetPasswordPage(): React.ReactElement {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await resetPassword(email, token, newPassword);
      navigate("/login", {
        state: { flash: "Password reset successfully. Please sign in." },
      });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "Invalid or expired token.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={PAGE_BG}>
      <div style={CARD}>
        <h1 style={HEADING}>Reset your password</h1>
        <p style={SUBTITLE}>Enter your email, the token your instructor provided, and your new password.</p>

        {error && <div style={ERROR_BOX}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label htmlFor="rp-email" style={LABEL}>Email</label>
            <input
              id="rp-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              style={INPUT}
              aria-label="Email"
            />
          </div>

          <div>
            <label htmlFor="rp-token" style={LABEL}>Reset token</label>
            <input
              id="rp-token"
              type="text"
              value={token}
              onChange={(e) => setToken(e.target.value.toUpperCase())}
              required
              maxLength={8}
              placeholder="8-character token from your instructor"
              style={{ ...INPUT, letterSpacing: "0.1em", fontFamily: "monospace" }}
              aria-label="Reset token"
            />
          </div>

          <div>
            <label htmlFor="rp-newpw" style={LABEL}>New password</label>
            <input
              id="rp-newpw"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              style={INPUT}
              aria-label="New password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{ ...BUTTON, opacity: loading ? 0.6 : 1, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Resetting..." : "Reset password"}
          </button>
        </form>

        <p style={FOOTER}>
          <Link to="/login" style={LINK}>
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
