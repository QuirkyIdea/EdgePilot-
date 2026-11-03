"""The simulated edge-cloud environment.

Holds the *ground-truth* dynamic state (server utilizations, link congestion)
and advances it over time with mean-reverting stochastic processes. Also
generates the task arrival trace and builds a NetworkX topology.

The environment exposes ``true_*`` query methods used both for (a) realized
task execution and (b) the omniscient *oracle* used to measure scheduling
regret. The scheduler itself must go through :mod:`telemetry` to observe this
state (possibly stale), which is what makes telemetry acquisition meaningful.
"""
from __future__ import annotations

from typing import Dict, List, Tuple
import math

import numpy as np
import networkx as nx

from .config import ScenarioConfig
from .entities import Task, Location, LocType


class Link:
    """A device<->edge (or device<->cloud) network link with dynamic congestion."""

    def __init__(self, base_bw: float, base_latency: float, loss: float):
        self.base_bw = base_bw
        self.base_latency = base_latency
        self.loss = loss
        self.congestion = 1.0  # multiplicative factor on latency, divisor on bw

    def transfer_time(self, size_mb: float) -> float:
        """One-way transfer time for ``size_mb`` given current congestion."""
        eff_bw = max(self.base_bw / self.congestion, 1e-3)
        lat = self.base_latency * self.congestion
        t = size_mb / eff_bw + lat
        if self.loss > 0:
            # expected retransmission inflation under independent loss
            t *= 1.0 / max(1.0 - self.loss, 0.2)
        return t


