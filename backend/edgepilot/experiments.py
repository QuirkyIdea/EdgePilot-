"""Experiment harness: multi-seed runs, grids, and parallel execution.

A *job* is a fully-specified single run (scheduler key + scenario config dict +
optional scheduler kwargs + label columns). Jobs are pickled to worker
processes so experiments run in parallel. All randomness is seed-driven, so
results are reproducible regardless of execution order or parallelism.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import concurrent.futures as cf
import os

import pandas as pd

from .config import ScenarioConfig
from .simulator import run_once


@dataclass
class Job:
    scheduler: str
    cfg: Dict[str, Any]
    scheduler_kwargs: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, Any] = field(default_factory=dict)


def _run_job(job: Job) -> Dict[str, Any]:
    cfg = ScenarioConfig.from_dict(job.cfg)
    # ABVI ablation kwargs are passed through as ABVIParams.
    skwargs = dict(job.scheduler_kwargs)
    if job.scheduler == "abvi_edge" and "params" in skwargs:
        from .schedulers.abvi import ABVIParams
        skwargs["params"] = ABVIParams(**skwargs["params"])
    res = run_once(cfg, job.scheduler, skwargs)
    row = {"scheduler": job.scheduler, "scenario": cfg.name, "seed": cfg.seed}
    row.update(job.labels)
    row.update(res.summary)
    return row


def run_jobs(jobs: List[Job], parallel: bool = True,
             max_workers: Optional[int] = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    if parallel and len(jobs) > 1:
        workers = max_workers or max(1, (os.cpu_count() or 2) - 1)
        with cf.ProcessPoolExecutor(max_workers=workers) as ex:
            for row in ex.map(_run_job, jobs):
                rows.append(row)
    else:
        for job in jobs:
            rows.append(_run_job(job))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Experiment builders -- each returns a list of Jobs.
# --------------------------------------------------------------------------
ALL_SCHEDULERS = [
    "local_only", "cloud_only", "random", "nearest_edge",
    "lowest_est_time", "periodic_telemetry", "freshness_aware", "abvi_edge",
]
TELEMETRY_SCHEDULERS = ["lowest_est_time", "periodic_telemetry",
                        "freshness_aware", "abvi_edge"]


def _base(seed: int, **over) -> Dict[str, Any]:
    d = ScenarioConfig(seed=seed).to_dict()
    d.update(over)
    return d


def exp_A_algorithm_comparison(seeds: List[int]) -> List[Job]:
    jobs = []
    for s in seeds:
        cfg = _base(s, name="medium", sim_time=200.0, task_rate=6.0,
                    telemetry_budget=0.3)
        for sch in ALL_SCHEDULERS:
            jobs.append(Job(sch, cfg, labels={"experiment": "A"}))
    return jobs


def exp_B_budget(seeds: List[int]) -> List[Job]:
    budgets = [0.02, 0.05, 0.1, 0.15, 0.25, 0.4, 0.6, 1.0]
    jobs = []
    for s in seeds:
        for b in budgets:
            cfg = _base(s, name="medium", sim_time=200.0, telemetry_budget=b)
            for sch in TELEMETRY_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": "B", "x": b,
                                                   "xname": "telemetry_budget"}))
    return jobs


def exp_C_workload(seeds: List[int]) -> List[Job]:
    rates = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    jobs = []
    for s in seeds:
        for r in rates:
            cfg = _base(s, name="workload", sim_time=200.0, task_rate=r,
                        telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS + ["cloud_only", "nearest_edge"]:
                jobs.append(Job(sch, cfg, labels={"experiment": "C", "x": r,
                                                   "xname": "task_rate"}))
    return jobs


def exp_D_latency(seeds: List[int]) -> List[Job]:
    lats = [0.04, 0.07, 0.10, 0.14, 0.20]
    jobs = []
    for s in seeds:
        for l in lats:
            cfg = _base(s, name="latency", sim_time=200.0, cloud_base_latency=l,
                        telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS + ["cloud_only"]:
                jobs.append(Job(sch, cfg, labels={"experiment": "D", "x": l,
                                                   "xname": "cloud_latency"}))
    return jobs


def exp_E_bandwidth(seeds: List[int]) -> List[Job]:
    bws = [20.0, 40.0, 60.0, 90.0, 120.0]
    jobs = []
    for s in seeds:
        for bw in bws:
            cfg = _base(s, name="bandwidth", sim_time=200.0, edge_bw_mean=bw,
                        telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": "E", "x": bw,
                                                   "xname": "edge_bandwidth"}))
    return jobs


def exp_F_deadline(seeds: List[int]) -> List[Job]:
    slacks = [1.2, 1.5, 2.0, 2.5, 3.0]
    jobs = []
    for s in seeds:
        for sl in slacks:
            cfg = _base(s, name="deadline", sim_time=200.0,
                        deadline_slack_mean=sl, telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": "F", "x": sl,
                                                   "xname": "deadline_slack"}))
    return jobs


def exp_G_devices(seeds: List[int]) -> List[Job]:
    devs = [20, 30, 40, 50]
    jobs = []
    for s in seeds:
        for nd in devs:
            # keep per-device rate constant-ish by scaling total rate
            cfg = _base(s, name="devices", sim_time=200.0, n_devices=nd,
                        task_rate=0.2 * nd, telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": "G", "x": nd,
                                                   "xname": "n_devices"}))
    return jobs


def exp_H_edges(seeds: List[int]) -> List[Job]:
    edges = [3, 5, 7, 10]
    jobs = []
    for s in seeds:
        for ne in edges:
            cfg = _base(s, name="edges", sim_time=200.0, n_edges=ne,
                        telemetry_budget=0.3)
            for sch in TELEMETRY_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": "H", "x": ne,
                                                   "xname": "n_edges"}))
    return jobs


def exp_IJK_scenarios(seeds: List[int]) -> List[Job]:
    """Stress scenarios: workload spike (I), congestion (J), server failure (K)."""
    from .config import scenario_presets
    presets = scenario_presets()
    chosen = {"I": "spike", "J": "congestion", "K": "edge_failure"}
    jobs = []
    for s in seeds:
        for exp, pkey in chosen.items():
            cfg = presets[pkey].to_dict()
            cfg.update(seed=s, sim_time=200.0, telemetry_budget=0.3)
            for sch in ALL_SCHEDULERS:
                jobs.append(Job(sch, cfg, labels={"experiment": exp,
                                                   "scenario_kind": pkey}))
    return jobs


def exp_L_ablation(seeds: List[int]) -> List[Job]:
    """Ablation: remove one ABVI component at a time."""
    variants = {
        "full": {},
        "no_voi": {"enable_voi": False},
        "no_budget": {"enable_budget": False},
        "no_urgency": {"enable_urgency": False},
        "no_uncertainty": {"enable_uncertainty": False},
        "no_adaptive": {"enable_adaptive": False},
    }
    jobs = []
    for s in seeds:
        cfg = _base(s, name="medium", sim_time=200.0, telemetry_budget=0.2)
        for vname, params in variants.items():
            jobs.append(Job("abvi_edge", cfg,
                            scheduler_kwargs={"params": params},
                            labels={"experiment": "L", "variant": vname}))
    return jobs


EXPERIMENTS = {
    "A": exp_A_algorithm_comparison,
    "B": exp_B_budget,
    "C": exp_C_workload,
    "D": exp_D_latency,
    "E": exp_E_bandwidth,
    "F": exp_F_deadline,
    "G": exp_G_devices,
    "H": exp_H_edges,
    "IJK": exp_IJK_scenarios,
    "L": exp_L_ablation,
}
