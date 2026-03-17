import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { RunComparison } from "./RunComparison";

describe("RunComparison", () => {
  it("highlights better WNS value in green and worse in red", () => {
    const runs = [
      {
        id: "r1",
        created_at: "2026-01-01T00:00:00Z",
        ppa: { worst_negative_slack: -0.1 },
        config: {},
      },
      {
        id: "r2",
        created_at: "2026-01-02T00:00:00Z",
        ppa: { worst_negative_slack: -0.5 },
        config: {},
      },
    ];
    const { container } = render(<RunComparison runs={runs} />);
    // r1 has better WNS (-0.1 > -0.5 → higher is better), should have green class
    // r2 has worse WNS, should have red class
    const cells = container.querySelectorAll("[data-metric='worst_negative_slack']");
    expect(cells.length).toBe(2);
    expect(cells[0].getAttribute("data-color")).toBe("green");
    expect(cells[1].getAttribute("data-color")).toBe("red");
  });

  it("renders config differences section for params that differ", () => {
    const runs = [
      {
        id: "r1",
        created_at: "2026-01-01T00:00:00Z",
        ppa: {},
        config: { CLOCK_PERIOD: "10", CORE_UTILIZATION: "40" },
      },
      {
        id: "r2",
        created_at: "2026-01-02T00:00:00Z",
        ppa: {},
        config: { CLOCK_PERIOD: "8", CORE_UTILIZATION: "40" },
      },
    ];
    const { getByText } = render(<RunComparison runs={runs} />);
    // CLOCK_PERIOD differs → should appear in config diff section
    expect(getByText("CLOCK_PERIOD")).toBeTruthy();
    // CORE_UTILIZATION is same → should NOT appear in diff section
    // (It appears in config diff section only if different)
    const allCoreUtil = document.querySelectorAll("[data-config-key='CORE_UTILIZATION']");
    expect(allCoreUtil.length).toBe(0);
  });

  it("shows empty state when fewer than 2 runs provided", () => {
    const { getByText } = render(<RunComparison runs={[]} />);
    expect(getByText(/select.*run/i)).toBeTruthy();
  });
});
