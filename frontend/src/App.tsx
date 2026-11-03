import React, { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  Cell,
} from "recharts";
import { api, CompareRow, SchedulerInfo, SimResult, TopologyNode, TopologyLink } from "./services/api";
import { ConfigPanel, Cfg, DEFAULT_CFG } from "./components/ConfigPanel";
import { TopologyView } from "./components/TopologyView";

const COLORS: Record<string, string> = {
  local_only: "#8c8c8c",
  cloud_only: "#4c72b0",
  random: "#c44e52",
  nearest_edge: "#937860",
  lowest_est_time: "#dd8452",
  periodic_telemetry: "#55a868",
  freshness_aware: "#8172b3",
  abvi_edge: "#d62728",
};

type Tab = "simulate" | "compare" | "experiment";

export default function App() {
  const [tab, setTab] = useState<Tab>("compare");
  const [cfg, setCfg] = useState<Cfg>(DEFAULT_CFG);
  const [presets, setPresets] = useState<Record<string, Record<string, number>>>({});
  const [scheds, setScheds] = useState<SchedulerInfo[]>([]);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    api.schedulers().then(setScheds).catch((e) => setErr(String(e)));
    api
      .scenarios()
      .then((s) => setPresets(s.presets))
      .catch((e) => setErr(String(e)));
  }, []);

  const applyPreset = (name: string) => {
    const p = presets[name];
    if (!p) return;
    setCfg({
      ...cfg,
      seed: p.seed ?? cfg.seed,
      n_devices: p.n_devices ?? cfg.n_devices,
      n_edges: p.n_edges ?? cfg.n_edges,
      task_rate: p.task_rate ?? cfg.task_rate,
      telemetry_budget: p.telemetry_budget ?? cfg.telemetry_budget,
      load_mean: p.load_mean ?? cfg.load_mean,
      cloud_base_latency: p.cloud_base_latency ?? cfg.cloud_base_latency,
      deadline_slack_mean: p.deadline_slack_mean ?? cfg.deadline_slack_mean,
    });
  };

  return (
    <div className="app">
      <header>
        <h1>EdgePilot</h1>
        <p className="sub">
          Adaptive Telemetry-Budgeted Intelligent Task Offloading — research dashboard
          (all charts render live simulation output)
        </p>
      </header>

      <div className="tabs">
        <button className={tab === "compare" ? "active" : ""} onClick={() => setTab("compare")}>
          Algorithm comparison
        </button>
        <button className={tab === "simulate" ? "active" : ""} onClick={() => setTab("simulate")}>
          Single run + topology
        </button>
        <button className={tab === "experiment" ? "active" : ""} onClick={() => setTab("experiment")}>
          Experiments
        </button>
      </div>

      {err && <div className="err">Backend error: {err} — is the API running on :8000?</div>}

      <div className="grid cols-2">
        <ConfigPanel
          cfg={cfg}
          setCfg={setCfg}
          presets={Object.keys(presets)}
          onPreset={applyPreset}
        />
        <div>
          {tab === "compare" && <ComparePage cfg={cfg} scheds={scheds} />}
          {tab === "simulate" && <SimulatePage cfg={cfg} scheds={scheds} />}
          {tab === "experiment" && <ExperimentPage cfg={cfg} />}
        </div>
      </div>
    </div>
  );
}

function fmt(x: number | string | undefined | null, d = 3) {
  return x === undefined || x === null || x === "" ? "–" : Number(x).toFixed(d);
}

