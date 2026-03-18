import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AppHeader } from "./AppHeader";

// Stub logout so tests don't hit the network
vi.mock("../../api/auth", () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}));

// Minimal Zustand store mock
vi.mock("../../store", () => ({
  useStore: (selector: (s: unknown) => unknown) => {
    const state = {
      user: {
        email: "test@example.com",
        display_name: "Test User",
        storage_used_bytes: 500_000_000,
        storage_quota_bytes: null,
      },
      clearAuth: vi.fn(),
    };
    return selector(state);
  },
}));

function renderHeader(props = {}) {
  return render(
    <MemoryRouter>
      <AppHeader {...props} />
    </MemoryRouter>
  );
}

describe("AppHeader", () => {
  it("shows the ChipAtelier branding", () => {
    renderHeader();
    expect(screen.getByText("ChipAtelier")).toBeTruthy();
  });

  it("shows storage usage chip with used / quota", () => {
    renderHeader();
    // quota is null → falls back to DEFAULT_QUOTA_GB constant
    expect(screen.getByText(/0\.5 GB of \d+ GB used/)).toBeTruthy();
  });

  it("shows user display name in dropdown trigger", () => {
    renderHeader();
    expect(screen.getByText("Test User")).toBeTruthy();
  });

  it("dropdown opens on click and shows email, Change Password, Sign out", () => {
    renderHeader();
    fireEvent.click(screen.getByText("Test User"));
    expect(screen.getByText("test@example.com")).toBeTruthy();
    expect(screen.getByText("Change Password")).toBeTruthy();
    expect(screen.getByText("Sign out")).toBeTruthy();
  });

  it("renders breadcrumbs slot when provided", () => {
    renderHeader({ breadcrumbs: <span>Projects &gt; my-design</span> });
    expect(screen.getByText(/Projects/)).toBeTruthy();
  });

  it("renders actions slot when provided", () => {
    renderHeader({ actions: <button>New Project</button> });
    expect(screen.getByText("New Project")).toBeTruthy();
  });

  it("calls onChangePassword when Change Password item is clicked", () => {
    const onChangePassword = vi.fn();
    renderHeader({ onChangePassword });
    fireEvent.click(screen.getByText("Test User"));
    fireEvent.click(screen.getByText("Change Password"));
    expect(onChangePassword).toHaveBeenCalledTimes(1);
  });
});
