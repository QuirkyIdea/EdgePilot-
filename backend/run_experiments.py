"""Run the full EdgePilot experimental suite and emit CSVs, figures, reports.

Usage
-----
    python run_experiments.py                 # full suite (20 seeds)
    python run_experiments.py --quick         # fast smoke (4 seeds, exp A/B/L)
    python run_experiments.py --seeds 12 --exp A B L
    python run_experiments.py --no-parallel

Outputs (under ../results):
    raw/<exp>.csv            one row per (scheduler, seed, x) with all metrics
    processed/<exp>_agg.csv  mean/std/95%CI aggregates
    processed/expA_significance.csv  paired ABVI-vs-baseline tests
    figures/*.png            publication-quality charts
    reports/RESULTS_SUMMARY.md
"""
from __future__ import annotations

import argparse
import os
import time

import pandas as pd

from edgepilot import experiments as ex
from edgepilot import analysis as an

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.abspath(os.path.join(HERE, "..", "results"))
RAW = os.path.join(RESULTS, "raw")
PROC = os.path.join(RESULTS, "processed")
FIG = os.path.join(RESULTS, "figures")
REP = os.path.join(RESULTS, "reports")

KEY_METRICS = ["avg_completion", "median_completion", "p95_completion",
               "deadline_violation_rate", "success_rate", "avg_regret",
               "p95_regret", "avg_energy", "total_energy", "telemetry_requests",
               "telemetry_bytes", "telemetry_norm", "monitoring_overhead",
               "avg_info_age", "edge_utilization", "throughput",
               "avg_decision_time_ms", "frac_local", "frac_edge", "frac_cloud"]


def _ensure_dirs():
    for d in (RAW, PROC, FIG, REP):
        os.makedirs(d, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=20)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--exp", nargs="*", default=None,
                    help="subset of A B C D E F G H IJK L")
    ap.add_argument("--no-parallel", action="store_true")
    args = ap.parse_args()

    _ensure_dirs()
    n_seeds = 4 if args.quick else args.seeds
    seeds = list(range(1, n_seeds + 1))
    which = args.exp or (["A", "B", "L"] if args.quick else list(ex.EXPERIMENTS))
    parallel = not args.no_parallel

    print(f"EdgePilot experiments | seeds={n_seeds} | experiments={which} | "
          f"parallel={parallel}")
    results: dict[str, pd.DataFrame] = {}
    t0 = time.perf_counter()

    for key in which:
        if key not in ex.EXPERIMENTS:
            print(f"  [skip] unknown experiment {key}")
            continue
        jobs = ex.EXPERIMENTS[key](seeds)
        print(f"  [exp {key}] {len(jobs)} runs ...", flush=True)
        ts = time.perf_counter()
        df = ex.run_jobs(jobs, parallel=parallel)
        df.to_csv(os.path.join(RAW, f"exp{key}.csv"), index=False)
        results[key] = df
        print(f"           done in {time.perf_counter()-ts:.1f}s "
              f"-> raw/exp{key}.csv")

    # ---- aggregate + figures ------------------------------------------
    if "A" in results:
        df = results["A"]
        an.aggregate(df, ["scheduler"], KEY_METRICS).to_csv(
            os.path.join(PROC, "expA_agg.csv"), index=False)
        an.significance_vs_abvi(
            df, ["avg_completion", "p95_completion", "deadline_violation_rate",
                 "avg_regret", "avg_energy"]).to_csv(
            os.path.join(PROC, "expA_significance.csv"), index=False)
        an.plot_algorithm_comparison(df, FIG)

    if "B" in results:
        df = results["B"]
        an.aggregate(df, ["scheduler", "x"], KEY_METRICS).to_csv(
            os.path.join(PROC, "expB_agg.csv"), index=False)
        an.plot_sensitivity(df, "Telemetry budget (normalized)", FIG,
                            "expB_budget_sensitivity.png",
                            "Experiment B — Telemetry budget sensitivity")
        an.plot_budget_pareto(df, FIG)

    sens = {
        "C": ("Task arrival rate (tasks/s)", "Experiment C — Workload intensity"),
        "D": ("Cloud one-way latency (s)", "Experiment D — Network latency"),
        "E": ("Edge access bandwidth (Mb/s)", "Experiment E — Bandwidth"),
        "F": ("Deadline slack factor", "Experiment F — Deadline tightness"),
        "G": ("Number of devices", "Experiment G — Device count"),
        "H": ("Number of edge servers", "Experiment H — Edge count"),
    }
    for key, (xlabel, title) in sens.items():
        if key in results:
            df = results[key]
            an.aggregate(df, ["scheduler", "x"], KEY_METRICS).to_csv(
                os.path.join(PROC, f"exp{key}_agg.csv"), index=False)
            an.plot_sensitivity(df, xlabel, FIG,
                               f"exp{key}_sensitivity.png", title)

    if "IJK" in results:
        df = results["IJK"]
        an.aggregate(df, ["experiment", "scheduler"], KEY_METRICS).to_csv(
            os.path.join(PROC, "expIJK_agg.csv"), index=False)
        for exp_id, scen in [("I", "spike"), ("J", "congestion"), ("K", "edge_failure")]:
            sub = df[df.experiment == exp_id]
            if len(sub):
                an.plot_algorithm_comparison(sub, FIG + f"/_tmp")
                os.replace(os.path.join(FIG, "_tmp", "expA_algorithm_comparison.png"),
                           os.path.join(FIG, f"exp{exp_id}_{scen}.png"))
        try:
            os.rmdir(os.path.join(FIG, "_tmp"))
        except OSError:
            pass

    if "L" in results:
        df = results["L"]
        an.aggregate(df, ["variant"], KEY_METRICS).to_csv(
            os.path.join(PROC, "expL_agg.csv"), index=False)
        an.plot_ablation(df, FIG)

    _write_summary(results)
    print(f"\nALL DONE in {time.perf_counter()-t0:.1f}s. Results under {RESULTS}")


