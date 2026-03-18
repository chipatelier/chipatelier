import React, { useState } from "react";
import { changePassword } from "../../api/auth";

export interface ChangePasswordModalProps {
  open: boolean;
  onClose: () => void;
}

const OVERLAY: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 200,
};

const CARD: React.CSSProperties = {
  width: "100%",
  maxWidth: 420,
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 12,
  padding: 28,
};

const HEADING: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#e6edf3",
  marginBottom: 20,
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

const BTN_PRIMARY: React.CSSProperties = {
  borderRadius: 6,
  background: "#238636",
  color: "#fff",
  padding: "8px 16px",
  fontSize: 14,
  fontWeight: 600,
  border: "none",
  cursor: "pointer",
};

const BTN_SECONDARY: React.CSSProperties = {
  borderRadius: 6,
  background: "none",
  color: "#8b949e",
  padding: "8px 16px",
  fontSize: 14,
  border: "1px solid #30363d",
  cursor: "pointer",
};

const ERROR_BOX: React.CSSProperties = {
  borderRadius: 6,
  background: "#3d1f1f",
  border: "1px solid #6e3630",
  color: "#f85149",
  padding: "10px 14px",
  fontSize: 13,
  marginBottom: 16,
};

const SUCCESS_BOX: React.CSSProperties = {
  borderRadius: 6,
  background: "#1a3a25",
  border: "1px solid #2ea043",
  color: "#3fb950",
  padding: "10px 14px",
  fontSize: 13,
  marginBottom: 16,
};

export function ChangePasswordModal({ open, onClose }: ChangePasswordModalProps): React.ReactElement | null {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  function reset(): void {
    setCurrent("");
    setNext("");
    setConfirm("");
    setError(null);
    setSuccess(false);
    setLoading(false);
  }

  function handleClose(): void {
    reset();
    onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);

    if (next.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (next === current) {
      setError("New password must differ from current password.");
      return;
    }

    setLoading(true);
    try {
      await changePassword(current, next);
      setSuccess(true);
      setTimeout(() => {
        reset();
        onClose();
      }, 1500);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "Failed to change password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={OVERLAY} onClick={handleClose}>
      <div style={CARD} onClick={(e) => e.stopPropagation()}>
        <h2 style={HEADING}>Change Password</h2>

        {error && <div style={ERROR_BOX}>{error}</div>}
        {success && <div style={SUCCESS_BOX}>Password changed successfully.</div>}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label htmlFor="cpw-current" style={LABEL}>Current password</label>
            <input
              id="cpw-current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              style={INPUT}
              aria-label="Current password"
            />
          </div>
          <div>
            <label htmlFor="cpw-new" style={LABEL}>New password</label>
            <input
              id="cpw-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              style={INPUT}
              aria-label="New password"
            />
          </div>
          <div>
            <label htmlFor="cpw-confirm" style={LABEL}>Confirm new password</label>
            <input
              id="cpw-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              style={INPUT}
              aria-label="Confirm new password"
            />
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 4 }}>
            <button type="button" style={BTN_SECONDARY} onClick={handleClose}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || success}
              style={{ ...BTN_PRIMARY, opacity: loading || success ? 0.6 : 1, cursor: loading || success ? "not-allowed" : "pointer" }}
            >
              {loading ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
