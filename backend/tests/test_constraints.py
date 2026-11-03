"""Validity and constraint tests: placements, budget, deadlines, energy."""
import pytest

from edgepilot.config import ScenarioConfig
from edgepilot.simulator import Simulator, run_once
from edgepilot.schedulers import REGISTRY


ALL = list(REGISTRY)


@pytest.mark.parametrize("sched", ALL)
def test_placements_are_valid(sched):
    cfg = ScenarioConfig(name="v", seed=3, sim_time=50.0)
    sim = Simulator(cfg, REGISTRY[sched])
    res = sim.run()
    valid = set(sim.env.locations.keys())
    for t in res.tasks:
        assert t.placement in valid, t.placement
        # a task placed locally must be on its own device
        if t.placement.startswith("local"):
            assert t.placement == f"local:{t.device}"


@pytest.mark.parametrize("sched", ALL)
def test_budget_never_exceeded(sched):
    cfg = ScenarioConfig(name="bud", seed=3, sim_time=80.0, telemetry_budget=0.1)
    sim = Simulator(cfg, REGISTRY[sched])
    sim.run()
    # spent bytes may not exceed the budget (allow fp epsilon).
    assert sim.tm.spent_bytes <= sim.tm.budget_bytes + 1e-9


def test_zero_budget_means_no_probes():
    cfg = ScenarioConfig(name="zb", seed=3, sim_time=50.0, telemetry_budget=0.0)
    for sched in ["periodic_telemetry", "freshness_aware", "abvi_edge"]:
        sim = Simulator(cfg, REGISTRY[sched])
        sim.run()
        assert sim.tm.n_probes == 0, sched


@pytest.mark.parametrize("sched", ALL)
def test_completion_and_energy_nonnegative(sched):
    cfg = ScenarioConfig(name="ne", seed=5, sim_time=50.0)
    res = run_once(cfg, sched)
    for t in res.tasks:
        if t.finish_time is not None:
            assert t.completion_time >= 0
            assert t.finish_time >= t.arrival
            assert t.energy >= 0
            assert t.regret >= -1e-9


@pytest.mark.parametrize("sched", ALL)
def test_regret_nonnegative_vs_oracle(sched):
    """Realized completion can never beat the omniscient oracle."""
    cfg = ScenarioConfig(name="reg", seed=9, sim_time=60.0)
    res = run_once(cfg, sched)
    assert res.summary["avg_regret"] >= -1e-9
