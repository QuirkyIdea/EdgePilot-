# EdgePilot — Experimental Results Summary

_Auto-generated from real simulation runs. All numbers are means across seeds unless noted._

## Experiment A — Algorithm comparison

| Scheduler | Completion (s) | p95 (s) | Violations | Regret (s) | Energy (J) | Telemetry | Decide (ms) |
|---|---|---|---|---|---|---|---|
| Local-only | 3.626 ± 0.134 | 9.672 | 0.953 | 3.3076 | 4.352 | 0 | 0.002 |
| Cloud-only | 0.479 ± 0.004 | 0.816 | 0.119 | 0.1604 | 0.509 | 0 | 0.001 |
| Random | 1.138 ± 0.047 | 3.761 | 0.356 | 0.8178 | 1.187 | 0 | 0.010 |
| Nearest-edge | 0.646 ± 0.059 | 1.825 | 0.205 | 0.3276 | 0.622 | 0 | 0.004 |
| Lowest-est-time | 0.431 ± 0.015 | 0.848 | 0.084 | 0.1124 | 0.530 | 0 | 0.720 |
| Periodic-telemetry | 0.361 ± 0.014 | 0.668 | 0.034 | 0.0431 | 0.569 | 1033 | 0.694 |
| Freshness-aware | 0.374 ± 0.014 | 0.699 | 0.041 | 0.0535 | 0.563 | 719 | 0.687 |
| ABVI-Edge (ours) | 0.326 ± 0.013 | 0.568 | 0.010 | 0.0074 | 0.561 | 1838 | 2.859 |

### Paired significance (ABVI-Edge vs baselines)

| Metric | vs | ABVI | Baseline | Improvement % | t-test p | sig? |
|---|---|---|---|---|---|---|
| avg_completion | Local-only | 0.326 | 3.626 | +91.0% | 5.16e-22 | yes |
| p95_completion | Local-only | 0.568 | 9.672 | +94.1% | 5.22e-20 | yes |
| deadline_violation_rate | Local-only | 0.010 | 0.953 | +99.0% | 2.70e-37 | yes |
| avg_regret | Local-only | 0.007 | 3.308 | +99.8% | 6.31e-22 | yes |
| avg_energy | Local-only | 0.561 | 4.352 | +87.1% | 1.81e-21 | yes |
| avg_completion | Cloud-only | 0.326 | 0.479 | +31.9% | 8.39e-16 | yes |
| p95_completion | Cloud-only | 0.568 | 0.816 | +30.4% | 4.53e-15 | yes |
| deadline_violation_rate | Cloud-only | 0.010 | 0.119 | +91.9% | 4.10e-18 | yes |
| avg_regret | Cloud-only | 0.007 | 0.160 | +95.4% | 5.63e-16 | yes |
| avg_energy | Cloud-only | 0.561 | 0.509 | -10.2% | 7.00e-11 | yes |
| avg_completion | Random | 0.326 | 1.138 | +71.3% | 1.78e-19 | yes |
| p95_completion | Random | 0.568 | 3.761 | +84.9% | 9.99e-21 | yes |
| deadline_violation_rate | Random | 0.010 | 0.356 | +97.3% | 3.94e-19 | yes |
| avg_regret | Random | 0.007 | 0.818 | +99.1% | 1.07e-19 | yes |
| avg_energy | Random | 0.561 | 1.187 | +52.8% | 5.83e-17 | yes |
| avg_completion | Nearest-edge | 0.326 | 0.646 | +49.5% | 4.09e-11 | yes |
| p95_completion | Nearest-edge | 0.568 | 1.825 | +68.9% | 2.60e-11 | yes |
| deadline_violation_rate | Nearest-edge | 0.010 | 0.205 | +95.3% | 1.41e-11 | yes |
| avg_regret | Nearest-edge | 0.007 | 0.328 | +97.7% | 3.77e-11 | yes |
| avg_energy | Nearest-edge | 0.561 | 0.622 | +9.9% | 5.64e-10 | yes |
| avg_completion | Lowest-est-time | 0.326 | 0.431 | +24.4% | 2.30e-16 | yes |
| p95_completion | Lowest-est-time | 0.568 | 0.848 | +33.0% | 6.65e-14 | yes |
| deadline_violation_rate | Lowest-est-time | 0.010 | 0.084 | +88.5% | 2.00e-13 | yes |
| avg_regret | Lowest-est-time | 0.007 | 0.112 | +93.4% | 7.62e-17 | yes |
| avg_energy | Lowest-est-time | 0.561 | 0.530 | -5.8% | 2.06e-11 | yes |
| avg_completion | Periodic-telemetry | 0.326 | 0.361 | +9.8% | 2.41e-14 | yes |
| p95_completion | Periodic-telemetry | 0.568 | 0.668 | +14.9% | 1.22e-13 | yes |
| deadline_violation_rate | Periodic-telemetry | 0.010 | 0.034 | +71.7% | 7.99e-12 | yes |
| avg_regret | Periodic-telemetry | 0.007 | 0.043 | +82.8% | 4.03e-19 | yes |
| avg_energy | Periodic-telemetry | 0.561 | 0.569 | +1.5% | 1.74e-07 | yes |
| avg_completion | Freshness-aware | 0.326 | 0.374 | +12.7% | 2.34e-15 | yes |
| p95_completion | Freshness-aware | 0.568 | 0.699 | +18.8% | 7.76e-18 | yes |
| deadline_violation_rate | Freshness-aware | 0.010 | 0.041 | +76.4% | 2.17e-11 | yes |
| avg_regret | Freshness-aware | 0.007 | 0.053 | +86.1% | 9.21e-19 | yes |
| avg_energy | Freshness-aware | 0.561 | 0.563 | +0.4% | 1.12e-01 | no |

## Experiment L — Ablation

| Variant | Completion (s) | Violations | Regret (s) | Telemetry |
|---|---|---|---|---|
| full | 0.330 | 0.009 | 0.0097 | 1672 |
| no_adaptive | 0.440 | 0.077 | 0.1210 | 0 |
| no_budget | 0.328 | 0.010 | 0.0080 | 1773 |
| no_uncertainty | 0.432 | 0.089 | 0.1133 | 0 |
| no_urgency | 0.332 | 0.012 | 0.0132 | 1341 |
| no_voi | 0.386 | 0.046 | 0.0652 | 2159 |
