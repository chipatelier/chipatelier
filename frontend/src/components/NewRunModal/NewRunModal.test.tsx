import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import NewRunModal from "./NewRunModal";
import * as jobsApi from "../../api/jobs";

const baseProject = {
  id: "proj-1", name: "test", pdk: "sky130hd",
  storage_bytes: 0, created_at: "2026-01-01T00:00:00Z",
  run_count: 2, config_version: 1, verilog_version: 1,
  latest_source_path: "projects/proj-1/verilog/v1",
};

describe("NewRunModal", () => {
  it("is disabled when verilog_version is 0", () => {
    render(
      <NewRunModal
        project={{ ...baseProject, verilog_version: 0 }}
        hasActiveRun={false}
        onSubmitted={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /new run/i })).toBeDisabled();
  });

  it("is disabled when config_version is 0", () => {
    render(
      <NewRunModal
        project={{ ...baseProject, config_version: 0 }}
        hasActiveRun={false}
        onSubmitted={vi.fn()}
      />
    );
    expect(screen.getByRole("button", { name: /new run/i })).toBeDisabled();
  });

  it("submits with latest_source_path as source_path", async () => {
    const mockSubmit = vi.spyOn(jobsApi, "submitJob").mockResolvedValue({
      run_id: "run-1", status: "queued", queue_priority: "normal",
    });
    render(
      <NewRunModal project={baseProject} hasActiveRun={false} onSubmitted={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /new run/i }));
    fireEvent.click(screen.getByRole("button", { name: /submit run/i }));
    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ source_path: "projects/proj-1/verilog/v1" })
      );
    });
  });

  it("omits config_overrides when all override fields empty", async () => {
    const mockSubmit = vi.spyOn(jobsApi, "submitJob").mockResolvedValue({
      run_id: "run-1", status: "queued", queue_priority: "normal",
    });
    render(
      <NewRunModal project={baseProject} hasActiveRun={false} onSubmitted={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /new run/i }));
    fireEvent.click(screen.getByRole("button", { name: /submit run/i }));
    await waitFor(() => {
      const call = mockSubmit.mock.calls[0][0];
      expect(call.config_overrides).toBeUndefined();
    });
  });

  it("shows GDS label for finish stage", () => {
    render(
      <NewRunModal project={baseProject} hasActiveRun={false} onSubmitted={vi.fn()} />
    );
    fireEvent.click(screen.getByRole("button", { name: /new run/i }));
    expect(screen.getByText(/gds.*full flow/i)).toBeInTheDocument();
  });
});