def _write_summary(results: dict):
    lines = ["# EdgePilot — Experimental Results Summary\n",
             "_Auto-generated from real simulation runs. All numbers are means "
             "across seeds unless noted._\n"]

    if "A" in results:
        df = results["A"]
        agg = an.aggregate(df, ["scheduler"],
                           ["avg_completion", "p95_completion",
                            "deadline_violation_rate", "avg_regret", "avg_energy",
                            "telemetry_requests", "avg_decision_time_ms"])
        order = ["local_only", "cloud_only", "random", "nearest_edge",
                 "lowest_est_time", "periodic_telemetry", "freshness_aware", "abvi_edge"]
        agg["__o"] = agg["scheduler"].apply(lambda s: order.index(s) if s in order else 99)
        agg = agg.sort_values("__o")
        lines.append("## Experiment A — Algorithm comparison\n")
        lines.append("| Scheduler | Completion (s) | p95 (s) | Violations | "
                     "Regret (s) | Energy (J) | Telemetry | Decide (ms) |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for _, r in agg.iterrows():
            lines.append(
                f"| {an.SCHED_LABELS.get(r['scheduler'], r['scheduler'])} "
                f"| {r['avg_completion_mean']:.3f} ± {r['avg_completion_ci95']:.3f} "
                f"| {r['p95_completion_mean']:.3f} "
                f"| {r['deadline_violation_rate_mean']:.3f} "
                f"| {r['avg_regret_mean']:.4f} "
                f"| {r['avg_energy_mean']:.3f} "
                f"| {r['telemetry_requests_mean']:.0f} "
                f"| {r['avg_decision_time_ms_mean']:.3f} |")
        sig_path = os.path.join(PROC, "expA_significance.csv")
        if os.path.exists(sig_path):
            sig = pd.read_csv(sig_path)
            lines.append("\n### Paired significance (ABVI-Edge vs baselines)\n")
            lines.append("| Metric | vs | ABVI | Baseline | Improvement % | t-test p | sig? |")
            lines.append("|---|---|---|---|---|---|---|")
            for _, r in sig.iterrows():
                lines.append(
                    f"| {r['metric']} | {an.SCHED_LABELS.get(r['vs'], r['vs'])} "
                    f"| {r['abvi_mean']:.3f} | {r['other_mean']:.3f} "
                    f"| {r['pct_improvement']:+.1f}% | {r['ttest_p']:.2e} "
                    f"| {'yes' if r['significant_0.05'] else 'no'} |")

    if "L" in results:
        agg = an.aggregate(results["L"], ["variant"],
                           ["avg_completion", "deadline_violation_rate",
                            "avg_regret", "telemetry_requests"])
        lines.append("\n## Experiment L — Ablation\n")
        lines.append("| Variant | Completion (s) | Violations | Regret (s) | Telemetry |")
        lines.append("|---|---|---|---|---|")
        for _, r in agg.iterrows():
            lines.append(
                f"| {r['variant']} | {r['avg_completion_mean']:.3f} "
                f"| {r['deadline_violation_rate_mean']:.3f} "
                f"| {r['avg_regret_mean']:.4f} "
                f"| {r['telemetry_requests_mean']:.0f} |")

    with open(os.path.join(REP, "RESULTS_SUMMARY.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
