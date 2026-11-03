"""Baseline schedulers.

All baselines operate on the *same* task arrivals, topology and ground-truth
traces as the proposed method (fairness). They differ only in how they decide
placement and whether/how they spend telemetry.

Reference (naive) baselines:
  * LocalOnly, CloudOnly, RandomOffload, NearestEdge
Estimation baselines (belief-driven, like our method):
  * LowestEstimatedTime     -- greedy on expected completion, never probes
  * PeriodicTelemetry       -- refreshes all locations on a fixed period
  * FreshnessAware          -- probes a location when its AoI exceeds a threshold
"""
from __future__ import annotations

from typing import List, Optional

from .base import Scheduler, Decision
from ..entities import Task, LocType


class LocalOnly(Scheduler):
    name = "local_only"

    def decide(self, task: Task, now: float) -> Decision:
        return self._timed(lambda t, n: Decision(f"local:{t.device}"), task, now)


class CloudOnly(Scheduler):
    name = "cloud_only"

    def decide(self, task: Task, now: float) -> Decision:
        return self._timed(lambda t, n: Decision("cloud"), task, now)


class RandomOffload(Scheduler):
    name = "random"

    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            locs = self.env.candidate_locations(t)
            idx = int(self.env.rng.integers(0, len(locs)))
            return Decision(locs[idx].loc_id)
        return self._timed(fn, task, now)


class NearestEdge(Scheduler):
    """Always use the edge with the highest-bandwidth link to the device."""
    name = "nearest_edge"

    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            best_edge, best_bw = None, -1.0
            for e in self.env.edges:
                if e.failed:
                    continue
                link = self.env.link_for(t.device, e.loc_id)
                bw = 0.0 if link is None else link.base_bw
                if bw > best_bw:
                    best_bw, best_edge = bw, e.loc_id
            return Decision(best_edge or "cloud")
        return self._timed(fn, task, now)


class LowestEstimatedTime(Scheduler):
    """Greedy on expected completion time under the current (stale) belief.

    Never issues telemetry: it is the "schedule on whatever we last knew"
    reference against which the value of fresh information is measured.
    """
    name = "lowest_est_time"

    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            preds = self.predictor.predict_all(t, self.tm, self.env, n)
            best = min(preds, key=lambda p: p.mean_time)
            return Decision(best.loc.loc_id)
        return self._timed(fn, task, now)


class PeriodicTelemetry(Scheduler):
    """Refresh *all* locations on a fixed monitoring period, then schedule.

    Represents conventional "monitor everything on a timer" telemetry. It
    spends budget blindly (independent of task urgency or uncertainty) and
    stops probing once the budget is exhausted.
    """
    name = "periodic_telemetry"
    uses_telemetry = True

    def __init__(self, *args, period: float = 1.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.period = period
        self._last_probe = -1e9

    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            probes: List[str] = []
            if n - self._last_probe >= self.period:
                for loc in self.env.candidate_locations(t):
                    if loc.loc_type == LocType.LOCAL:
                        continue
                    if self.tm.observe_location(loc.loc_id, n):
                        self.tm.observe_link(t.device, loc.loc_id, n)
                        probes.append(loc.loc_id)
                self._last_probe = n
            preds = self.predictor.predict_all(t, self.tm, self.env, n)
            best = min(preds, key=lambda p: p.mean_time)
            return Decision(best.loc.loc_id, probes=probes)
        return self._timed(fn, task, now)


class FreshnessAware(Scheduler):
    """Probe any candidate whose Age-of-Information exceeds a fixed threshold.

    A pure freshness rule (the AoI-threshold heuristic the directive warns
    against calling "intelligent"): it ignores task urgency, uncertainty
    magnitude and the value of the information — only staleness matters.
    """
    name = "freshness_aware"
    uses_telemetry = True

    def __init__(self, *args, aoi_threshold: float = 1.5, **kwargs):
        super().__init__(*args, **kwargs)
        self.aoi_threshold = aoi_threshold

    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            probes: List[str] = []
            for loc in self.env.candidate_locations(t):
                if loc.loc_type == LocType.LOCAL:
                    continue
                age = self.tm.util_belief[loc.loc_id].age(n)
                if age >= self.aoi_threshold and self.tm.observe_location(loc.loc_id, n):
                    self.tm.observe_link(t.device, loc.loc_id, n)
                    probes.append(loc.loc_id)
            preds = self.predictor.predict_all(t, self.tm, self.env, n)
            best = min(preds, key=lambda p: p.mean_time)
            return Decision(best.loc.loc_id, probes=probes)
        return self._timed(fn, task, now)