// ---------------------------------------------------------------- Compare
function ComparePage({ cfg, scheds }: { cfg: Cfg; scheds: SchedulerInfo[] }) {
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const run = () => {
    setLoading(true);
    setErr("");
    api
      .compare(scheds.map((s) => s.key), cfg as any)
      .then((r) => setRows(r.results))
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    if (scheds.length) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheds.length]);

  const metrics: { k: string; label: string }[] = [
    { k: "avg_completion", label: "Avg completion (s)" },
    { k: "p95_completion", label: "p95 completion (s)" },
    { k: "deadline_violation_rate", label: "Deadline violations" },
    { k: "avg_regret", label: "Avg regret (s)" },
  ];

  const abvi = rows.find((r) => r.scheduler === "abvi_edge");

  return (
    <>
      <div className="card">
        <h3>Algorithm comparison — identical workload, topology & seed</h3>
        <button className="btn" onClick={run} disabled={loading}>
          {loading ? "Running simulations…" : "Run comparison"}
        </button>
        {err && <div className="err">{err}</div>}
      </div>

      {abvi && (
        <div className="grid cols-4" style={{ marginTop: 14 }}>
          <Kpi label="ABVI completion" value={fmt(abvi.avg_completion)} accent />
          <Kpi label="ABVI violations" value={fmt(abvi.deadline_violation_rate)} accent />
          <Kpi label="ABVI regret" value={fmt(abvi.avg_regret, 4)} accent />
          <Kpi label="Telemetry probes" value={fmt(abvi.telemetry_requests, 0)} />
        </div>
      )}

      {metrics.map((m) => (
        <div className="card" key={m.k} style={{ marginTop: 14 }}>
          <h3>{m.label}</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={rows.map((r) => ({ name: r.label, v: r[m.k], key: r.scheduler }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#92a0b4" }} interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11, fill: "#92a0b4" }} />
              <Tooltip contentStyle={{ background: "#19202e", border: "1px solid #2d3a4f" }} />
              <Bar dataKey="v">
                {rows.map((r) => (
                  <Cell key={r.scheduler} fill={COLORS[r.scheduler] || "#888"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}

      {rows.length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>Full metric table</h3>
          <table>
            <thead>
              <tr>
                <th>Scheduler</th>
                <th>Compl.</th>
                <th>p95</th>
                <th>Viol.</th>
                <th>Regret</th>
                <th>Energy</th>
                <th>Probes</th>
                <th>Mon.OH</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.scheduler} className={r.scheduler === "abvi_edge" ? "ours" : ""}>
                  <td>{r.label}</td>
                  <td>{fmt(r.avg_completion)}</td>
                  <td>{fmt(r.p95_completion)}</td>
                  <td>{fmt(r.deadline_violation_rate)}</td>
                  <td>{fmt(r.avg_regret, 4)}</td>
                  <td>{fmt(r.avg_energy)}</td>
                  <td>{fmt(r.telemetry_requests, 0)}</td>
                  <td>{fmt(r.monitoring_overhead, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------- Simulate
function SimulatePage({ cfg, scheds }: { cfg: Cfg; scheds: SchedulerInfo[] }) {
  const [scheduler, setScheduler] = useState("abvi_edge");
  const [res, setRes] = useState<SimResult | null>(null);
  const [topo, setTopo] = useState<{ nodes: TopologyNode[]; links: TopologyLink[] } | null>(null);
  const [loading, setLoading] = useState(false);

  const run = () => {
    setLoading(true);
    Promise.all([
      api.simulate(scheduler, cfg as any, true),
      api.topology(cfg.seed, Math.min(cfg.n_devices, 16), cfg.n_edges),
    ])
      .then(([s, t]) => {
        setRes(s);
        setTopo(t);
      })
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    if (scheds.length) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scheds.length]);

  const ts =
    res?.timeseries?.time?.map((t, i) => ({
      t: Number(t.toFixed(1)),
      budget: res.timeseries!.budget_frac_left[i],
      edge_util: res.timeseries!.edge_util[i],
      probes: res.timeseries!.probes_cum[i],
      regret: res.timeseries!.regret[i],
    })) || [];

  const s = res?.summary;

  return (
    <>
      <div className="card">
        <h3>Single simulation run</h3>
        <label className="field">
          Scheduler
          <select value={scheduler} onChange={(e) => setScheduler(e.target.value)}>
            {scheds.map((x) => (
              <option key={x.key} value={x.key}>
                {x.label}
              </option>
            ))}
          </select>
        </label>
        <button className="btn secondary" onClick={run} disabled={loading}>
          {loading ? "Running…" : "Run simulation"}
        </button>
      </div>

      {s && (
        <div className="grid cols-4" style={{ marginTop: 14 }}>
          <Kpi label="Avg completion (s)" value={fmt(s.avg_completion)} />
          <Kpi label="Deadline violations" value={fmt(s.deadline_violation_rate)} />
          <Kpi label="Avg info age (s)" value={fmt(s.avg_info_age, 2)} />
          <Kpi label="Telemetry probes" value={fmt(s.telemetry_requests, 0)} />
          <Kpi label="Avg regret (s)" value={fmt(s.avg_regret, 4)} />
          <Kpi label="Avg energy (J)" value={fmt(s.avg_energy)} />
          <Kpi label="Throughput (/s)" value={fmt(s.throughput, 2)} />
          <Kpi label="Decide time (ms)" value={fmt(s.avg_decision_time_ms, 3)} />
        </div>
      )}

      {topo && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>Network topology (edge load at snapshot)</h3>
          <TopologyView nodes={topo.nodes} links={topo.links} />
        </div>
      )}

      {ts.length > 0 && (
        <>
          <div className="card" style={{ marginTop: 14 }}>
            <h3>Telemetry budget remaining & cumulative probes</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={ts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
                <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#92a0b4" }} />
                <YAxis yAxisId="l" tick={{ fontSize: 11, fill: "#92a0b4" }} />
                <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 11, fill: "#92a0b4" }} />
                <Tooltip contentStyle={{ background: "#19202e", border: "1px solid #2d3a4f" }} />
                <Legend />
                <Line yAxisId="l" dataKey="budget" name="budget frac left" stroke="#55a868" dot={false} />
                <Line yAxisId="r" dataKey="probes" name="probes (cum)" stroke="#d62728" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="card" style={{ marginTop: 14 }}>
            <h3>Mean edge utilization over time</h3>
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={ts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
                <XAxis dataKey="t" tick={{ fontSize: 11, fill: "#92a0b4" }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "#92a0b4" }} />
                <Tooltip contentStyle={{ background: "#19202e", border: "1px solid #2d3a4f" }} />
                <Line dataKey="edge_util" name="edge utilization" stroke="#4c72b0" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </>
  );
}

// ---------------------------------------------------------------- Experiment
function ExperimentPage({ cfg }: { cfg: Cfg }) {
  const [kind, setKind] = useState("budget");
  const [seeds, setSeeds] = useState(5);
  const [data, setData] = useState<any[]>([]);
  const [xname, setXname] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const run = () => {
    setLoading(true);
    setErr("");
    api
      .experiment(kind, seeds, cfg as any)
      .then((r) => {
        setXname(r.xname);
        setData(r.records);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  };

  // Pivot records into chart-friendly series keyed by x, one line per scheduler.
  const scheds = Array.from(new Set(data.map((d) => d.scheduler)));
  const xs = Array.from(new Set(data.map((d) => d.x))).sort((a, b) => a - b);
  const completionData = xs.map((x) => {
    const row: any = { x };
    data
      .filter((d) => d.x === x)
      .forEach((d) => (row[d.scheduler] = d.avg_completion_mean));
    return row;
  });
  const paretoData = scheds.map((s) => ({
    scheduler: s,
    points: data
      .filter((d) => d.scheduler === s)
      .map((d) => ({ x: d.telemetry_norm_mean, y: d.avg_completion_mean })),
  }));

  return (
    <>
      <div className="card">
        <h3>Run a multi-seed experiment (live)</h3>
        <p className="note">
          Runs the selected sweep across {seeds} seeds on the backend and plots mean curves.
          Budget-sweep reproduces the quality-vs-overhead frontier (Experiment B).
        </p>
        <div className="grid cols-3">
          <label className="field">
            Experiment
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="budget">Telemetry budget sweep</option>
              <option value="workload">Workload intensity sweep</option>
              <option value="algorithm">Algorithm comparison</option>
            </select>
          </label>
          <label className="field">
            Seeds
            <input
              type="number"
              min={1}
              max={30}
              value={seeds}
              onChange={(e) => setSeeds(Number(e.target.value))}
            />
          </label>
        </div>
        <button className="btn" onClick={run} disabled={loading}>
          {loading ? "Running experiment…" : "Run experiment"}
        </button>
        {err && <div className="err">{err}</div>}
      </div>

      {xname && completionData.length > 0 && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>Avg completion vs {xname}</h3>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={completionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3a4f" />
              <XAxis dataKey="x" tick={{ fontSize: 11, fill: "#92a0b4" }} />
              <YAxis tick={{ fontSize: 11, fill: "#92a0b4" }} />
              <Tooltip contentStyle={{ background: "#19202e", border: "1px solid #2d3a4f" }} />
              <Legend />
              {scheds.map((s) => (
                <Line key={s} dataKey={s} stroke={COLORS[s] || "#888"} dot={{ r: 3 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {kind === "budget" && paretoData.some((p) => p.points.length) && (
        <div className="card" style={{ marginTop: 14 }}>
          <h3>Quality vs monitoring-overhead frontier</h3>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart>
              <CartesianGrid stroke="#2d3a4f" />
              <XAxis
                type="number"
                dataKey="x"
                name="overhead"
                tick={{ fontSize: 11, fill: "#92a0b4" }}
                label={{ value: "normalized telemetry spend", position: "insideBottom", fill: "#92a0b4", dy: 10 }}
              />
              <YAxis
                type="number"
                dataKey="y"
                name="completion"
                tick={{ fontSize: 11, fill: "#92a0b4" }}
              />
              <Tooltip contentStyle={{ background: "#19202e", border: "1px solid #2d3a4f" }} />
              <Legend />
              {paretoData.map((p) => (
                <Scatter
                  key={p.scheduler}
                  name={p.scheduler}
                  data={p.points.sort((a, b) => a.x - b.x)}
                  line
                  fill={COLORS[p.scheduler] || "#888"}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </>
  );
}

function Kpi({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="kpi">
      <div className="label">{label}</div>
      <div className={"value" + (accent ? " accent" : "")}>{value}</div>
    </div>
  );
}
