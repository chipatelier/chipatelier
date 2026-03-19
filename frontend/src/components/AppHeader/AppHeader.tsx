import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { logout as authLogout } from "../../api/auth";
import { useStore } from "../../store";
import { DEFAULT_QUOTA_GB } from "../../constants";

export interface AppHeaderProps {
  breadcrumbs?: React.ReactNode;
  actions?: React.ReactNode;
  onChangePassword?: () => void;
}

const HEADER: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 16,
  padding: "12px 24px",
  borderBottom: "1px solid #30363d",
  background: "#161b22",
  position: "relative",
};

const LOGO: React.CSSProperties = {
  fontSize: 18,
  fontWeight: 700,
  color: "#f0f6fc",
  textDecoration: "none",
  flexShrink: 0,
};

const BREADCRUMB_WRAP: React.CSSProperties = {
  flex: 1,
  fontSize: 13,
  color: "#8b949e",
};

const STORAGE_CHIP: React.CSSProperties = {
  fontSize: 12,
  color: "#8b949e",
  background: "#0d1117",
  border: "1px solid #30363d",
  borderRadius: 6,
  padding: "4px 10px",
  flexShrink: 0,
};

const DROPDOWN_BTN: React.CSSProperties = {
  background: "none",
  border: "1px solid #30363d",
  borderRadius: 6,
  color: "#c9d1d9",
  padding: "6px 12px",
  fontSize: 13,
  cursor: "pointer",
  flexShrink: 0,
};

const DROPDOWN_MENU: React.CSSProperties = {
  position: "absolute",
  top: "100%",
  marginTop: 4,
  background: "#161b22",
  border: "1px solid #30363d",
  borderRadius: 8,
  minWidth: 220,
  zIndex: 100,
  boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
};

const DROPDOWN_EMAIL: React.CSSProperties = {
  padding: "12px 16px 8px",
  fontSize: 12,
  color: "#8b949e",
  borderBottom: "1px solid #21262d",
};

const DROPDOWN_ITEM: React.CSSProperties = {
  display: "block",
  width: "100%",
  padding: "10px 16px",
  background: "none",
  border: "none",
  textAlign: "left",
  fontSize: 13,
  color: "#c9d1d9",
  cursor: "pointer",
};

const DROPDOWN_DIVIDER: React.CSSProperties = {
  borderTop: "1px solid #21262d",
  margin: "4px 0",
};

export function AppHeader({ breadcrumbs, actions, onChangePassword }: AppHeaderProps): React.ReactElement {
  const navigate = useNavigate();
  const user = useStore((s) => s.user);
  const clearAuth = useStore((s) => s.clearAuth);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const storageGB = user ? (user.storage_used_bytes / 1e9).toFixed(1) : "0.0";
  const quotaGB = user?.storage_quota_bytes
    ? (user.storage_quota_bytes / 1e9).toFixed(0)
    : String(DEFAULT_QUOTA_GB);

  // Close dropdown on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent): void {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  function handleSignOut(): void {
    setOpen(false);
    authLogout()
      .catch(() => undefined)
      .finally(() => {
        clearAuth();
        navigate("/login");
      });
  }

  function handleChangePassword(): void {
    setOpen(false);
    onChangePassword?.();
  }

  return (
    <header style={HEADER}>
      <Link to="/projects" style={LOGO}>
        ChipAtelier
      </Link>

      {breadcrumbs && <div style={BREADCRUMB_WRAP}>{breadcrumbs}</div>}
      {!breadcrumbs && <div style={{ flex: 1 }} />}

      {actions}

      <span style={STORAGE_CHIP}>{storageGB} GB of {quotaGB} GB used</span>

      <div ref={menuRef} style={{ position: "relative" }}>
        <button style={DROPDOWN_BTN} onClick={() => setOpen((v) => !v)}>
          {user?.display_name ?? user?.email ?? "Account"}
        </button>

        {open && (
          <div style={DROPDOWN_MENU}>
            <div style={DROPDOWN_EMAIL}>{user?.email}</div>
            <button
              style={DROPDOWN_ITEM}
              onClick={handleChangePassword}
            >
              Change Password
            </button>
            <div style={DROPDOWN_DIVIDER} />
            <button style={{ ...DROPDOWN_ITEM, color: "#f85149" }} onClick={handleSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
