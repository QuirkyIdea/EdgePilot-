import React from "react";

export interface Cfg {
  seed: number;
  n_devices: number;
  n_edges: number;
  sim_time: number;
  task_rate: number;
  telemetry_budget: number;
  load_mean: number;
  cloud_base_latency: number;
  deadline_slack_mean: number;
}

export const DEFAULT_CFG: Cfg = {
  seed: 1,
  n_devices: 30,
  n_edges: 5,
  sim_time: 150,
  task_rate: 6,
  telemetry_budget: 0.3,
  load_mean: 0.5,
  cloud_base_latency: 0.1,
  deadline_slack_mean: 2.2,
};

const FIELDS: { key: keyof Cfg; label: string; step?: number; min?: number }[] = [
  { key: "seed", label: "Random seed", step: 1, min: 0 },
  { key: "n_devices", label: "Devices (20–50)", step: 1, min: 1 },
  { key: "n_edges", label: "Edge servers (3–10)", step: 1, min: 0 },
  { key: "sim_time", label: "Sim time (s)", step: 10, min: 20 },
  { key: "task_rate", label: "Task rate (/s)", step: 0.5, min: 0.1 },
  { key: "telemetry_budget", label: "Telemetry budget (norm.)", step: 0.05, min: 0 },
  { key: "load_mean", label: "Mean edge load", step: 0.05, min: 0 },
  { key: "cloud_base_latency", label: "Cloud latency (s)", step: 0.01, min: 0 },
  { key: "deadline_slack_mean", label: "Deadline slack", step: 0.1, min: 1 },
];

export function ConfigPanel({
  cfg,
  setCfg,
  presets,
  onPreset,
}: {
  cfg: Cfg;
  setCfg: (c: Cfg) => void;
  presets: string[];
  onPreset: (name: string) => void;
}) {
  return (
    <div className="card">
      <h3>Simulation configuration</h3>
      {presets.length > 0 && (
        <label className="field">
          Scenario preset
          <select onChange={(e) => e.target.value && onPreset(e.target.value)} defaultValue="">
            <option value="">— custom —</option>
            {presets.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
      )}
      {FIELDS.map((f) => (
        <label className="field" key={f.key}>
          {f.label}
          <input
            type="number"
            step={f.step}
            min={f.min}
            value={cfg[f.key]}
            onChange={(e) => setCfg({ ...cfg, [f.key]: Number(e.target.value) })}
          />
        </label>
      ))}
    </div>
  );
}