class Environment:
    """Ground-truth world state and its temporal evolution."""

    def __init__(self, cfg: ScenarioConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.t = 0.0

        self.locations: Dict[str, Location] = {}
        self.edges: List[Location] = []
        self.devices: List[Location] = []
        self.cloud: Location

        self._build_topology()
        self.tasks: List[Task] = self._generate_tasks()

    # ------------------------------------------------------------------ build
    def _build_topology(self) -> None:
        cfg = self.cfg
        rng = self.rng
        self.graph = nx.Graph()

        # Devices (local execution locations)
        for i in range(cfg.n_devices):
            cap = max(
                _lognormal(rng, cfg.device_capacity_mean, cfg.device_capacity_cv),
                50.0,
            )
            loc = Location(
                loc_id=f"local:{i}", loc_type=LocType.LOCAL, index=i,
                capacity=cap, compute_energy=0.0, u_mean=cfg.load_mean * 0.6,
            )
            loc.u_true = max(0.0, rng.normal(loc.u_mean, cfg.load_sigma * 0.5))
            self.devices.append(loc)
            self.locations[loc.loc_id] = loc
            self.graph.add_node(loc.loc_id, kind="device")

        # Edge servers (heterogeneous)
        for j in range(cfg.n_edges):
            cap = max(
                _lognormal(rng, cfg.edge_capacity_mean, cfg.edge_capacity_cv),
                500.0,
            )
            loc = Location(
                loc_id=f"edge:{j}", loc_type=LocType.EDGE, index=j,
                capacity=cap, compute_energy=cfg.edge_compute_energy,
                u_mean=cfg.load_mean,
            )
            loc.u_true = max(0.0, rng.normal(cfg.load_mean, cfg.load_sigma))
            self.edges.append(loc)
            self.locations[loc.loc_id] = loc
            self.graph.add_node(loc.loc_id, kind="edge")

        # Cloud
        self.cloud = Location(
            loc_id="cloud", loc_type=LocType.CLOUD, index=-1,
            capacity=cfg.cloud_capacity, compute_energy=cfg.cloud_compute_energy,
            u_mean=cfg.load_mean * 0.5,
        )
        self.cloud.u_true = max(0.0, rng.normal(self.cloud.u_mean, cfg.load_sigma * 0.5))
        self.locations["cloud"] = self.cloud
        self.graph.add_node("cloud", kind="cloud")

        # Links: each device connects to every edge and the cloud.
        self.links: Dict[Tuple[int, str], Link] = {}
        for i in range(cfg.n_devices):
            for j in range(cfg.n_edges):
                bw = max(_lognormal(rng, cfg.edge_bw_mean, cfg.edge_bw_cv), 2.0)
                lat = max(rng.normal(cfg.edge_latency_mean, cfg.edge_latency_mean * 0.3), 1e-3)
                link = Link(bw, lat, cfg.packet_loss_prob)
                self.links[(i, f"edge:{j}")] = link
                self.graph.add_edge(f"local:{i}", f"edge:{j}", bw=bw, latency=lat)
            cloud_link = Link(cfg.cloud_bandwidth, cfg.cloud_base_latency, cfg.packet_loss_prob)
            self.links[(i, "cloud")] = cloud_link
            self.graph.add_edge(f"local:{i}", "cloud", bw=cfg.cloud_bandwidth,
                                latency=cfg.cloud_base_latency)

    def _generate_tasks(self) -> List[Task]:
        cfg = self.cfg
        rng = self.rng
        tasks: List[Task] = []
        t = 0.0
        tid = 0
        while t < cfg.sim_time:
            # Poisson arrivals: exponential inter-arrival times.
            t += rng.exponential(1.0 / cfg.task_rate)
            if t >= cfg.sim_time:
                break
            dev = int(rng.integers(0, cfg.n_devices))
            demand = max(_lognormal(rng, cfg.demand_mean, cfg.demand_cv), 10.0)
            inp = max(_lognormal(rng, cfg.input_mean, 0.5), 0.1)
            out = inp * cfg.output_ratio
            priority = 2 if rng.random() < cfg.priority_high_frac else 1
            # Deadline relative to a scheduler-independent reference: the
            # completion time on a *nominally loaded* edge (mean utilization,
            # mean bandwidth). This makes deadlines meaningful and sometimes
            # tight, so that choosing a currently-uncongested edge (which needs
            # fresh telemetry) genuinely matters.
            edge_ref = (demand / cfg.edge_capacity_mean) / (1.0 - cfg.load_mean) \
                + (inp + out) / cfg.edge_bw_mean + cfg.edge_latency_mean * 2
            cloud_ref = demand / cfg.cloud_capacity \
                + (inp + out) / cfg.cloud_bandwidth + cfg.cloud_base_latency * 2
            fastest = min(edge_ref, cloud_ref)
            slack = max(_lognormal(rng, cfg.deadline_slack_mean, cfg.deadline_slack_cv), 1.05)
            deadline = t + max(fastest * slack, 0.05)
            tasks.append(Task(
                tid=tid, device=dev, arrival=t, demand=demand,
                input_size=inp, output_size=out, deadline=deadline,
                priority=priority, local_capable=True,
            ))
            tid += 1
        return tasks

    # ------------------------------------------------------------- dynamics
    def advance_to(self, t_target: float) -> None:
        """Advance ground-truth state from ``self.t`` up to ``t_target``."""
        cfg = self.cfg
        rng = self.rng
        while self.t < t_target - 1e-9:
            step = min(cfg.dt, t_target - self.t)
            self._evolve(step)
            self.t += step

        # Deterministic edge failure event.
        if cfg.edge_failure_time >= 0 and self.t >= cfg.edge_failure_time:
            idx = cfg.failed_edge_index
            if 0 <= idx < len(self.edges):
                self.edges[idx].failed = True

    def _evolve(self, step: float) -> None:
        cfg = self.cfg
        rng = self.rng
        theta = cfg.load_theta
        # Ornstein-Uhlenbeck discretization for utilizations.
        for loc in list(self.locations.values()):
            if loc.failed:
                continue
            mu = loc.u_mean
            sigma = cfg.load_sigma
            drift = theta * (mu - loc.u_true) * step
            diffusion = sigma * math.sqrt(2 * theta * step) * rng.standard_normal()
            loc.u_true = min(max(loc.u_true + drift + diffusion, 0.0), 0.98)
            # Occasional load spikes.
            if cfg.load_spike_prob > 0 and rng.random() < cfg.load_spike_prob * step:
                loc.u_true = min(loc.u_true + cfg.load_spike_mag, 0.98)

        # Link congestion mean-reverts toward 1.0 (multiplicative, log-space).
        ltheta = cfg.link_congestion_theta
        lsigma = cfg.link_congestion_sigma
        for link in self.links.values():
            x = math.log(link.congestion)
            drift = ltheta * (0.0 - x) * step
            diffusion = lsigma * math.sqrt(2 * ltheta * step) * rng.standard_normal()
            x = x + drift + diffusion
            link.congestion = float(min(max(math.exp(x), 0.3), 8.0))

    # --------------------------------------------------------- ground truth
    def link_for(self, device: int, loc_id: str) -> Link | None:
        if loc_id.startswith("local"):
            return None
        return self.links.get((device, loc_id))

    def true_completion_time(self, task: Task, loc: Location) -> float:
        """Realized completion time (relative to now) if executing on ``loc``.

        Uses the *true* current environment state; used for realized execution
        and for the omniscient oracle. Transfer + compute (no server queue
        beyond the utilization sojourn scaling)."""
        if loc.failed or loc.capacity <= 0:
            return float("inf")
        compute = loc.effective_time(task.demand)
        if loc.loc_type == LocType.LOCAL:
            return compute
        link = self.link_for(task.device, loc.loc_id)
        if link is None:
            return float("inf")
        tx = link.transfer_time(task.input_size) + link.transfer_time(task.output_size)
        return tx + compute

    def true_energy(self, task: Task, loc: Location) -> float:
        """Estimated joules for running ``task`` on ``loc`` (device + server)."""
        cfg = self.cfg
        if loc.loc_type == LocType.LOCAL:
            return cfg.device_compute_power * loc.effective_time(task.demand)
        link = self.link_for(task.device, loc.loc_id)
        tx_time = 0.0 if link is None else (
            link.transfer_time(task.input_size) + link.transfer_time(task.output_size))
        device_e = cfg.device_tx_power * tx_time \
            + cfg.device_idle_power * loc.effective_time(task.demand)
        server_e = loc.compute_energy * task.demand
        return device_e + server_e

    def candidate_locations(self, task: Task) -> List[Location]:
        locs: List[Location] = []
        if task.local_capable:
            locs.append(self.devices[task.device])
        locs.extend([e for e in self.edges])
        locs.append(self.cloud)
        return locs

    def oracle_completion(self, task: Task) -> Tuple[str, float]:
        """Best achievable completion time with full fresh knowledge."""
        best_id, best_t = "cloud", float("inf")
        for loc in self.candidate_locations(task):
            t = self.true_completion_time(task, loc)
            if t < best_t:
                best_t, best_id = t, loc.loc_id
        return best_id, best_t


def _lognormal(rng: np.random.Generator, mean: float, cv: float) -> float:
    """Draw a positive value with given mean and coefficient of variation."""
    if cv <= 0:
        return mean
    sigma2 = math.log(1.0 + cv * cv)
    mu = math.log(mean) - 0.5 * sigma2
    return float(rng.lognormal(mu, math.sqrt(sigma2)))
