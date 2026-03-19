import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LoginPage from "./LoginPage";

vi.mock("../api/auth", () => ({
  login: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock("../store", () => ({
  useStore: (selector: (s: unknown) => unknown) =>
    selector({ setAuth: vi.fn() }),
}));

describe("LoginPage", () => {
  it("renders Forgot your password link", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Forgot your password/i)).toBeTruthy();
  });

  it("shows flash message when location state contains flash", () => {
    render(
      <MemoryRouter
        initialEntries={[{ pathname: "/login", state: { flash: "Password reset successfully. Please sign in." } }]}
      >
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText(/Password reset successfully/i)).toBeTruthy();
  });

  it("does not show flash banner without location state", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.queryByText(/Password reset successfully/i)).toBeNull();
  });
});
