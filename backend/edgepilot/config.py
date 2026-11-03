"""Scenario and simulation configuration.

All randomness is driven by an explicit ``seed`` so every experiment is
reproducible. A :class:`ScenarioConfig` fully determines a simulation run
together with the chosen scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any
import math


@dataclass
class ScenarioConfig:
    """Fully specifies a reproducible simulation scenario.

    Units
    -----
    * Time is in seconds.
    * Computational demand is in megacycles (Mcyc); capacity in Mcyc/s.
    * Data sizes are in megabits (Mb); bandwidth in Mb/s; latency in seconds.
    * Energy is in joules (estimated, not measured on hardware).
    """

    name: str = "baseline"
    seed: int = 0

    # ---- Topology -----------------------------------------------------------
    n_devices: int = 30                 # 20..50 virtual end devices
    n_edges: int = 5                    # 3..10 heterogeneous edge servers
    # Cloud is always a single remote server.

    # ---- Simulation horizon -------------------------------------------------
    sim_time: float = 300.0             # total simulated seconds
    dt: float = 0.1                     # state-evolution tick for env dynamics
    task_rate: float = 6.0              # mean task arrivals per second (Poisson)

    # ---- Task distribution --------------------------------------------------
    demand_mean: float = 1500.0         # mean compute demand (Mcyc)
    demand_cv: float = 0.6              # coefficient of variation
    input_mean: float = 8.0             # mean input size (Mb)
    output_ratio: float = 0.2           # output size as fraction of input
    deadline_slack_mean: float = 2.2    # deadline = slack * fastest-feasible time
    deadline_slack_cv: float = 0.35
    priority_high_frac: float = 0.25    # fraction of high-priority tasks

    # ---- Device compute -----------------------------------------------------
    device_capacity_mean: float = 900.0     # Mcyc/s (weak local CPUs)
    device_capacity_cv: float = 0.25
    device_tx_power: float = 0.5            # W radio transmit power
    device_compute_power: float = 1.2       # W local compute power
    device_idle_power: float = 0.05         # W

    # ---- Edge compute -------------------------------------------------------
    edge_capacity_mean: float = 12000.0     # Mcyc/s
    edge_capacity_cv: float = 0.5           # heterogeneity across edges
    edge_compute_energy: float = 3.5e-4     # J per Mcyc (server-side estimate)

    # ---- Cloud compute ------------------------------------------------------
    cloud_capacity: float = 40000.0         # Mcyc/s (very fast but far)
    cloud_compute_energy: float = 2.0e-4    # J per Mcyc
    cloud_base_latency: float = 0.10        # s one-way WAN propagation
    cloud_bandwidth: float = 50.0           # Mb/s WAN bandwidth

    # ---- Dynamic server load (Ornstein-Uhlenbeck-like mean reverting) -------
    # Edges are fast when idle but their background load is volatile, so a
    # congested edge is much worse than the cloud -- which is exactly why fresh
    # telemetry about edge utilization carries real value.
    load_mean: float = 0.50                 # stationary mean utilization
    load_sigma: float = 0.28                # stationary std of utilization
    load_theta: float = 0.50                # mean-reversion speed (per second)
    load_spike_prob: float = 0.0            # per-second prob of a load spike
    load_spike_mag: float = 0.4             # added utilization on spike

    # ---- Network links (device<->edge) --------------------------------------
    edge_bw_mean: float = 60.0              # Mb/s access bandwidth
    edge_bw_cv: float = 0.4
    edge_latency_mean: float = 0.012        # s one-way
    link_congestion_sigma: float = 0.3      # multiplicative congestion std
    link_congestion_theta: float = 0.4      # mean reversion speed
    packet_loss_prob: float = 0.0           # base loss (retransmit penalty)

    # ---- Telemetry / monitoring ---------------------------------------------
    telemetry_budget: float = 0.30          # normalized budget in [0, inf);
    #   expressed as fraction of "observe-everything-every-decision" cost.
    telemetry_req_bytes: float = 0.02       # Mb transferred per telemetry probe
    telemetry_latency: float = 0.004        # s added when a probe is issued
    telemetry_noise: float = 0.02           # measurement noise std on utilization
    telemetry_budget_window: float = -1.0   # seconds; <=0 means "use sim_time"

    # ---- Faults -------------------------------------------------------------
    edge_failure_time: float = -1.0         # if >=0, one edge fails at this time
    failed_edge_index: int = 0

    # ---- Misc ---------------------------------------------------------------
    warmup_time: float = 10.0               # discard metrics before this time

    def __post_init__(self) -> None:
        # Budget window defaults to the full simulated horizon.
        if self.telemetry_budget_window is None or self.telemetry_budget_window <= 0:
            self.telemetry_budget_window = self.sim_time

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ScenarioConfig":
        known = {f for f in cls().__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


# ---- Named preset scenarios (Phase 4 requirement) --------------------------

def scenario_presets() -> Dict[str, ScenarioConfig]:
    """Return the 10 required evaluation scenarios."""
    presets: Dict[str, ScenarioConfig] = {}

    presets["light"] = ScenarioConfig(name="light", task_rate=3.0)
    presets["medium"] = ScenarioConfig(name="medium", task_rate=6.0)
    presets["heavy"] = ScenarioConfig(name="heavy", task_rate=11.0, load_mean=0.6)
    presets["spike"] = ScenarioConfig(
        name="spike", task_rate=6.0, load_spike_prob=0.01, load_spike_mag=0.45
    )
    presets["congestion"] = ScenarioConfig(
        name="congestion", link_congestion_sigma=0.6, edge_bw_mean=30.0
    )
    presets["edge_failure"] = ScenarioConfig(
        name="edge_failure", edge_failure_time=120.0, failed_edge_index=0
    )
    presets["heterogeneous"] = ScenarioConfig(
        name="heterogeneous", edge_capacity_cv=0.8, device_capacity_cv=0.5
    )
    presets["tight_deadline"] = ScenarioConfig(
        name="tight_deadline", deadline_slack_mean=1.3, deadline_slack_cv=0.2
    )
    presets["limited_budget"] = ScenarioConfig(
        name="limited_budget", telemetry_budget=0.15
    )
    presets["volatile_network"] = ScenarioConfig(
        name="volatile_network",
        link_congestion_theta=0.8, link_congestion_sigma=0.5,
        load_theta=0.6, load_sigma=0.3,
    )
    return presets
