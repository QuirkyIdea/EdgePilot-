# ABVI-Edge — Algorithm Specification

_Adaptive Budgeted Value-of-Information Edge Scheduler._

> **Naming disclaimer.** "ABVI-Edge" is a working name for the proposed policy.
> It is **not** a novelty claim. The novelty assessment is in
> [RESEARCH_GAP.md](RESEARCH_GAP.md), grounded in the literature survey.

Implementation: [`backend/edgepilot/schedulers/abvi.py`](../backend/edgepilot/schedulers/abvi.py).
Notation follows [PROBLEM_FORMULATION.md](PROBLEM_FORMULATION.md).

---

## 1. Intuition

On each task arrival the scheduler must decide **where** to run the task and,
first, **whether it is worth spending scarce telemetry budget** to reduce its
uncertainty about the candidate locations before committing. The core idea: a
probe is worth buying only when its *expected reduction in decision cost*
(its **value of information**) exceeds the *adaptive price* of consuming a unit
of a finite, shared budget — amplified by the task's urgency.

This is deliberately **not** a fixed AoI-threshold rule ("refresh if staleness
> X"). Such a rule ignores whether the refresh would actually change the
decision, how uncertain the state is, how urgent the task is, and how scarce the
budget is. ABVI-Edge reasons about all four.

---

## 2. Decision cost under belief

For candidate $\ell$ with belief-predictive completion-time mean $m_\ell$ and
deadline-hit probability $p_\ell$ (both from the Monte-Carlo belief predictor,
`prediction.py`), the decision cost is

$$
C(\ell) = m_\ell + w_d\,\phi(\rho)\,(1-p_\ell)\,D + w_e\,E_\ell,
$$

and the myopic best under the current belief is $C^\star=\min_\ell C(\ell)$.

---

## 3. Value of Information (VoI)

Probing location $\ell$ reveals its true utilization $u_\ell$ (and link
congestion $g_\ell$), collapsing its predictive variance to $\approx 0$. Its
post-observation completion time becomes the closed-form deterministic value
$T_{\ell}(u,g)$. The **value of information** of probing $\ell$ is the expected
reduction in realised decision cost:

$$
\mathrm{VoI}(\ell) \;=\; C^\star \;-\;
\mathbb{E}_{\substack{u\sim \mathcal{N}(\hat u_\ell,\,\varsigma_\ell^2)\\ g\sim\mathcal{N}(\hat g_\ell,\,\gamma_\ell^2)}}
\Bigl[\; \min\bigl(\,C_\ell(u,g),\;\min_{k\ne\ell} C(k)\,\bigr)\Bigr].
$$

* $\varsigma_\ell,\gamma_\ell$ are the **age-dependent** predictive std's from
  the OU belief (PROBLEM_FORMULATION §2).
* The inner $\min$ captures that information only helps when the true value
  could **flip the decision** relative to the best *other* candidate.
* $\mathrm{VoI}(\ell)\ge 0$ always (information cannot raise expected decision
  cost in this myopic model); it is estimated with $R$ Monte-Carlo samples
  (`voi_samples`, default 20) drawn from the belief — **never** from ground
  truth.

$\mathrm{VoI}$ is large exactly when $\ell$ is (i) **uncertain** (old, high
variance) **and** (ii) a **plausible winner** whose realised value could change
the placement. A location that is stale but irrelevant, or relevant but already
fresh, has near-zero VoI and is not probed.

---

## 4. Adaptive budget shadow price

Each probe draws on a finite budget shared across all future decisions. We price
a probe with an **adaptive shadow price** $\lambda(t)$ that rises when the budget
is being spent faster than an even-pacing schedule and falls when we are ahead,
thereby **reserving budget for future, potentially more valuable decisions**:

$$
\lambda(t) = \lambda_0 \cdot \frac{\text{time\_frac\_left}(t) + \epsilon}
                                   {\text{budget\_frac\_left}(t) + \epsilon},
\qquad
\text{time\_frac\_left}=\max\!\Bigl(1-\tfrac{t}{\Omega},0\Bigr),\;
\text{budget\_frac\_left}=\tfrac{\text{remaining}}{\beta C_{\text{full}}}.
$$

If budget is being consumed faster than time elapses
($\text{budget\_frac\_left}<\text{time\_frac\_left}$), $\lambda$ grows and probes
become "expensive"; if we are under-spending, $\lambda$ shrinks and probing is
encouraged.

---

## 5. Urgency

Tight deadlines and high priority increase willingness to pay for information:

$$
\text{urgency}(k,t) = \phi(\rho_k)\,\Bigl(1 + \eta\cdot\min\bigl(\tfrac{m^\star}{\delta_k - t},\,2\bigr)\Bigr),
$$

where $m^\star$ is the current best expected completion time and $\eta$ is the
`urgency_gain`. An urgent task tolerates a higher price for a given VoI.

---

## 6. Policy — greedy sequential VoI acquisition

```
decide(task k at time t):
    slack ← δ_k − t
    costs ← belief_cost(k, t)                      # C(ℓ) for all candidates
    if adaptive acquisition enabled:
        λ ← shadow_price(t)
        repeat up to max_probes times:
            if budget cannot afford 1 probe: break
            C*  ← min_ℓ costs[ℓ];  m*  ← argmin's mean time
            urg ← urgency(k, t, m*)
            # rank affordable probes by NET value
            ℓ̂, best_net ← argmax_{ℓ ∈ E∪{c}, ℓ∉probed}  ( urg · VoI(ℓ) − λ )
            if ℓ̂ is None or best_net ≤ 0: break      # no probe is worth it
            observe(ℓ̂)                                # spend 1 probe, reveal state
            probed ← probed ∪ {ℓ̂}
            costs ← belief_cost(k, t)                 # beliefs changed → re-evaluate
    x_k ← argmin_ℓ costs[ℓ]                           # place at best under updated belief
    return (x_k, probed)
```

The loop is **greedy and sequential**: after each probe the baseline $C^\star$
and the remaining VoIs are recomputed, because resolving one location changes
the value of resolving another. It stops as soon as no remaining probe has
positive net value, the per-decision cap is reached, or the budget is exhausted.

---

## 7. Complexity

With $K=|\mathcal{L}|$ candidates, $R$ VoI samples and at most $P=$`max_probes`
probes per decision:

* **Time:** each VoI estimate is $O(R)$ closed-form evaluations; ranking all
  candidates is $O(K R)$; the greedy loop repeats $\le P$ times with a belief
  re-evaluation ($O(K R_{\text{pred}})$) each → **$O(P\,K\,R)$** per decision.
  All terms are small (tens), no inner simulation; measured decision time is
  ~1–2 ms (see results).
* **Space:** $O(K)$ beliefs + $O(R)$ sample buffers = **$O(K)$**.

---

## 8. Parameters

| Param | Symbol | Default | Role |
|---|---|---|---|
| `lambda0` | $\lambda_0$ | 0.015 | base shadow price (s of value demanded/probe) |
| `w_deadline` | $w_d$ | 1.0 | weight on deadline-miss risk |
| `deadline_penalty` | $D$ | 1.5 | s-equivalent penalty for a miss |
| `w_energy` | $w_e$ | 5e-4 | secondary energy weight (s/J) |
| `voi_samples` | $R$ | 20 | Monte-Carlo samples for VoI |
| `max_probes` | $P$ | 4 | per-decision probe cap |
| `urgency_gain` | $\eta$ | 1.5 | urgency sensitivity |

---

## 9. Why a model, not reinforcement learning?

The policy is a **white-box, belief-driven controller**, not an RL agent. This
is deliberate:

* The VoI computation needs a **calibrated predictive variance**; the OU belief
  provides it in closed form. A point-prediction ML regressor does not (we show
  this empirically: the learned predictor in `prediction.py` is accurate on the
  *mean* but carries no usable uncertainty, so it cannot drive VoI).
* The policy is **interpretable and reproducible** — every probe is justified by
  a number (urgency·VoI vs price) that can be logged and audited.
* It requires **no training data or reward shaping**, so it generalises across
  scenarios without re-training and avoids the reproducibility pitfalls of RL.

An RL extension is noted as future work, but is not necessary for the central
hypothesis and would obscure the mechanism under study.

---

## 10. Ablation handles

Each component can be switched off (used in Experiment L):

| Flag off | Effect |
|---|---|
| `enable_voi` | replace VoI with an uncertainty-threshold probe heuristic |
| `enable_budget` | fix $\lambda=\lambda_0$ (no adaptive pacing) |
| `enable_urgency` | urgency $\equiv 1$ |
| `enable_uncertainty` | collapse belief variance → VoI $\equiv 0$ (never probes) |
| `enable_adaptive` | never probe (pure stale-estimate placement) |

The ablation quantifies each component's contribution to the end result.

### Failure / edge cases handled
* Zero budget → never probes, degrades gracefully to estimate-based placement.
* Failed edge → infeasible ($T=\infty$), automatically excluded; run-time
  fallback to cloud if a chosen location becomes infeasible.
* Impossible deadline → counted as a violation, no crash.
* No edges → only local/cloud candidates considered.
