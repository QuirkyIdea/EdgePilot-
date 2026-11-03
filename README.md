# EdgePilot — Adaptive Telemetry-Budgeted Intelligent Task Offloading

A reproducible, simulation-based research platform for studying the **joint
optimisation of task placement and telemetry (monitoring) acquisition** under an
explicit monitoring budget in dynamic edge–cloud environments.

> **Research question.** Can a value-of-information-driven scheduling policy
> jointly optimise *task placement* and *telemetry acquisition* under a
> constrained monitoring budget, while maintaining acceptable task-execution
> performance in dynamic edge computing environments?

The proposed scheduler — **ABVI-Edge** (Adaptive Budgeted Value-of-Information
Edge scheduler) — decides, per task, *where* to run it and *whether it is worth
spending scarce telemetry budget* to refresh its view of the network and server
state before committing.

No physical devices are needed: everything runs in a discrete-event simulator.

> 🟢 **New to the topic?** Read **[GUIDE.md](GUIDE.md)** first — a plain-language,
> beginner-friendly walkthrough of the problem, the algorithm and the results
> (no prior edge-computing knowledge needed), written to help you explain the
> project in your own words.

---

## What's inside

```
Hema_Proj/
├── backend/
│   ├── edgepilot/            # simulation library (the science)
│   │   ├── config.py         # reproducible scenario configs + 10 presets
│   │   ├── entities.py       # tasks & processing locations
│   │   ├── environment.py    # topology, OU load/congestion dynamics, oracle
│   │   ├── telemetry.py      # belief state, Age-of-Information, budget ledger
│   │   ├── prediction.py     # belief-aware predictor (+ optional sklearn model)
│   │   ├── schedulers/       # 7 baselines + ABVI-Edge (abvi.py)
│   │   ├── metrics.py        # 20+ metric definitions
│   │   ├── simulator.py      # discrete-event engine
│   │   ├── experiments.py    # multi-seed experiment builders (A–L)
│   │   └── analysis.py       # stats (mean/CI/significance) + figures
│   ├── app/main.py           # FastAPI backend
│   ├── run_experiments.py    # full experimental suite → CSVs + figures
│   └── tests/                # 50 pytest tests
├── frontend/                 # React + TypeScript + Recharts dashboard
├── research/                 # literature review, gap, formulation, report
└── results/                  # raw CSVs, aggregates, figures, reports
```

---

## Quick start

### 1. Backend + experiments (Python 3.11+)

```bash
cd backend
pip install -r requirements.txt

# Run the full experimental suite (20 seeds, parallel). Writes to ../results/.
python run_experiments.py --seeds 20
#   fast smoke:   python run_experiments.py --quick
#   subset:       python run_experiments.py --seeds 12 --exp A B L

# Validation tests (reproducibility, constraints, edge cases, algorithm)
pytest -q
```

### 2. API server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
# docs at http://127.0.0.1:8000/docs
```

### 3. Dashboard

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → :8000)
```

The dashboard has three pages — **Algorithm comparison**, **Single run +
topology** (with live telemetry-budget / edge-utilization time series), and
**Experiments** (budget / workload sweeps and the quality-vs-overhead frontier).
Every chart renders live simulation output; nothing is hardcoded.

---

## Key results (see `results/reports/RESULTS_SUMMARY.md`)

Under the medium scenario (30 devices, 5 edges, β = 0.3), **ABVI-Edge
significantly outperforms all baselines** on completion time, 95th-percentile
latency, deadline violations and scheduling regret (paired tests, 20 seeds).
The budget sweep (Experiment B) shows ABVI-Edge **dominates the
quality-vs-monitoring-overhead frontier**: at equal monitoring spend it delivers
lower completion time and fewer deadline misses than periodic or
freshness-threshold telemetry, and it reaches operating points those baselines
never achieve. The ablation (Experiment L) confirms every component — value of
information, uncertainty estimation, adaptive acquisition — contributes.

---

## Documentation

* [research/PROBLEM_FORMULATION.md](research/PROBLEM_FORMULATION.md) — system model, objective, budget constraint
* [research/ALGORITHM.md](research/ALGORITHM.md) — ABVI-Edge: VoI, shadow price, pseudocode, complexity
* [research/EXPERIMENTAL_METHODOLOGY.md](research/EXPERIMENTAL_METHODOLOGY.md) — metrics, baselines, statistics
* [research/LITERATURE_REVIEW.md](research/LITERATURE_REVIEW.md) + [research/RESEARCH_GAP.md](research/RESEARCH_GAP.md) — survey & novelty assessment
* [research/FINAL_RESEARCH_REPORT.md](research/FINAL_RESEARCH_REPORT.md) — full report

## Scope & honesty notes

* Energy is an **estimated** quantity from analytic power models, never a
  hardware measurement.
* Background server load is **exogenous** (open-loop); see *Threats to validity*
  in the final report.
* "ABVI-Edge" is a working name, **not** a novelty claim; the novelty assessment
  is grounded in the literature survey and is deliberately narrow and candid.

## Repository

Source is hosted at <https://github.com/QuirkyIdea/EdgePilot->. Dependency,
build and cache directories (`node_modules/`, `__pycache__/`, `.pytest_cache/`,
`frontend/dist/`) are intentionally excluded via `.gitignore`; run the setup
steps above to regenerate them.
