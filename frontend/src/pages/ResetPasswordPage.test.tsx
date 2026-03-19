import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ResetPasswordPage from "./ResetPasswordPage";

vi.mock("../api/auth", () => ({
  resetPassword: vi.fn(),
}));

import { resetPassword } from "../api/auth";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/reset-password"]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResetPasswordPage", () => {
  it("renders email, token, and new password fields", () => {
    renderPage();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Reset token")).toBeTruthy();
    expect(screen.getByLabelText("New password")).toBeTruthy();
  });

  it("renders link back to login", () => {
    renderPage();
    expect(screen.getByText(/Back to sign in/i)).toBeTruthy();
  });

  it("shows error on API failure", async () => {
    vi.mocked(resetPassword).mockRejectedValueOnce({
      response: { data: { detail: "Invalid or expired reset token" } },
    });
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText("Reset token"), { target: { value: "ABCD1234" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.click(screen.getByText("Reset password"));
    await waitFor(() => {
      expect(screen.getByText(/Invalid or expired reset token/i)).toBeTruthy();
    });
  });

  it("navigates to /login with flash on success", async () => {
    vi.mocked(resetPassword).mockResolvedValueOnce(undefined);
    renderPage();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "u@example.com" } });
    fireEvent.change(screen.getByLabelText("Reset token"), { target: { value: "ABCD1234" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.click(screen.getByText("Reset password"));
    await waitFor(() => {
      expect(screen.getByText("Login Page")).toBeTruthy();
    });
  });
});
