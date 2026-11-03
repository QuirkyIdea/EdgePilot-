"""EdgePilot FastAPI backend.

Exposes the simulation platform to the React dashboard:

  GET  /api/health
  GET  /api/schedulers            list scheduler keys + labels
  GET  /api/scenarios             named preset scenarios + default config
  POST /api/simulate              run one scheduler on a scenario (+timeseries)
  POST /api/compare               run several schedulers on the same scenario
  GET  /api/topology              topology (nodes/links) for a scenario
  POST /api/experiment            run a small multi-seed experiment live
  GET  /api/results/{name}        read a precomputed results CSV (if present)

All endpoints return actual simulation output; nothing is hardcoded.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from edgepilot.config import ScenarioConfig, scenario_presets
from edgepilot.simulator import Simulator, run_once
from edgepilot.schedulers import REGISTRY
from edgepilot import experiments as ex
from edgepilot import analysis as an

app = FastAPI(title="EdgePilot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"],
)

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.abspath(os.path.join(HERE, "..", "..", "results"))


# --------------------------------------------------------------- schemas
class SimRequest(BaseModel):
    scheduler: str = "abvi_edge"
    config: Dict[str, Any] = Field(default_factory=dict)
    timeseries: bool = True


class CompareRequest(BaseModel):
    schedulers: List[str] = Field(
        default_factory=lambda: ["cloud_only", "lowest_est_time",
                                 "periodic_telemetry", "freshness_aware", "abvi_edge"])
    config: Dict[str, Any] = Field(default_factory=dict)


class ExperimentRequest(BaseModel):
    kind: str = "budget"            # budget | workload | algorithm
    seeds: int = 5
    config: Dict[str, Any] = Field(default_factory=dict)


def _cfg(overrides: Dict[str, Any]) -> ScenarioConfig:
    base = ScenarioConfig().to_dict()
    base.update({k: v for k, v in overrides.items() if k in base})
    return ScenarioConfig.from_dict(base)


# --------------------------------------------------------------- routes
@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/api/schedulers")
def schedulers():
    return [{"key": k, "label": an.SCHED_LABELS.get(k, k),
             "uses_telemetry": REGISTRY[k].uses_telemetry} for k in REGISTRY]


@app.get("/api/scenarios")
def scenarios():
    presets = scenario_presets()
    return {
        "default": ScenarioConfig().to_dict(),
        "presets": {name: cfg.to_dict() for name, cfg in presets.items()},
    }


@app.get("/api/topology")
def topology(seed: int = 1, n_devices: int = 12, n_edges: int = 5):
    cfg = _cfg({"seed": seed, "n_devices": n_devices, "n_edges": n_edges,
                "sim_time": 10.0})
    from edgepilot.environment import Environment
    env = Environment(cfg)
    nodes = [{"id": "cloud", "kind": "cloud", "capacity": env.cloud.capacity}]
    for e in env.edges:
        nodes.append({"id": e.loc_id, "kind": "edge", "capacity": e.capacity,
                      "u_true": e.u_true})
    for d in env.devices:
        nodes.append({"id": d.loc_id, "kind": "device", "capacity": d.capacity})
    links = []
    for (dev, loc_id), link in env.links.items():
        links.append({"source": f"local:{dev}", "target": loc_id,
                      "bandwidth": round(link.base_bw, 1),
                      "latency": round(link.base_latency, 4)})
    return {"nodes": nodes, "links": links}


@app.post("/api/simulate")
def simulate(req: SimRequest):
    if req.scheduler not in REGISTRY:
        raise HTTPException(400, f"unknown scheduler '{req.scheduler}'")
    cfg = _cfg(req.config)
    res = run_once(cfg, req.scheduler, collect_timeseries=req.timeseries)
    out = {"scheduler": res.scheduler, "scenario": res.scenario,
           "seed": res.seed, "summary": res.summary}
    if req.timeseries:
        out["timeseries"] = res.timeseries
    return out


@app.post("/api/compare")
def compare(req: CompareRequest):
    cfg = _cfg(req.config)
    rows = []
    for sch in req.schedulers:
        if sch not in REGISTRY:
            raise HTTPException(400, f"unknown scheduler '{sch}'")
        res = run_once(cfg, sch)
        rows.append({"scheduler": sch, "label": an.SCHED_LABELS.get(sch, sch),
                     **res.summary})
    return {"config": cfg.to_dict(), "results": rows}


@app.post("/api/experiment")
def experiment(req: ExperimentRequest):
    seeds = list(range(1, max(1, min(req.seeds, 30)) + 1))
    base = _cfg(req.config).to_dict()
    base["sim_time"] = min(base.get("sim_time", 150.0), 200.0)

    if req.kind == "budget":
        xs = [0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
        scheds = ["lowest_est_time", "periodic_telemetry", "freshness_aware", "abvi_edge"]
        xname = "telemetry_budget"
    elif req.kind == "workload":
        xs = [3.0, 6.0, 9.0, 12.0]
        scheds = ["cloud_only", "periodic_telemetry", "freshness_aware", "abvi_edge"]
        xname = "task_rate"
    else:  # algorithm
        xs = [None]
        scheds = ex.ALL_SCHEDULERS
        xname = None

    jobs: List[ex.Job] = []
    for s in seeds:
        for x in xs:
            cfg = dict(base); cfg["seed"] = s
            if xname:
                cfg[xname] = x
            for sch in scheds:
                jobs.append(ex.Job(sch, cfg, labels=(
                    {"x": x, "xname": xname} if xname else {})))
    df = ex.run_jobs(jobs, parallel=True)

    metrics = ["avg_completion", "deadline_violation_rate", "avg_regret",
               "telemetry_requests", "telemetry_norm", "avg_energy", "p95_completion"]
    group = ["scheduler", "x"] if xname else ["scheduler"]
    agg = an.aggregate(df, group, metrics)
    return {"kind": req.kind, "xname": xname,
            "records": agg.replace({np.nan: None}).to_dict(orient="records")}


@app.get("/api/results/{name}")
def results(name: str):
    safe = name.replace("..", "").strip("/\\")
    for sub in ("processed", "raw"):
        path = os.path.join(RESULTS, sub, safe)
        if os.path.exists(path) and path.endswith(".csv"):
            df = pd.read_csv(path)
            return {"name": safe, "rows": df.replace({np.nan: None})
                    .to_dict(orient="records")}
    raise HTTPException(404, f"result '{name}' not found")


@app.get("/api/results")
def list_results():
    out = {}
    for sub in ("processed", "raw"):
        d = os.path.join(RESULTS, sub)
        out[sub] = sorted(f for f in os.listdir(d)) if os.path.isdir(d) else []
    return out
