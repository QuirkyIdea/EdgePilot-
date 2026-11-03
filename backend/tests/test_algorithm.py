"""Algorithm-level tests for ABVI-Edge: VoI, budget pacing, belief dynamics."""
import math
import pytest

from edgepilot.config import ScenarioConfig
from edgepilot.environment import Environment
from edgepilot.telemetry import TelemetryManager, Belief
from edgepilot.simulator import run_once
from edgepilot.schedulers.abvi import ABVIParams


def test_belief_uncertainty_grows_with_age():
    b = Belief(value=0.8, t_obs=0.0, prior_mean=0.4, sigma=0.3, theta=0.5)
    assert b.predict_std(0.0) == pytest.approx(0.0, abs=1e-9)
    s_small = b.predict_std(0.5)
    s_large = b.predict_std(10.0)
    assert s_small < s_large
    # mean decays toward prior as age grows
    assert abs(b.predict_mean(100.0) - 0.4) < 1e-3


def test_telemetry_observation_resets_age_and_spends():
    cfg = ScenarioConfig(seed=1, sim_time=10.0)
    env = Environment(cfg)
    tm = TelemetryManager(cfg, env)
    before = tm.spent_bytes
    ok = tm.observe_location("edge:0", now=5.0)
    assert ok
    assert tm.spent_bytes == pytest.approx(before + cfg.telemetry_req_bytes)
    assert tm.util_belief["edge:0"].age(5.0) == 0.0


def test_shadow_price_rises_when_budget_scarce():
    from edgepilot.schedulers import REGISTRY
    cfg = ScenarioConfig(seed=1, sim_time=100.0, telemetry_budget=0.3)
    env = Environment(cfg)
    tm = TelemetryManager(cfg, env)
    sched = REGISTRY["abvi_edge"](cfg, env, tm)
    p_ahead = sched._shadow_price(now=1.0)          # early, budget full
    tm.spent_bytes = 0.95 * tm.budget_bytes          # nearly exhausted
    p_scarce = sched._shadow_price(now=1.0)
    assert p_scarce > p_ahead


def test_voi_nonnegative_and_zero_without_uncertainty():
    from edgepilot.schedulers import REGISTRY
    cfg = ScenarioConfig(seed=1, sim_time=20.0)
    env = Environment(cfg)
    tm = TelemetryManager(cfg, env)
    sched = REGISTRY["abvi_edge"](cfg, env, tm)
    task = env.tasks[0]
    now = task.arrival
    costs = sched._belief_cost(task, now, task.deadline - now)
    best = min(c for c, _ in costs.values())
    v = sched._voi(task, "edge:0", now, task.deadline - now, costs, best)
    assert v >= -1e-9
    # collapse uncertainty -> VoI must be exactly 0
    sched.p.enable_uncertainty = False
    v0 = sched._voi(task, "edge:0", now, task.deadline - now, costs, best)
    assert v0 == 0.0


def test_abvi_not_worse_than_estimate_only_on_quality():
    """Sanity: with telemetry, ABVI should beat the stale-estimate baseline."""
    cfg = ScenarioConfig(seed=11, sim_time=150.0, telemetry_budget=0.3)
    abvi = run_once(cfg, "abvi_edge").summary
    base = run_once(ScenarioConfig(seed=11, sim_time=150.0, telemetry_budget=0.3),
                    "lowest_est_time").summary
    assert abvi["avg_regret"] <= base["avg_regret"] + 1e-6
    assert abvi["deadline_violation_rate"] <= base["deadline_violation_rate"] + 1e-6
