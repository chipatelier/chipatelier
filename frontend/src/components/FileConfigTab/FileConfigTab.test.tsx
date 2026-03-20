import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import FileConfigTab from "./FileConfigTab";
import * as projectsApi from "../../api/projects";

vi.mock("@monaco-editor/react", () => ({
  default: ({ value, onChange }: any) => (
    <textarea data-testid="monaco" value={value ?? ""} onChange={(e) => onChange?.(e.target.value)} />
  ),
}));

const baseProject = {
  id: "p1", name: "test", pdk: "sky130hd",
  storage_bytes: 0, created_at: "2026-01-01T00:00:00Z",
  run_count: 0, config_version: 0, verilog_version: 0,
  latest_source_path: null,
};

describe("FileConfigTab", () => {
  it("shows empty state when no verilog uploaded", async () => {
    vi.spyOn(projectsApi, "getProjectSource").mockRejectedValue({ response: { status: 404 } });
    vi.spyOn(projectsApi, "getProjectConfig").mockResolvedValue({ content: "", version: 0 });
    render(<FileConfigTab project={baseProject} onProjectUpdate={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/no verilog uploaded yet/i)).toBeInTheDocument());
  });

  it("shows unsaved indicator on config edit", async () => {
    vi.spyOn(projectsApi, "getProjectSource").mockRejectedValue({ response: { status: 404 } });
    vi.spyOn(projectsApi, "getProjectConfig").mockResolvedValue({ content: "CLOCK_PERIOD = 10", version: 1 });
    render(<FileConfigTab project={{ ...baseProject, config_version: 1 }} onProjectUpdate={vi.fn()} />);
    await waitFor(() => screen.getByTestId("monaco"));
    fireEvent.change(screen.getByTestId("monaco"), { target: { value: "CLOCK_PERIOD = 8" } });
    expect(screen.getByText(/unsaved/i)).toBeInTheDocument();
  });

  it("clears unsaved indicator after save", async () => {
    vi.spyOn(projectsApi, "getProjectSource").mockRejectedValue({ response: { status: 404 } });
    vi.spyOn(projectsApi, "getProjectConfig").mockResolvedValue({ content: "CLOCK_PERIOD = 10", version: 1 });
    const mockUpdate = vi.spyOn(projectsApi, "updateProject").mockResolvedValue({ ...baseProject, config_version: 2 });
    const mockRefetch = vi.fn();
    render(<FileConfigTab project={{ ...baseProject, config_version: 1 }} onProjectUpdate={mockRefetch} />);
    await waitFor(() => screen.getByTestId("monaco"));
    fireEvent.change(screen.getByTestId("monaco"), { target: { value: "CLOCK_PERIOD = 8" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith("p1", { config_mk: "CLOCK_PERIOD = 8" }));
    await waitFor(() => expect(screen.queryByText(/unsaved/i)).not.toBeInTheDocument());
  });
});
