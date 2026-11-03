# Research Gap and Novelty Assessment

_For EdgePilot / ABVI-Edge. Grounded in [LITERATURE_REVIEW.md](LITERATURE_REVIEW.md)
and [PAPER_COMPARISON.csv](PAPER_COMPARISON.csv). Novelty is stated **narrowly and
candidly**; this is a defensible research opportunity, not a proven first._

## 1. Existing research landscape

Five mature but **largely disjoint** bodies of work surround this problem:

1. **Offloading / placement** (DRL-E2D 2021; Firm-Deadline MDP 2022; Wang TMC
   2020; surveys JNCA 2023, ACM CSUR 2023) — optimise latency/energy/deadlines,
   assuming the needed state is available.
2. **Partial-observation offloading** (Badnava 2023; POMDP migration 2022;
   imperfect-CSI 2024) — act under incomplete state, but do not *acquire* more.
3. **Age of Information** (Heterogeneous-channel AoI 2021; Uplink-partial-obs
   AoI 2022) — keep a monitor fresh via transmission scheduling.
4. **Value of Information / observation scheduling** (Spatio-temporal VoI 2018;
   VoI updating 2021; VoI foundations 2024) — buy observations under a budget to
   improve an *estimation/control* decision.
5. **Adaptive network telemetry** (PINT 2020; event-INT 2019; LINT 2021;
   FineMon 2024; INT-MC 2024; AdapINT 2024) — reduce monitoring overhead on the
   monitoring plane alone.

## 2. What has already been solved

* Offloading under deadlines/energy with full or learned state — **well solved**.
* Acting under partial/imperfect observations — **solved** (bandits, POMDPs).
* Keeping a monitor fresh (AoI) and valuing an observation (VoI) under a
  measurement budget — **solved in monitoring/control contexts**.
* Reducing telemetry overhead adaptively — **solved on the network plane**.

## 3. What remains insufficiently investigated

No surveyed work **closes the loop** between the monitoring plane and the
offloading decision. Specifically, we did not find a method that:

* treats **telemetry acquisition as a per-decision action** priced against an
  explicit **monitoring budget**, *and*
* chooses what to observe by the **value of information for the task-placement
  decision** (not for generic estimation/control), *and*
* does so **jointly** with the placement itself in a dynamic edge environment
  with deadlines.

The closest point, Badnava et al. (2023), is partial-observation deadline-aware
edge offloading — but it **never pays to refresh state** and uses **no AoI/VoI
and no monitoring budget** (verified from its abstract). VoI-under-budget exists
(Theme 4) but targets estimation/control, not offloading. Adaptive telemetry
exists (Theme 5) but is decoupled from any placement decision.

## 4. The exact research gap

> **Gap.** A *budget-constrained, value-of-information-driven* policy that
> **jointly** decides (a) which candidate servers/links to probe with scarce
> telemetry and (b) where to place each task, in a dynamic, deadline-driven
> edge–cloud environment, appears to be an **under-explored combination**. The
> individual ingredients are established; their joint, decision-coupled,
> budgeted integration for compute offloading is not evidenced in the surveyed
> literature.

## 5. Why the gap matters

Monitoring is not free at scale, yet stale state causes costly misplacements.
Operators need a principled knob between "monitor everything" (overhead) and
"monitor nothing" (regret). Coupling VoI to the *offloading* decision targets
monitoring exactly where it changes outcomes, which neither plane-isolated
telemetry nor free-state offloading can do.

## 6. Proposed technical contribution

**ABVI-Edge** (see [ALGORITHM.md](ALGORITHM.md)): a white-box scheduler that, per
task, (i) maintains an age-dependent belief over candidate utilizations/congestion,
(ii) estimates the **VoI** of a telemetry probe as the expected reduction in
placement decision cost, (iii) prices probes with an **adaptive budget shadow
price** that paces spending and reserves budget for future decisions, scaled by
**task urgency**, and (iv) places the task under the updated belief. The budget
provably shapes decisions (ablation `no_budget` changes behaviour), and the
policy self-limits telemetry when beliefs are already good (Experiment B).

## 7. Mathematical formulation

See [PROBLEM_FORMULATION.md](PROBLEM_FORMULATION.md) (system model, OU belief,
budget constraint, decision cost, regret) and [ALGORITHM.md](ALGORITHM.md) (VoI
expectation, shadow price, greedy acquisition, complexity $O(PKR)$/decision).

## 8. Expected advantages

* Lower completion time / deadline violations at **equal monitoring overhead**
  than periodic or freshness-threshold telemetry.
* Lower **scheduling regret** than stale-estimate placement.
* **Interpretability** (every probe justified by urgency·VoI vs price) and
  **reproducibility** (no training).

## 9. Limitations of the contribution

* VoI is **myopic** (per task, single-step), not POMDP-optimal.
* Benefits are **regime-dependent** — negligible at extreme budget scarcity
  (shown in Exp B) and in low-volatility conditions.
* Evidence is **simulation-based**; the novelty claim is bounded by a
  time-limited survey, so it is framed as an under-explored combination.

## 10. Research questions

* **RQ1.** Can VoI-driven, budget-aware telemetry acquisition reduce offloading
  completion time / deadline violations versus periodic and freshness-threshold
  telemetry at equal monitoring overhead?
* **RQ2.** Does coupling acquisition to placement reduce scheduling regret versus
  placement on stale beliefs?
* **RQ3.** How do the gains depend on telemetry budget, workload volatility and
  deadline tightness?
* **RQ4.** Which algorithmic components (VoI, uncertainty, adaptivity, urgency,
  budget pacing) are necessary for the observed gains?

## 11. Testable hypotheses

* **H1.** Adaptive telemetry reduces monitoring overhead at equal task
  performance versus periodic collection. _(Tested in Exp B — supported: ABVI
  matches/beats periodic quality at lower or equal overhead across β.)_
* **H2.** Joint acquisition+placement reduces regret versus stale-information
  placement. _(Tested in Exp A/B — supported: regret 0.007 s vs 0.112 s.)_
* **H3.** The benefit grows with workload volatility, urgency and available
  budget. _(Tested in Exp B/C/F/J — supported: largest margin under congestion.)_

## 12. Novelty assessment (candid)

**Claim.** The *combination* — VoI-driven, budget-constrained telemetry
acquisition **coupled to** deadline-aware edge task placement — is an
under-explored research opportunity. **Not claimed:** that VoI, AoI, budgeted
sensing, adaptive telemetry or partial-observation offloading are individually
new (they are not; see Themes 2–5). If a reader knows a paper combining all three
pillars (offloading + telemetry budget + VoI acquisition), the contribution
should be **narrowed** to our specific shadow-price pacing + urgency-weighted
myopic-VoI formulation and its empirical frontier characterisation — which remain
a concrete, reproducible contribution regardless.
