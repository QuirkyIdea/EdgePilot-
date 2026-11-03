"""Scheduler interface.

A scheduler is invoked once per task arrival. It may optionally spend telemetry
budget (through the :class:`TelemetryManager`) to refresh its belief before
committing to a placement. It returns a :class:`Decision`. The measured
wall-clock time of the ``decide`` call is recorded as the algorithm decision
time metric.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import time

from ..config import ScenarioConfig
from ..entities import Task
from ..telemetry import TelemetryManager
from ..prediction import AnalyticPredictor


@dataclass
class Decision:
    loc_id: str                         # chosen placement
    probes: List[str] = field(default_factory=list)   # locations observed
    decision_time: float = 0.0          # measured seconds spent deciding


class Scheduler:
    name = "base"
    #: Whether this scheduler ever issues telemetry probes.
    uses_telemetry = False

    def __init__(self, cfg: ScenarioConfig, env, tm: TelemetryManager,
                 predictor: Optional[AnalyticPredictor] = None):
        self.cfg = cfg
        self.env = env
        self.tm = tm
        self.predictor = predictor or AnalyticPredictor(cfg)

    def decide(self, task: Task, now: float) -> Decision:  # pragma: no cover
        raise NotImplementedError

    # Helper used by several schedulers.
    def _timed(self, fn, task: Task, now: float) -> Decision:
        start = time.perf_counter()
        dec = fn(task, now)
        dec.decision_time = time.perf_counter() - start
        return dec
