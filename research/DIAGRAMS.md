# EdgePilot — Diagrams

Mermaid diagrams (render on GitHub/VS Code Markdown preview).

## 1. System architecture

```mermaid
flowchart TB
  subgraph FE["Frontend — React + TypeScript + Recharts"]
    UI1[Algorithm comparison]
    UI2[Single run + topology]
    UI3[Experiments / sweeps]
  end
  subgraph API["Backend — FastAPI"]
    EP1["/api/simulate"]
    EP2["/api/compare"]
    EP3["/api/experiment"]
    EP4["/api/topology"]
  end
  subgraph CORE["edgepilot simulation library"]
    ENV[Environment<br/>OU load & congestion, oracle]
    TM[TelemetryManager<br/>beliefs, AoI, budget]
    PRED[Belief predictor<br/>Monte-Carlo + sklearn]
    SCH[Schedulers<br/>7 baselines + ABVI-Edge]
    SIM[Discrete-event Simulator]
    MET[Metrics]
    EXP[Experiment runner<br/>multiseed, parallel]
    AN[Analysis<br/>stats + figures]
  end
  FE <--> API
  API --> SIM
  SIM --> ENV & TM & SCH & MET
  SCH --> PRED
  SCH --> TM
  EXP --> SIM --> MET
  EXP --> AN
  AN --> OUT["results/ (CSV, figures, reports)"]
```

## 2. ABVI-Edge decision flowchart

```mermaid
flowchart TD
  A[Task k arrives at time t] --> B[Compute belief decision cost C-of-l for all candidates]
  B --> C{Adaptive acquisition enabled?}
  C -- no --> P[Place at argmin C-of-l]
  C -- yes --> D[lambda = shadow_price t]
  D --> E{Budget affords a probe?}
  E -- no --> P
  E -- yes --> F[For each unprobed edge/cloud:<br/>VoI l via belief sampling]
  F --> G[Pick l* = argmax urgency*VoI - lambda]
  G --> H{net value > 0?}
  H -- no --> P
  H -- yes --> I[Observe l*: spend 1 probe,<br/>reveal true state, reset AoI]
  I --> J[Recompute C-of-l]
  J --> E
  P --> K[Execute task under true state;<br/>record metrics and regret]
```

## 3. Simulation workflow (per run)

```mermaid
sequenceDiagram
  participant Env as Environment
  participant Sch as Scheduler
  participant TM as TelemetryManager
  participant Met as Metrics
  loop for each task (event-driven)
    Env->>Env: advance_to(arrival) — evolve OU state
    Env->>Env: oracle_completion (true state) for regret
    Sch->>TM: query beliefs / (maybe) observe()  [spends budget]
    Sch-->>Env: placement decision x_k
    Env->>Env: realized completion under true state
    Env->>Met: record completion, violation, regret, energy, telemetry
  end
  Met-->>Met: summarize (post-warmup)
```

## 4. Experimental methodology

```mermaid
flowchart LR
  S[Seeds 1..20] --> J[Build Jobs<br/>scheduler x scenario x seed]
  J --> PP[ProcessPool: run_once per job]
  PP --> RAW[raw/expX.csv<br/>per-seed metrics]
  RAW --> AGG[aggregate: mean, std, 95% CI]
  RAW --> SIG[paired Wilcoxon / t-test<br/>ABVI vs each baseline]
  AGG --> FIG[publication figures]
  SIG --> REP[RESULTS_SUMMARY.md]
  AGG --> REP
```
