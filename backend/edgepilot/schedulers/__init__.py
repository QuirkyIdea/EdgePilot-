"""Scheduler implementations: baselines and the proposed ABVI-Edge."""
from .base import Scheduler, Decision
from .baselines import (
    LocalOnly, CloudOnly, RandomOffload, NearestEdge,
    LowestEstimatedTime, PeriodicTelemetry, FreshnessAware,
)
from .abvi import ABVIEdge

REGISTRY = {
    "local_only": LocalOnly,
    "cloud_only": CloudOnly,
    "random": RandomOffload,
    "nearest_edge": NearestEdge,
    "lowest_est_time": LowestEstimatedTime,
    "periodic_telemetry": PeriodicTelemetry,
    "freshness_aware": FreshnessAware,
    "abvi_edge": ABVIEdge,
}

__all__ = ["Scheduler", "Decision", "REGISTRY", "ABVIEdge"]
