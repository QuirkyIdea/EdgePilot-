"""Discrete-event simulation engine.

Events are task arrivals (the environment's stochastic state is advanced
between arrivals). This is an *event-driven* loop: there is no fixed global
clock stepping through empty time; the environment's internal ``advance_to``
integrates its OU dynamics with a fine tick only when needed.

Execution model (stated assumption): a task's realized completion time is
computed from the *true* environment state sampled at its arrival (a snapshot
model at arrival granularity). This keeps realized outcomes consistent with the
information a scheduler could in principle obtain, and makes the omniscient
oracle well-defined for the regret metric.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

import numpy as np

from .config import ScenarioConfig
from .environment import Environment
from .entities import Task
from .telemetry import TelemetryManager
from .prediction import AnalyticPredictor
from .schedulers.base import Scheduler
from . import metrics as metrics_mod


@dataclass
class SimResult:
    scheduler: str
    scenario: str
    seed: int
    summary: Dict[str, float]
    tasks: List[Task] = field(default_factory=list)
    timeseries: Dict[str, List[float]] = field(default_factory=dict)


class Simulator:
    def __init__(self, cfg: ScenarioConfig, scheduler_cls: Type[Scheduler],
                 scheduler_kwargs: Optional[dict] = None,
                 collect_timeseries: bool = False):
        self.cfg = cfg
        self.env = Environment(cfg)
        self.tm = TelemetryManager(cfg, self.env)
        self.predictor = AnalyticPredictor(cfg)
        self.scheduler_cls = scheduler_cls
        self.scheduler_kwargs = scheduler_kwargs or {}
        self.scheduler: Scheduler = scheduler_cls(
            cfg, self.env, self.tm, self.predictor, **self.scheduler_kwargs)
        self.collect_timeseries = collect_timeseries

    def run(self) -> SimResult:
        cfg = self.cfg
        env = self.env
        tm = self.tm
        aoi_samples: List[float] = []
        ts: Dict[str, List[float]] = {
            "time": [], "budget_frac_left": [], "edge_util": [],
            "probes_cum": [], "completion": [], "regret": [],
        }

        for task in env.tasks:
            env.advance_to(task.arrival)

            # Omniscient oracle (full fresh knowledge) for regret.
            _, oracle_t = env.oracle_completion(task)

            # Scheduler decision (may spend telemetry).
            dec = self.scheduler.decide(task, task.arrival)
            task.placement = dec.loc_id
            task.decision_time = dec.decision_time
            task.telemetry_used = len(dec.probes)
            task.telemetry_bytes = len(dec.probes) * cfg.telemetry_req_bytes

            # Mean AoI of candidate utilization beliefs at decision time.
            cand = env.candidate_locations(task)
            ages = [tm.util_belief[c.loc_id].age(task.arrival)
                    for c in cand if not c.loc_id.startswith("local")]
            if ages:
                aoi_samples.append(float(np.mean(ages)))

            # Realized execution under true state (snapshot at arrival).
            loc = env.locations[dec.loc_id]
            realized = env.true_completion_time(task, loc)
            if not np.isfinite(realized):
                # Chosen location infeasible (e.g. failed edge): fall back to cloud.
                loc = env.cloud
                task.placement = "cloud"
                realized = env.true_completion_time(task, loc)
            # NOTE: the algorithm's wall-clock decision time is reported as a
            # separate computational-overhead metric; it is deliberately NOT
            # folded into the simulated completion time (doing so would make
            # results depend on host CPU speed and break reproducibility).
            task.start_time = task.arrival
            task.finish_time = task.start_time + realized
            task.energy = env.true_energy(task, loc)
            task.regret = max(realized - oracle_t, 0.0) if np.isfinite(oracle_t) else 0.0

            if self.collect_timeseries and task.arrival >= cfg.warmup_time:
                ts["time"].append(task.arrival)
                ts["budget_frac_left"].append(tm.budget_fraction_left)
                ts["edge_util"].append(float(np.mean([e.u_true for e in env.edges])) if env.edges else 0.0)
                ts["probes_cum"].append(float(tm.n_probes))
                ts["completion"].append(float(realized))
                ts["regret"].append(float(task.regret))

        summary = metrics_mod.summarize(env.tasks, tm, env, cfg, aoi_samples)
        return SimResult(
            scheduler=self.scheduler.name, scenario=cfg.name, seed=cfg.seed,
            summary=summary, tasks=env.tasks,
            timeseries=ts if self.collect_timeseries else {},
        )


def run_once(cfg: ScenarioConfig, scheduler_key: str,
             scheduler_kwargs: Optional[dict] = None,
             collect_timeseries: bool = False) -> SimResult:
    """Convenience: run a single simulation by scheduler registry key."""
    from .schedulers import REGISTRY
    if scheduler_key not in REGISTRY:
        raise KeyError(f"unknown scheduler '{scheduler_key}'; "
                       f"choices: {sorted(REGISTRY)}")
    return Simulator(cfg, REGISTRY[scheduler_key], scheduler_kwargs,
                     collect_timeseries=collect_timeseries).run()
