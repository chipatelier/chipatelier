import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ChangePasswordModal } from "./ChangePasswordModal";

vi.mock("../../api/auth", () => ({
  changePassword: vi.fn(),
}));

import { changePassword } from "../../api/auth";

describe("ChangePasswordModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <ChangePasswordModal open={false} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders form fields when open", () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    expect(screen.getByLabelText("Current password")).toBeTruthy();
    expect(screen.getByLabelText("New password")).toBeTruthy();
    expect(screen.getByLabelText("Confirm new password")).toBeTruthy();
  });

  it("shows error when new password is shorter than 8 chars", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "current1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "short" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "short" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/at least 8/i)).toBeTruthy();
    });
  });

  it("shows error when passwords do not match", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "current1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpassword1" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "differentpass1" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/do not match/i)).toBeTruthy();
    });
  });

  it("shows error when new equals current", async () => {
    render(<ChangePasswordModal open={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "samepass1" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "samepass1" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "samepass1" } });
    fireEvent.click(screen.getByText("Save"));
    await waitFor(() => {
      expect(screen.getByText(/must differ/i)).toBeTruthy();
    });
  });

  it("calls changePassword API, shows success, then calls onClose after 1.5 s", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const onClose = vi.fn();
    vi.mocked(changePassword).mockResolvedValueOnce(undefined);

    render(<ChangePasswordModal open={true} onClose={onClose} />);
    fireEvent.change(screen.getByLabelText("Current password"), { target: { value: "oldpass1!" } });
    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass1!" } });
    fireEvent.change(screen.getByLabelText("Confirm new password"), { target: { value: "newpass1!" } });

    await act(async () => {
      fireEvent.click(screen.getByText("Save"));
    });

    expect(changePassword).toHaveBeenCalledWith("oldpass1!", "newpass1!");
    expect(screen.getByText(/password changed/i)).toBeTruthy();

    // Advance past the 1.5 s auto-close timer
    act(() => {
      vi.advanceTimersByTime(2000);
    });
    expect(onClose).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });
});
