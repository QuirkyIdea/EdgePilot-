r"""ABVI-Edge: Adaptive Budgeted Value-of-Information Edge Scheduler (proposed).

Decision problem per task
-------------------------
On each task arrival the scheduler holds a *belief* over every candidate
location's utilization (and the relevant link congestion), with age-dependent
uncertainty (see :mod:`telemetry`). It must jointly decide:

  (A) a subset ``S`` of locations to **probe** (spend telemetry budget to
      collapse their uncertainty), and then
  (B) the **placement** for the task.

Decision cost
-------------
For a candidate location l with predictive completion-time mean ``m_l`` and
deadline-hit probability ``p_l`` we define the scalar decision cost

    C(l) = m_l  +  w_d * prio * (1 - p_l) * D   +  w_e * E_l

where ``D`` is a deadline-miss penalty (s), ``prio`` scales urgency, and the
energy term is a small secondary objective. The myopic placement cost under
the current belief is ``C* = min_l C(l)``.

Value of Information
--------------------
Probing location l reveals its true utilization (and link congestion), turning
its uncertain cost into a (near) deterministic one. The *value of information*
of probing l is the expected reduction in realized decision cost:

    VoI(l) = C*  -  E_{u ~ belief(l)}[ min( C_l(u) , min_{k != l} C(k) ) ]

which is non-negative and large exactly when (i) l is uncertain, and (ii) l is
a plausible winner whose true value could flip the decision. We estimate the
expectation by sampling ``u`` (and congestion) from the closed-form predictive
distribution — no peeking at ground truth.

Budget shadow price (adaptivity)
--------------------------------
Each probe is charged against a monitoring budget. We demand a minimum value
per probe via an adaptive shadow price ``lambda(t)`` that rises when the budget
is being consumed faster than an even-pacing schedule, and falls when we are
ahead of pace — reserving budget for future, potentially more valuable
decisions:

    lambda(t) = lambda0 * (time_frac_left + eps) / (budget_frac_left + eps)

Policy
------
Greedily probe the location with the highest *net* value
``urgency * VoI(l) - lambda(t)`` while it is positive, affordable, and uncaps
the per-decision probe limit; re-estimate VoI after each probe (the baseline
``C*`` shifts). Finally place the task at ``argmin_l C(l)`` under the updated
belief.

Complexity: with ``K`` candidate locations, ``R`` VoI samples and at most ``K``
probes, a decision costs ``O(K^2 * R)`` arithmetic ops — all closed-form, no
inner simulation. ``R`` and ``K`` are small (tens), so decisions are sub-ms.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import math

import numpy as np

from .base import Scheduler, Decision
from ..entities import Task, Location, LocType


@dataclass
class ABVIParams:
    lambda0: float = 0.015        # base shadow price (s of value demanded / probe)
    w_deadline: float = 1.0       # weight on deadline-miss risk
    deadline_penalty: float = 1.5 # D: seconds-equivalent penalty for a miss
    w_energy: float = 0.0005      # small secondary weight on energy (s per J)
    voi_samples: int = 20         # R: samples for the VoI expectation
    max_probes: int = 4           # per-decision probe cap
    urgency_gain: float = 1.5     # how strongly tight deadlines raise willingness
    eps: float = 1e-3

    # Ablation switches
    enable_voi: bool = True
    enable_budget: bool = True
    enable_urgency: bool = True
    enable_uncertainty: bool = True
    enable_adaptive: bool = True   # if False: never probe (pure estimate)
    uncertainty_tau: float = 0.08  # fallback probe threshold when VoI disabled


class ABVIEdge(Scheduler):
    name = "abvi_edge"
    uses_telemetry = True

    def __init__(self, *args, params: Optional[ABVIParams] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.p = params or ABVIParams()
        self._rng = np.random.default_rng(777 + self.cfg.seed)

    # ------------------------------------------------------- cost helpers
    def _deterministic_time(self, task: Task, loc: Location, u: float,
                            cong: float) -> float:
        """Closed-form completion time given known utilization & congestion."""
        if loc.failed or loc.capacity <= 0:
            return float("inf")
        u = min(max(u, 0.0), 0.95)
        compute = (task.demand / loc.capacity) / (1.0 - u)
        if loc.loc_type == LocType.LOCAL:
            return compute
        link = self.env.link_for(task.device, loc.loc_id)
        if link is None:
            return float("inf")
        c = max(cong, 0.3)
        eff_bw = max(link.base_bw / c, 1e-3)
        lat = link.base_latency * c
        tx = (task.input_size + task.output_size) / eff_bw + 2 * lat
        return tx + compute

    def _cost_from_time(self, task: Task, t: float, slack: float,
                        met: Optional[bool], deadline_prob: Optional[float],
                        energy: float) -> float:
        p = self.p
        prio = 1.0 + (task.priority - 1) * 0.8
        if met is not None:
            miss = 0.0 if met else 1.0
        else:
            miss = 1.0 - (deadline_prob if deadline_prob is not None else 1.0)
        return t + p.w_deadline * prio * miss * p.deadline_penalty \
            + p.w_energy * energy

    def _belief_cost(self, task: Task, now: float, slack: float):
        """Expected cost for each candidate under the current belief."""
        preds = self.predictor.predict_all(task, self.tm, self.env, now)
        costs = {}
        for pr in preds:
            if not self.p.enable_uncertainty:
                # collapse uncertainty: treat belief mean as certain
                u = self.tm.est_utilization(pr.loc.loc_id, now)
                cong = 1.0 if pr.loc.loc_type == LocType.LOCAL else \
                    self.tm.est_congestion(task.device, pr.loc.loc_id, now)
                t = self._deterministic_time(task, pr.loc, u, cong)
                met = t <= slack
                costs[pr.loc.loc_id] = (
                    self._cost_from_time(task, t, slack, met, None, pr.expected_energy),
                    pr)
            else:
                costs[pr.loc.loc_id] = (
                    self._cost_from_time(task, pr.mean_time, slack, None,
                                         pr.deadline_prob, pr.expected_energy),
                    pr)
        return costs

    # --------------------------------------------------------------- VoI
    def _voi(self, task: Task, loc_id: str, now: float, slack: float,
             costs: dict, baseline_best: float) -> float:
        """Estimate VoI of probing ``loc_id`` by sampling its true state."""
        if not self.p.enable_uncertainty:
            return 0.0
        loc = self.env.locations[loc_id]
        if loc.loc_type == LocType.LOCAL:
            return 0.0
        b_u = self.tm.util_belief[loc_id]
        u_mean, u_std = b_u.predict_mean(now), b_u.predict_std(now)
        b_c = self.tm.cong_belief.get((task.device, loc_id))
        c_mean = 1.0 if b_c is None else b_c.predict_mean(now)
        c_std = 0.0 if b_c is None else b_c.predict_std(now)

        if u_std < 1e-4 and c_std < 1e-4:
            return 0.0

        # best cost among the *other* candidates (unaffected by probing l)
        other_best = min((c for k, (c, _) in costs.items() if k != loc_id),
                         default=float("inf"))

        R = self.p.voi_samples
        us = np.clip(self._rng.normal(u_mean, max(u_std, 1e-6), R), 0.0, 0.95)
        cs = np.clip(self._rng.normal(c_mean, max(c_std, 1e-6), R), 0.3, 8.0)
        pr = costs[loc_id][1]
        acc = 0.0
        for i in range(R):
            t = self._deterministic_time(task, loc, us[i], cs[i])
            met = t <= slack
            cl = self._cost_from_time(task, t, slack, met, None, pr.expected_energy)
            acc += min(cl, other_best)
        exp_after = acc / R
        return max(baseline_best - exp_after, 0.0)

    # ----------------------------------------------------- shadow price
    def _shadow_price(self, now: float) -> float:
        p = self.p
        if not p.enable_budget:
            return p.lambda0
        time_frac = max(1.0 - now / self.cfg.telemetry_budget_window, 0.0)
        budget_frac = self.tm.budget_fraction_left
        return p.lambda0 * (time_frac + p.eps) / (budget_frac + p.eps)

    def _urgency(self, task: Task, now: float, best_time: float) -> float:
        if not self.p.enable_urgency:
            return 1.0
        slack = max(task.deadline - now, 1e-3)
        ratio = best_time / slack  # closer to 1 => more urgent
        prio = 1.0 + (task.priority - 1) * 0.6
        return prio * (1.0 + self.p.urgency_gain * min(max(ratio, 0.0), 2.0))

    # ----------------------------------------------------------- decide
    def decide(self, task: Task, now: float) -> Decision:
        def fn(t: Task, n: float) -> Decision:
            slack = t.deadline - n
            probes: List[str] = []
            costs = self._belief_cost(t, n, slack)

            if self.p.enable_adaptive:
                lam = self._shadow_price(n)
                for _ in range(self.p.max_probes):
                    if not self.tm.can_afford(1):
                        break
                    best_id = min(costs, key=lambda k: costs[k][0])
                    best_cost = costs[best_id][0]
                    best_time = costs[best_id][1].mean_time
                    urg = self._urgency(t, n, best_time)

                    # Rank candidate probes by net value.
                    best_probe, best_net = None, 0.0
                    for loc_id in costs:
                        if self.env.locations[loc_id].loc_type == LocType.LOCAL:
                            continue
                        if loc_id in probes:
                            continue
                        if self.p.enable_voi:
                            v = self._voi(t, loc_id, n, slack, costs, best_cost)
                            net = urg * v - lam
                        else:
                            # fallback: probe most-uncertain candidate over tau
                            std = self.tm.util_uncertainty(loc_id, n)
                            net = (std - self.p.uncertainty_tau)
                        if net > best_net:
                            best_net, best_probe = net, loc_id

                    if best_probe is None or best_net <= 0:
                        break
                    if not self.tm.observe_location(best_probe, n):
                        break
                    self.tm.observe_link(t.device, best_probe, n)
                    probes.append(best_probe)
                    costs = self._belief_cost(t, n, slack)  # beliefs changed

            placement = min(costs, key=lambda k: costs[k][0])
            return Decision(placement, probes=probes)

        return self._timed(fn, task, now)
