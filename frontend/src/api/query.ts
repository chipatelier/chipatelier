import { apiClient } from "./client";

export interface InspectElement {
  name: string;
  master: string | null;
  nets: string[];
}

export interface InspectResponse {
  elements: InspectElement[];
  run_id: string;
  x_um: number;
  y_um: number;
}

export async function clickToInspect(
  runId: string,
  xUm: number,
  yUm: number,
  toleranceUm: number = 1.0,
): Promise<InspectResponse> {
  const resp = await apiClient.get(`/query/${runId}`, {
    params: { x_um: xUm, y_um: yUm, tolerance_um: toleranceUm },
  });
  return resp.data;
}
