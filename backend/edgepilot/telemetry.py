"""Telemetry, belief state, Age-of-Information and the monitoring budget.

The scheduler does **not** read ground truth. Instead it keeps a *belief*
about each location's utilization and each link's congestion, consisting of a
last-observed value and the time it was observed (its Age of Information, AoI).

Because the true state follows a mean-reverting (OU) process, the predictive
distribution of the current state given an observation of age ``a`` is:

    mean(a)      = u_mean + (u_obs - u_mean) * exp(-theta * a)
    variance(a)  = sigma^2 * (1 - exp(-2 * theta * a))

i.e. the belief decays toward the prior mean and its variance grows toward the
stationary variance as information ages. This closed form is what lets the
scheduler quantify *uncertainty* — and therefore the value of refreshing it.

The :class:`TelemetryManager` also enforces the monitoring **budget**: a probe
costs ``telemetry_req_bytes`` of monitoring traffic; the total over the budget
window may not exceed the configured budget (expressed as a fraction of the
cost of observing every location on every decision).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import math

from .config import ScenarioConfig
from .environment import Environment


@dataclass
class Belief:
    """Belief about a single scalar state (utilization or congestion)."""
    value: float          # last observed value
    t_obs: float          # time of last observation
    prior_mean: float     # stationary mean of the OU process
    sigma: float          # stationary std
    theta: float          # mean reversion speed

    def age(self, now: float) -> float:
        return max(now - self.t_obs, 0.0)

    def predict_mean(self, now: float) -> float:
        a = self.age(now)
        decay = math.exp(-self.theta * a)
        return self.prior_mean + (self.value - self.prior_mean) * decay

    def predict_var(self, now: float) -> float:
        a = self.age(now)
        return (self.sigma ** 2) * (1.0 - math.exp(-2.0 * self.theta * a))

    def predict_std(self, now: float) -> float:
        return math.sqrt(max(self.predict_var(now), 0.0))


class TelemetryManager:
    """Maintains beliefs over the environment and accounts for budget usage."""

    def __init__(self, cfg: ScenarioConfig, env: Environment):
        self.cfg = cfg
        self.env = env

        # Budget bookkeeping -------------------------------------------------
        # "Observe everything every decision" reference cost over the window.
        # Only edges and the cloud are ever probed (local state is free), so the
        # reference counts those probeable locations -- this makes the budget
        # fraction interpretable and actually binding.
        n_locs = cfg.n_edges + 1
        est_decisions = max(cfg.task_rate * cfg.telemetry_budget_window, 1.0)
        self.full_cost = n_locs * est_decisions * cfg.telemetry_req_bytes
        self.budget_bytes = cfg.telemetry_budget * self.full_cost

        self.spent_bytes = 0.0
        self.n_probes = 0
        self.probe_history: list[tuple[float, str]] = []  # (time, loc_id)

        # Beliefs ------------------------------------------------------------
        self.util_belief: Dict[str, Belief] = {}
        for loc_id, loc in env.locations.items():
            self.util_belief[loc_id] = Belief(
                value=loc.u_mean, t_obs=0.0, prior_mean=loc.u_mean,
                sigma=cfg.load_sigma, theta=cfg.load_theta,
            )
        # Link congestion beliefs (keyed by (device, loc_id)).
        self.cong_belief: Dict[tuple, Belief] = {}
        for key in env.links:
            self.cong_belief[key] = Belief(
                value=1.0, t_obs=0.0, prior_mean=1.0,
                sigma=cfg.link_congestion_sigma, theta=cfg.link_congestion_theta,
            )

    # ------------------------------------------------------------- budget
    @property
    def remaining_bytes(self) -> float:
        return max(self.budget_bytes - self.spent_bytes, 0.0)

    @property
    def budget_fraction_left(self) -> float:
        if self.budget_bytes <= 0:
            return 0.0
        return self.remaining_bytes / self.budget_bytes

    def can_afford(self, n_probes: int = 1) -> bool:
        return self.spent_bytes + n_probes * self.cfg.telemetry_req_bytes <= self.budget_bytes + 1e-12

    def budget_pacing_target(self, now: float) -> float:
        """Fraction of budget that *should* remain at time ``now`` under even
        pacing. Used by the scheduler to compute the shadow price of budget."""
        w = self.cfg.telemetry_budget_window
        return max(1.0 - now / w, 0.0)

    # --------------------------------------------------------- observation
    def observe_location(self, loc_id: str, now: float) -> bool:
        """Spend budget to refresh the utilization belief for ``loc_id``.

        Returns False (and does nothing) if the budget cannot afford it.
        """
        if not self.can_afford(1):
            return False
        loc = self.env.locations[loc_id]
        noisy = loc.u_true + self.env.rng.normal(0.0, self.cfg.telemetry_noise)
        b = self.util_belief[loc_id]
        b.value = min(max(noisy, 0.0), 0.98)
        b.t_obs = now
        self.spent_bytes += self.cfg.telemetry_req_bytes
        self.n_probes += 1
        self.probe_history.append((now, loc_id))
        return True

    def observe_link(self, device: int, loc_id: str, now: float) -> None:
        """Piggy-backed congestion observation (bundled with a location probe).

        Observing a server co-locates a link probe for the requesting device;
        it does not cost extra budget (same monitoring message carries RTT).
        """
        key = (device, loc_id)
        link = self.env.links.get(key)
        if link is None:
            return
        b = self.cong_belief.get(key)
        if b is None:
            return
        b.value = link.congestion
        b.t_obs = now

    # ----------------------------------------------------- belief queries
    def est_utilization(self, loc_id: str, now: float) -> float:
        return self.util_belief[loc_id].predict_mean(now)

    def util_uncertainty(self, loc_id: str, now: float) -> float:
        return self.util_belief[loc_id].predict_std(now)

    def est_congestion(self, device: int, loc_id: str, now: float) -> float:
        b = self.cong_belief.get((device, loc_id))
        return 1.0 if b is None else b.predict_mean(now)

    def normalized_spent(self) -> float:
        if self.full_cost <= 0:
            return 0.0
        return self.spent_bytes / self.full_cost
