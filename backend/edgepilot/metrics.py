"""Metric definitions and aggregation.

Every metric is computed from realized per-task outcomes and the telemetry
ledger. Energy is an *estimated* quantity from the models in
:mod:`environment`, never a hardware measurement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

from .entities import Task


def summarize(tasks: List[Task], tm, env, cfg,
              aoi_samples: List[float]) -> Dict[str, float]:
    """Aggregate metrics over the (post-warmup) completed tasks.

    Returns a flat dict of scalar metrics (see keys below). Definitions:

    * completion time      t_finish - t_arrival  (s)
    * deadline violation   1[t_finish > deadline]
    * success rate         1 - violation rate
    * edge utilization     mean true utilization of edge servers over decisions
    * energy               estimated joules (device + server)
    * telemetry overhead   monitoring bytes / useful data bytes transferred
    * information age       mean AoI of candidate beliefs at decision time (s)
    * scheduling regret     realized completion - omniscient-oracle completion
    * throughput           completed tasks per simulated second
    * decision time        wall-clock seconds per scheduling decision
    """
    done = [t for t in tasks if t.finish_time is not None and t.arrival >= cfg.warmup_time]
    n = len(done)
    out: Dict[str, float] = {}
    if n == 0:
        return {k: 0.0 for k in _KEYS}

    comp = np.array([t.completion_time for t in done])
    viol = np.array([0.0 if t.deadline_met else 1.0 for t in done])
    regret = np.array([max(t.regret, 0.0) for t in done])
    energy = np.array([t.energy for t in done])
    dtime = np.array([t.decision_time for t in done])
    useful_bytes = float(np.sum([t.input_size + t.output_size for t in done]))

    out["n_tasks"] = float(n)
    out["avg_completion"] = float(np.mean(comp))
    out["median_completion"] = float(np.median(comp))
    out["p95_completion"] = float(np.percentile(comp, 95))
    out["deadline_violation_rate"] = float(np.mean(viol))
    out["success_rate"] = float(1.0 - np.mean(viol))
    out["avg_regret"] = float(np.mean(regret))
    out["p95_regret"] = float(np.percentile(regret, 95))
    out["total_energy"] = float(np.sum(energy))
    out["avg_energy"] = float(np.mean(energy))
    out["telemetry_requests"] = float(tm.n_probes)
    out["telemetry_bytes"] = float(tm.spent_bytes)
    out["telemetry_norm"] = float(tm.normalized_spent())
    out["monitoring_overhead"] = float(tm.spent_bytes / useful_bytes) if useful_bytes > 0 else 0.0
    out["budget_used_frac"] = float(tm.spent_bytes / tm.budget_bytes) if tm.budget_bytes > 0 else 0.0
    out["avg_info_age"] = float(np.mean(aoi_samples)) if aoi_samples else 0.0
    out["edge_utilization"] = float(np.mean([e.u_true for e in env.edges])) if env.edges else 0.0
    out["throughput"] = float(n / max(cfg.sim_time - cfg.warmup_time, 1e-6))
    out["avg_decision_time_ms"] = float(np.mean(dtime) * 1000.0)

    # placement distribution
    placements = [t.placement for t in done]
    out["frac_local"] = float(np.mean([1.0 if p and p.startswith("local") else 0.0 for p in placements]))
    out["frac_edge"] = float(np.mean([1.0 if p and p.startswith("edge") else 0.0 for p in placements]))
    out["frac_cloud"] = float(np.mean([1.0 if p == "cloud" else 0.0 for p in placements]))
    return out


_KEYS = [
    "n_tasks", "avg_completion", "median_completion", "p95_completion",
    "deadline_violation_rate", "success_rate", "avg_regret", "p95_regret",
    "total_energy", "avg_energy", "telemetry_requests", "telemetry_bytes",
    "telemetry_norm", "monitoring_overhead", "budget_used_frac", "avg_info_age",
    "edge_utilization", "throughput", "avg_decision_time_ms",
    "frac_local", "frac_edge", "frac_cloud",
]
