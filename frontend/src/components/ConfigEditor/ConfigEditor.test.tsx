import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConfigEditor } from "./ConfigEditor";

// Mock Monaco to avoid heavy worker setup in tests
vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => (
    <div data-testid="monaco-editor">{value}</div>
  ),
}));

describe("ConfigEditor", () => {
  const defaultProps = {
    configContent: "export CORE_UTILIZATION = 40\nexport CLOCK_PERIOD = 10",
    onChange: vi.fn(),
  };

  it("form/raw toggle switches between modes", () => {
    render(<ConfigEditor {...defaultProps} />);
    // Default is form mode — monaco should not be visible
    expect(screen.queryByTestId("monaco-editor")).toBeNull();
    // Click Raw button
    fireEvent.click(screen.getByText("Raw"));
    expect(screen.getByTestId("monaco-editor")).toBeTruthy();
    // Click Form button
    fireEvent.click(screen.getByText("Form"));
    expect(screen.queryByTestId("monaco-editor")).toBeNull();
  });

  it("locked params show Locked by instructor badge", () => {
    render(
      <ConfigEditor
        {...defaultProps}
        lockedParams={{ CLOCK_PERIOD: "10" }}
      />
    );
    expect(screen.getByText("Locked by instructor")).toBeTruthy();
  });

  it("locked param input is disabled", () => {
    render(
      <ConfigEditor
        {...defaultProps}
        lockedParams={{ CLOCK_PERIOD: "10" }}
      />
    );
    const input = screen.getByLabelText("Clock Period") as HTMLInputElement;
    expect(input.disabled).toBe(true);
  });

  it("standalone mode shows all curated params with no locked params", () => {
    render(<ConfigEditor {...defaultProps} />);
    // All 7 curated params should appear
    expect(screen.getByLabelText("Core Utilization")).toBeTruthy();
    expect(screen.getByLabelText("Clock Period")).toBeTruthy();
    // No locked badge
    expect(screen.queryByText("Locked by instructor")).toBeNull();
  });
});
