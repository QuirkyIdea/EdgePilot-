"""Execution-time prediction under uncertainty.

Schedulers never see the true environment; they predict a task's completion
time on each candidate location from the (possibly stale) belief state.

Two predictors are provided and compared experimentally (Experiment on
prediction quality, and the ablation ``no-uncertainty``):

* :class:`AnalyticPredictor` — a white-box queueing/transfer model that
  propagates belief **uncertainty** by Monte-Carlo sampling the predictive
  distributions of utilization and link congestion. It returns both the
  expected completion time and the deadline-violation probability. This is the
  default used by ABVI-Edge because the VoI computation needs a calibrated
  notion of uncertainty, which a point-estimate ML regressor does not provide.

* :class:`MLPredictor` — a scikit-learn gradient-boosted regressor trained on
  realized (features -> completion time) traces. Used to demonstrate that a
  learned point predictor is competitive on *accuracy* but, lacking a
  calibrated predictive variance, cannot by itself drive value-of-information
  decisions. This justifies the analytic model rather than adding ML for show.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import math

import numpy as np

from .config import ScenarioConfig
from .entities import Task, Location, LocType
from .telemetry import TelemetryManager


@dataclass
class Prediction:
    loc: Location
    mean_time: float          # expected completion time (s, relative to now)
    std_time: float           # std of completion time under belief
    deadline_prob: float      # P(finish <= deadline)
    expected_energy: float


class AnalyticPredictor:
    """Belief-aware predictor that propagates uncertainty by sampling."""

    def __init__(self, cfg: ScenarioConfig, n_samples: int = 24):
        self.cfg = cfg
        self.n_samples = n_samples
        self._rng = np.random.default_rng(12345)

    def _sample_util(self, tm: TelemetryManager, loc_id: str, now: float,
                     n: int) -> np.ndarray:
        b = tm.util_belief[loc_id]
        mean = b.predict_mean(now)
        std = b.predict_std(now)
        if std < 1e-6:
            return np.full(n, mean)
        s = self._rng.normal(mean, std, n)
        return np.clip(s, 0.0, 0.95)

    def _sample_cong(self, tm: TelemetryManager, device: int, loc_id: str,
                     now: float, n: int) -> np.ndarray:
        b = tm.cong_belief.get((device, loc_id))
        if b is None:
            return np.ones(n)
        mean = max(b.predict_mean(now), 0.3)
        std = b.predict_std(now)
        if std < 1e-6:
            return np.full(n, mean)
        s = self._rng.normal(mean, std, n)
        return np.clip(s, 0.3, 8.0)

    def predict(self, task: Task, loc: Location, tm: TelemetryManager,
                env, now: float, remaining_slack: float) -> Prediction:
        """Predict completion-time distribution for ``task`` on ``loc``.

        ``remaining_slack`` is ``deadline - now`` used for the deadline prob.
        """
        cfg = self.cfg
        n = self.n_samples
        if loc.failed or loc.capacity <= 0:
            return Prediction(loc, float("inf"), 0.0, 0.0, float("inf"))

        us = self._sample_util(tm, loc.loc_id, now, n)
        compute = (task.demand / loc.capacity) / (1.0 - us)

        if loc.loc_type == LocType.LOCAL:
            total = compute
            # local energy (device compute power)
            energy = cfg.device_compute_power * float(np.mean(compute))
        else:
            link = env.link_for(task.device, loc.loc_id)
            if link is None:
                return Prediction(loc, float("inf"), 0.0, 0.0, float("inf"))
            cong = self._sample_cong(tm, task.device, loc.loc_id, now, n)
            eff_bw = np.maximum(link.base_bw / cong, 1e-3)
            lat = link.base_latency * cong
            tx = (task.input_size + task.output_size) / eff_bw + 2 * lat
            total = tx + compute
            device_e = cfg.device_tx_power * float(np.mean(tx)) \
                + cfg.device_idle_power * float(np.mean(compute))
            energy = device_e + loc.compute_energy * task.demand

        mean_t = float(np.mean(total))
        std_t = float(np.std(total))
        deadline_prob = float(np.mean(total <= remaining_slack))
        return Prediction(loc, mean_t, std_t, deadline_prob, energy)

    def predict_all(self, task: Task, tm: TelemetryManager, env, now: float
                    ) -> List[Prediction]:
        slack = task.deadline - now
        return [self.predict(task, loc, tm, env, now, slack)
                for loc in env.candidate_locations(task)]


# --------------------------------------------------------------------------
# Optional learned predictor (scikit-learn). Used for the prediction-quality
# comparison; not required for the core scheduler to run.
# --------------------------------------------------------------------------
class MLPredictor:
    """Gradient-boosted regressor for completion time (point estimate).

    Trained from realized traces collected during a warmup simulation. Provides
    ``predict_point`` only — it has no calibrated predictive variance, which is
    precisely why ABVI-Edge relies on the analytic model for VoI.
    """

    FEATURES = ["demand", "input", "output", "capacity", "u_est",
                "cong_est", "is_local", "is_cloud"]

    def __init__(self):
        self.model = None
        self.trained = False

    def _featurize(self, task: Task, loc: Location, tm: TelemetryManager,
                   now: float) -> List[float]:
        is_local = 1.0 if loc.loc_type == LocType.LOCAL else 0.0
        is_cloud = 1.0 if loc.loc_type == LocType.CLOUD else 0.0
        cong = 1.0 if loc.loc_type == LocType.LOCAL else tm.est_congestion(
            task.device, loc.loc_id, now)
        return [task.demand, task.input_size, task.output_size, loc.capacity,
                tm.est_utilization(loc.loc_id, now), cong, is_local, is_cloud]

    def fit(self, X: List[List[float]], y: List[float]) -> None:
        from sklearn.ensemble import GradientBoostingRegressor
        if len(y) < 20:
            return
        self.model = GradientBoostingRegressor(
            n_estimators=120, max_depth=3, learning_rate=0.08, subsample=0.9,
            random_state=0)
        self.model.fit(np.array(X), np.array(y))
        self.trained = True

    def predict_point(self, task: Task, loc: Location, tm: TelemetryManager,
                      now: float) -> float:
        if not self.trained or self.model is None:
            return float("inf")
        x = np.array([self._featurize(task, loc, tm, now)])
        return float(self.model.predict(x)[0])
