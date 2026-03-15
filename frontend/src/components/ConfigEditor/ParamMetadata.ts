export interface ParamMeta {
  key: string;
  label: string;
  min: number;
  max: number;
  unit: string;
  description: string;
}

export const CURATED_PARAMS: ParamMeta[] = [
  {
    key: "CORE_UTILIZATION",
    label: "Core Utilization",
    min: 20,
    max: 80,
    unit: "%",
    description: "Percentage of core area filled with standard cells",
  },
  {
    key: "PLACE_DENSITY",
    label: "Place Density",
    min: 0.3,
    max: 0.9,
    unit: "",
    description: "Target cell placement density (0.3–0.9); higher = more congested",
  },
  {
    key: "TNS_END_PERCENT",
    label: "TNS End Percent",
    min: 0,
    max: 100,
    unit: "%",
    description: "Percentage of failing paths to fix before stopping timing repair",
  },
  {
    key: "CLOCK_PERIOD",
    label: "Clock Period",
    min: 1,
    max: 100,
    unit: "ns",
    description: "Target clock period in nanoseconds",
  },
  {
    key: "CORE_ASPECT_RATIO",
    label: "Core Aspect Ratio",
    min: 0.5,
    max: 2.0,
    unit: "",
    description: "Ratio of core height to core width (1.0 = square)",
  },
  {
    key: "CORE_MARGIN",
    label: "Core Margin",
    min: 1,
    max: 20,
    unit: "\u00b5m",
    description: "Margin between core area boundary and die edge",
  },
  {
    key: "SETUP_SLACK_MARGIN",
    label: "Setup Slack Margin",
    min: 0,
    max: 1,
    unit: "ns",
    description: "Additional setup slack margin added to timing constraints",
  },
];
