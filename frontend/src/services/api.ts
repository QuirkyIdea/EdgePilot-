// Typed client for the EdgePilot FastAPI backend.
export interface Summary {
  [k: string]: number;
}
export interface SchedulerInfo {
  key: string;
  label: string;
  uses_telemetry: boolean;
}
export interface SimResult {
  scheduler: string;
  scenario: string;
  seed: number;
  summary: Summary;
  timeseries?: Record<string, number[]>;
}
export interface CompareRow {
  scheduler: string;
  label: string;
  [k: string]: number | string;
}
export interface TopologyNode {
  id: string;
  kind: "cloud" | "edge" | "device";
  capacity: number;
  u_true?: number;
}
export interface TopologyLink {
  source: string;
  target: string;
  bandwidth: number;
  latency: number;
}

const base = "";

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(base + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path}: ${r.status} ${await r.text()}`);
  return r.json();
}
async function get<T>(path: string): Promise<T> {
  const r = await fetch(base + path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export const api = {
  health: () => get<{ status: string }>("/api/health"),
  schedulers: () => get<SchedulerInfo[]>("/api/schedulers"),
  scenarios: () =>
    get<{ default: Record<string, number>; presets: Record<string, Record<string, number>> }>(
      "/api/scenarios"
    ),
  topology: (seed: number, nd: number, ne: number) =>
    get<{ nodes: TopologyNode[]; links: TopologyLink[] }>(
      `/api/topology?seed=${seed}&n_devices=${nd}&n_edges=${ne}`
    ),
  simulate: (scheduler: string, config: Record<string, number>, timeseries = true) =>
    post<SimResult>("/api/simulate", { scheduler, config, timeseries }),
  compare: (schedulers: string[], config: Record<string, number>) =>
    post<{ config: Record<string, number>; results: CompareRow[] }>("/api/compare", {
      schedulers,
      config,
    }),
  experiment: (kind: string, seeds: number, config: Record<string, number>) =>
    post<{ kind: string; xname: string | null; records: any[] }>("/api/experiment", {
      kind,
      seeds,
      config,
    }),
};
