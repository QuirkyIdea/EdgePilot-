"""Statistical aggregation and publication-quality figure generation.

Aggregation reports mean, standard deviation and 95% confidence intervals
(Student-t) across seeds. For the headline algorithm comparison we also run
paired significance tests (Wilcoxon signed-rank, with a paired t-test as a
parametric cross-check) comparing ABVI-Edge against each baseline per seed.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import os

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCHED_LABELS = {
    "local_only": "Local-only", "cloud_only": "Cloud-only", "random": "Random",
    "nearest_edge": "Nearest-edge", "lowest_est_time": "Lowest-est-time",
    "periodic_telemetry": "Periodic-telemetry", "freshness_aware": "Freshness-aware",
    "abvi_edge": "ABVI-Edge (ours)",
}
COLORS = {
    "local_only": "#8c8c8c", "cloud_only": "#4c72b0", "random": "#c44e52",
    "nearest_edge": "#937860", "lowest_est_time": "#dd8452",
    "periodic_telemetry": "#55a868", "freshness_aware": "#8172b3",
    "abvi_edge": "#d62728",
}


def _ci95(x: Sequence[float]):
    x = np.asarray(x, dtype=float)
    n = len(x)
    m = float(np.mean(x)) if n else 0.0
    if n < 2:
        return m, 0.0
    sem = stats.sem(x)
    h = sem * stats.t.ppf(0.975, n - 1)
    return m, float(h)


def aggregate(df: pd.DataFrame, group_cols: List[str],
              metrics: List[str]) -> pd.DataFrame:
    """Group and compute mean/std/ci95 for each metric."""
    rows = []
    for key, g in df.groupby(group_cols):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(group_cols, key))
        row["n_seeds"] = len(g)
        for m in metrics:
            if m not in g:
                continue
            mean, h = _ci95(g[m].values)
            row[f"{m}_mean"] = mean
            row[f"{m}_std"] = float(np.std(g[m].values, ddof=1)) if len(g) > 1 else 0.0
            row[f"{m}_ci95"] = h
        rows.append(row)
    return pd.DataFrame(rows)


def significance_vs_abvi(df: pd.DataFrame, metrics: List[str],
                         ours: str = "abvi_edge") -> pd.DataFrame:
    """Paired tests: ABVI vs each other scheduler, matched by seed."""
    rows = []
    our = df[df.scheduler == ours].set_index("seed")
    for sch in df.scheduler.unique():
        if sch == ours:
            continue
        other = df[df.scheduler == sch].set_index("seed")
        common = our.index.intersection(other.index)
        if len(common) < 3:
            continue
        for m in metrics:
            a = our.loc[common, m].values
            b = other.loc[common, m].values
            diff = b - a  # positive => ABVI better for "lower is better" metrics
            try:
                w_stat, w_p = stats.wilcoxon(a, b)
            except ValueError:
                w_stat, w_p = float("nan"), float("nan")
            t_stat, t_p = stats.ttest_rel(a, b)
            rows.append({
                "metric": m, "vs": sch,
                "abvi_mean": float(np.mean(a)), "other_mean": float(np.mean(b)),
                "mean_improvement": float(np.mean(diff)),
                "pct_improvement": float(100 * np.mean(diff) / (np.mean(b) + 1e-12)),
                "wilcoxon_p": float(w_p), "ttest_p": float(t_p),
                "significant_0.05": bool(t_p < 0.05),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------- plotting
def _savefig(fig, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_algorithm_comparison(df: pd.DataFrame, outdir: str):
    """Grouped bar charts for the headline metrics (Experiment A)."""
    metrics = [
        ("avg_completion", "Avg. completion time (s)"),
        ("p95_completion", "95th-pct completion time (s)"),
        ("deadline_violation_rate", "Deadline violation rate"),
        ("avg_regret", "Avg. scheduling regret (s)"),
        ("avg_energy", "Avg. energy per task (J)"),
        ("monitoring_overhead", "Monitoring overhead (mon./useful bytes)"),
    ]
    order = ["local_only", "cloud_only", "random", "nearest_edge",
             "lowest_est_time", "periodic_telemetry", "freshness_aware", "abvi_edge"]
    present = [s for s in order if s in df.scheduler.values]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, (m, title) in zip(axes.flat, metrics):
        means, errs, cols, labels = [], [], [], []
        for s in present:
            g = df[df.scheduler == s][m]
            mean, h = _ci95(g.values)
            means.append(mean); errs.append(h)
            cols.append(COLORS.get(s, "#333"))
            labels.append(SCHED_LABELS.get(s, s))
        ax.bar(range(len(present)), means, yerr=errs, color=cols, capsize=3)
        ax.set_xticks(range(len(present)))
        ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Experiment A — Algorithm comparison (mean ± 95% CI)", fontsize=13)
    _savefig(fig, os.path.join(outdir, "expA_algorithm_comparison.png"))


def plot_sensitivity(df: pd.DataFrame, xname: str, outdir: str, fname: str,
                     title: str, metrics: Optional[List] = None):
    metrics = metrics or [
        ("avg_completion", "Avg. completion time (s)"),
        ("deadline_violation_rate", "Deadline violation rate"),
        ("avg_regret", "Avg. scheduling regret (s)"),
        ("telemetry_requests", "Telemetry requests"),
    ]
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4))
    if len(metrics) == 1:
        axes = [axes]
    scheds = [s for s in ["cloud_only", "nearest_edge", "lowest_est_time",
                          "periodic_telemetry", "freshness_aware", "abvi_edge"]
              if s in df.scheduler.values]
    for ax, (m, mlabel) in zip(axes, metrics):
        for s in scheds:
            sub = df[df.scheduler == s]
            agg = sub.groupby("x")[m].agg(["mean", "sem"]).reset_index()
            ax.errorbar(agg["x"], agg["mean"],
                        yerr=1.96 * agg["sem"].fillna(0),
                        marker="o", ms=4, capsize=2,
                        color=COLORS.get(s), label=SCHED_LABELS.get(s, s))
        ax.set_xlabel(xname); ax.set_ylabel(mlabel)
        ax.grid(alpha=0.3)
    axes[-1].legend(fontsize=7, loc="best")
    fig.suptitle(title, fontsize=12)
    _savefig(fig, os.path.join(outdir, fname))


def plot_budget_pareto(df: pd.DataFrame, outdir: str):
    """Quality vs monitoring-overhead Pareto (Experiment B)."""
    fig, ax = plt.subplots(figsize=(7, 5.2))
    for s in ["periodic_telemetry", "freshness_aware", "abvi_edge", "lowest_est_time"]:
        if s not in df.scheduler.values:
            continue
        sub = df[df.scheduler == s]
        agg = sub.groupby("x").agg(
            overhead=("telemetry_norm", "mean"),
            comp=("avg_completion", "mean")).reset_index()
        ax.plot(agg["overhead"], agg["comp"], marker="o", ms=5,
                color=COLORS.get(s), label=SCHED_LABELS.get(s, s))
    ax.set_xlabel("Monitoring overhead (normalized telemetry spend)")
    ax.set_ylabel("Avg. completion time (s)")
    ax.set_title("Experiment B — Quality vs monitoring overhead frontier")
    ax.grid(alpha=0.3); ax.legend(fontsize=8)
    _savefig(fig, os.path.join(outdir, "expB_budget_pareto.png"))


def plot_ablation(df: pd.DataFrame, outdir: str):
    metrics = [("avg_completion", "Avg. completion (s)"),
               ("deadline_violation_rate", "Deadline violations"),
               ("avg_regret", "Avg. regret (s)"),
               ("telemetry_requests", "Telemetry requests")]
    order = ["full", "no_voi", "no_budget", "no_urgency",
             "no_uncertainty", "no_adaptive"]
    present = [v for v in order if v in df.variant.values]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.2))
    for ax, (m, title) in zip(axes, metrics):
        means, errs = [], []
        for v in present:
            g = df[df.variant == v][m]
            mean, h = _ci95(g.values)
            means.append(mean); errs.append(h)
        cols = ["#d62728"] + ["#4c72b0"] * (len(present) - 1)
        ax.bar(range(len(present)), means, yerr=errs, color=cols, capsize=3)
        ax.set_xticks(range(len(present)))
        ax.set_xticklabels(present, rotation=35, ha="right", fontsize=8)
        ax.set_title(title, fontsize=10); ax.grid(axis="y", alpha=0.3)
    fig.suptitle("Experiment L — Ablation of ABVI-Edge components (mean ± 95% CI)",
                 fontsize=12)
    _savefig(fig, os.path.join(outdir, "expL_ablation.png"))
