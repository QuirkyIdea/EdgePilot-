"""Reproducibility: identical seed -> identical results; different seed differs."""
import pytest

from edgepilot.config import ScenarioConfig
from edgepilot.simulator import run_once


SCHEDULERS = ["cloud_only", "lowest_est_time", "periodic_telemetry",
              "freshness_aware", "abvi_edge"]


@pytest.mark.parametrize("sched", SCHEDULERS)
def test_same_seed_identical(sched):
    cfg = ScenarioConfig(name="repro", seed=42, sim_time=60.0)
    a = run_once(cfg, sched).summary
    b = run_once(ScenarioConfig(name="repro", seed=42, sim_time=60.0), sched).summary
    for k in ["avg_completion", "deadline_violation_rate", "avg_regret",
              "telemetry_requests"]:
        assert a[k] == pytest.approx(b[k], rel=1e-9, abs=1e-9), k


def test_different_seed_differs():
    cfg1 = ScenarioConfig(name="r", seed=1, sim_time=60.0)
    cfg2 = ScenarioConfig(name="r", seed=2, sim_time=60.0)
    a = run_once(cfg1, "abvi_edge").summary
    b = run_once(cfg2, "abvi_edge").summary
    # Task traces differ, so at least completion time should differ.
    assert a["avg_completion"] != b["avg_completion"]


def test_identical_task_trace_across_schedulers():
    """Fairness: all schedulers face the same arrivals/topology for a seed."""
    cfg = ScenarioConfig(name="fair", seed=7, sim_time=60.0)
    counts = {s: run_once(ScenarioConfig(name="fair", seed=7, sim_time=60.0), s)
              .summary["n_tasks"] for s in SCHEDULERS}
    assert len(set(counts.values())) == 1, counts
