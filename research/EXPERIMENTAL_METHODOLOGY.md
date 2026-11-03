# Experimental Methodology

## 1. Principles

* **Fairness.** For a given seed, every scheduler faces the *same* task arrival
  trace, topology, capacities and ground-truth state evolution. Only the
  decision logic differs. (Test: `tests/test_reproducibility.py::test_identical_task_trace_across_schedulers`.)
* **Reproducibility.** All randomness flows from a single seed. Identical seed →
  bit-identical metrics; the wall-clock decision time is reported separately and
  never folded into simulated completion. (Tests in `test_reproducibility.py`.)
* **No fabrication.** Every number in `results/` is produced by executing
  `backend/run_experiments.py`. Energy is labelled *estimated*.
* **No baseline sabotage.** Estimation baselines use the *same* belief predictor
  and the *same* budget machinery as ABVI-Edge; they differ only in the probe
  policy.

## 2. Metrics (all defined in `backend/edgepilot/metrics.py`)

| Metric | Definition |
|---|---|
| Avg / median / p95 completion | statistics of $T_{k,x_k}$ over post-warmup tasks |
| Deadline violation rate | fraction with $t^{\text{finish}}_k > \delta_k$ |
| Success rate | $1 -$ violation rate |
| Scheduling regret | $T_{k,x_k} - \min_\ell T^{\text{true}}_{k,\ell}$, mean & p95 |
| Edge utilization | mean true edge $u$ over decisions |
| Energy (estimated) | total & per-task joules from the power models |
| Telemetry requests / bytes | probe count and monitoring traffic |
| Telemetry (normalized) | monitoring bytes / $C_{\text{full}}$ |
| Monitoring overhead | monitoring bytes / useful data bytes transferred |
| Avg information age | mean AoI of candidate beliefs at decision time |
| Throughput | completed tasks / simulated second |
| Decision time | wall-clock ms per scheduling decision |

A warmup period (default 10 s) is discarded before aggregation.

## 3. Statistical protocol

* **Repetitions:** 20 independent seeds per configuration (full suite).
* **Reporting:** mean, standard deviation and **95 % confidence intervals**
  (Student-t) via `analysis.aggregate`.
* **Significance:** for the headline comparison (Exp A), ABVI-Edge is compared
  against each baseline with **paired** tests matched by seed — a Wilcoxon
  signed-rank test with a paired t-test cross-check
  (`analysis.significance_vs_abvi`). We report $p$-values and % improvement.

## 4. Baselines (`backend/edgepilot/schedulers/baselines.py`)

| Key | Description | Telemetry |
|---|---|---|
| `local_only` | always execute on the device | none |
| `cloud_only` | always offload to cloud | none |
| `random` | uniform random candidate | none |
| `nearest_edge` | highest-bandwidth edge | none |
| `lowest_est_time` | greedy on belief mean completion (stale) | none |
| `periodic_telemetry` | probe all locations on a fixed period | blind/periodic |
| `freshness_aware` | probe when AoI > threshold | AoI rule |
| `abvi_edge` | **proposed** budgeted VoI policy | adaptive |

`local_only`, `cloud_only`, `random` are naive references; `nearest_edge`,
`lowest_est_time` are heuristic references; `periodic_telemetry`,
`freshness_aware` are the telemetry baselines the contribution is measured
against. Distinction between published-method reimplementations and simplified
reference baselines is stated in the final report.

## 5. Experiments (`backend/run_experiments.py`)

| ID | Name | Independent variable |
|---|---|---|
| A | Algorithm comparison | — (all 8 schedulers) |
| B | Telemetry-budget sensitivity | $\beta \in \{0.02 .. 1.0\}$ |
| C | Workload intensity | task rate $\lambda$ |
| D | Network latency | cloud latency |
| E | Bandwidth | edge access bandwidth |
| F | Deadline tightness | slack factor |
| G | Device count | $N \in \{20,30,40,50\}$ |
| H | Edge count | $M \in \{3,5,7,10\}$ |
| I | Sudden workload spike | preset `spike` |
| J | Network congestion | preset `congestion` |
| K | Edge-server failure | preset `edge_failure` |
| L | Ablation | ABVI component removed |

**Experiment B is the key test of the hypothesis:** it compares ABVI-Edge
against an *always-probe* (periodic) and a *never-adaptively-probe*
(`lowest_est_time`) scheduler across monitoring budgets, and plots the
quality-vs-overhead frontier.

## 6. How to reproduce

```bash
cd backend
pip install -r requirements.txt
python run_experiments.py --seeds 20        # full suite (~10–15 min, parallel)
python run_experiments.py --quick           # 4-seed smoke (~1 min)
pytest -q                                   # 50 validation tests
```

Outputs: `results/raw/*.csv` (per-seed), `results/processed/*_agg.csv`
(aggregates + significance), `results/figures/*.png`,
`results/reports/RESULTS_SUMMARY.md`.
