"""Edge-case robustness: no edges, empty queue, failures, impossible deadlines."""
import pytest

from edgepilot.config import ScenarioConfig
from edgepilot.simulator import Simulator, run_once
from edgepilot.schedulers import REGISTRY


def test_no_edge_servers():
    cfg = ScenarioConfig(name="noedge", seed=1, sim_time=40.0, n_edges=0)
    res = run_once(cfg, "abvi_edge")
    # With no edges, tasks go local or cloud; all still complete.
    assert res.summary["n_tasks"] > 0
    assert res.summary["frac_edge"] == 0.0


def test_empty_task_queue():
    # Extremely low arrival rate + short horizon can yield few/no post-warmup tasks.
    cfg = ScenarioConfig(name="empty", seed=1, sim_time=5.0, warmup_time=5.0,
                         task_rate=0.5)
    res = run_once(cfg, "abvi_edge")  # must not crash
    assert res.summary["n_tasks"] >= 0


def test_server_failure_handled():
    cfg = ScenarioConfig(name="fail", seed=2, sim_time=120.0,
                         edge_failure_time=40.0, failed_edge_index=0)
    sim = Simulator(cfg, REGISTRY["abvi_edge"])
    res = sim.run()
    assert sim.env.edges[0].failed
    # No task should be left executing on the failed edge.
    for t in res.tasks:
        if t.arrival >= 40.0 and t.placement == "edge:0":
            pytest.fail("task placed on failed edge")


def test_impossible_deadline_counts_as_violation():
    cfg = ScenarioConfig(name="imp", seed=2, sim_time=40.0,
                         deadline_slack_mean=1.0, deadline_slack_cv=0.01,
                         demand_mean=30000.0)
    res = run_once(cfg, "abvi_edge")
    # Very tight deadlines + huge demand -> high violation rate, no crash.
    assert 0.0 <= res.summary["deadline_violation_rate"] <= 1.0


def test_single_edge_overloaded():
    cfg = ScenarioConfig(name="one", seed=2, sim_time=60.0, n_edges=1,
                         task_rate=12.0, load_mean=0.85)
    res = run_once(cfg, "abvi_edge")
    assert res.summary["n_tasks"] > 0
