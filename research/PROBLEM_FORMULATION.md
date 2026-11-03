# EdgePilot — Formal Problem Formulation

_Adaptive Telemetry-Budgeted Intelligent Task Offloading for Dynamic Edge
Computing Environments._

This document defines the system model, decision variables, objective and
constraints that the simulator in `backend/edgepilot/` implements. Symbols are
used consistently in [ALGORITHM.md](ALGORITHM.md) and the final report.

---

## 1. System model

### 1.1 Entities

* **End devices** $\mathcal{D} = \{d_1,\dots,d_N\}$, $N \in [20,50]$. Each device
  generates tasks and can execute them locally on a weak CPU.
* **Edge servers** $\mathcal{E} = \{e_1,\dots,e_M\}$, $M \in [3,10]$,
  heterogeneous in processing capacity.
* **Cloud** $c$: a single remote server, fast but reached over a
  high-latency / limited-bandwidth WAN.

The set of **candidate processing locations** for a task originating at device
$i$ is $\mathcal{L}_i = \{\text{local}_i\} \cup \mathcal{E} \cup \{c\}$.

### 1.2 Tasks

Tasks arrive as a Poisson process of rate $\lambda$ (tasks/s). Task $k$ is a tuple

$$
\tau_k = (i_k,\; a_k,\; w_k,\; s^{\text{in}}_k,\; s^{\text{out}}_k,\; \delta_k,\; \rho_k)
$$

| Symbol | Meaning | Unit |
|---|---|---|
| $i_k$ | originating device | — |
| $a_k$ | arrival time | s |
| $w_k$ | compute demand | Mcyc |
| $s^{\text{in}}_k, s^{\text{out}}_k$ | input / output size | Mb |
| $\delta_k$ | absolute deadline | s |
| $\rho_k \in \{1,2\}$ | priority (2 = high) | — |

Demands and sizes are drawn from log-normal distributions; the deadline is set
relative to a scheduler-independent reference completion time (nominal-edge or
cloud, whichever is faster) scaled by a random slack factor.

### 1.3 Processing locations — dynamic state

Each location $\ell$ has a fixed capacity $\mu_\ell$ (Mcyc/s) and a
time-varying **utilization** $u_\ell(t)\in[0,1)$ driven by exogenous background
load. We model $u_\ell(t)$ as a mean-reverting Ornstein–Uhlenbeck (OU) process:

$$
du_\ell = \theta\,(\bar u_\ell - u_\ell)\,dt + \sigma\sqrt{2\theta}\,dW_t,
$$

with mean-reversion rate $\theta$, stationary mean $\bar u_\ell$ and stationary
std $\sigma$. The **compute time** of task $k$ on location $\ell$ uses an
M/M/1-style sojourn inflation:

$$
T^{\text{cmp}}_{k,\ell} = \frac{w_k}{\mu_\ell}\cdot\frac{1}{1-\min(u_\ell,0.95)} .
$$

### 1.4 Network links

Each device–edge and device–cloud link has base bandwidth $B_\ell$ (Mb/s),
base one-way latency $L_\ell$ (s) and a time-varying multiplicative
**congestion** $g_\ell(t)\ge 0.3$ following a log-space OU process. One-way
transfer time of a payload of size $s$:

$$
T^{\text{net}}_\ell(s) = \frac{s}{B_\ell / g_\ell} + L_\ell\, g_\ell .
$$

The **completion time** of task $k$ placed at $\ell$ (relative to its arrival):

$$
T_{k,\ell} =
\begin{cases}
T^{\text{cmp}}_{k,\ell}, & \ell = \text{local}_i \\[4pt]
T^{\text{net}}_\ell(s^{\text{in}}_k) + T^{\text{net}}_\ell(s^{\text{out}}_k) + T^{\text{cmp}}_{k,\ell}, & \text{otherwise.}
\end{cases}
$$

### 1.5 Energy (estimated)

Energy is an **estimated** quantity (never a hardware measurement):

* Local: $E = P^{\text{cmp}}_{\text{dev}}\cdot T^{\text{cmp}}$.
* Offloaded: $E = P^{\text{tx}}_{\text{dev}}\cdot T^{\text{net}} + P^{\text{idle}}_{\text{dev}}\cdot T^{\text{cmp}} + \kappa_\ell\, w_k$,
  where $\kappa_\ell$ is server energy per cycle.

---

## 2. Partial observability

The scheduler does **not** observe $u_\ell(t)$ or $g_\ell(t)$ directly. It keeps
a **belief** per state: a last-observed value $\hat x$ at time $t_{\text{obs}}$.
The **Age of Information** is $\alpha_\ell(t) = t - t_{\text{obs}}$. Under the OU
model the predictive distribution of the current value given an observation of
age $\alpha$ is Gaussian with

$$
\text{mean} = \bar x + (\hat x - \bar x)\,e^{-\theta\alpha},\qquad
\text{var}  = \sigma^2\bigl(1 - e^{-2\theta\alpha}\bigr).
$$

Thus belief **uncertainty grows with age** toward the stationary variance. This
closed form is the basis of the value-of-information computation.

---

## 3. Decision variables

For each task $k$ the policy chooses:

1. **Telemetry set** $S_k \subseteq \mathcal{E}\cup\{c\}$ — which locations to
   probe (refresh belief) before deciding. Probing $\ell$ sets
   $\alpha_\ell \leftarrow 0$ and costs one probe.
2. **Placement** $x_k \in \mathcal{L}_{i_k}$ — where the task executes.

---

## 4. Monitoring budget

Let a probe transfer $b$ Mb of monitoring traffic. Over a budget window $\Omega$
the total monitoring traffic must satisfy

$$
\sum_{k: a_k \in \Omega} |S_k|\, b \;\le\; \beta\, C_{\text{full}},\qquad
C_{\text{full}} = (M+1)\,\lambda\,|\Omega|\,b ,
$$

where $\beta\in[0,\infty)$ is the **normalized telemetry budget** and
$C_{\text{full}}$ is the cost of probing every probeable location on every
decision. $\beta = 1$ means "could observe everything, every time";
$\beta = 0.3$ means a 70 % reduction versus that reference. The budget is a hard
constraint enforced by the telemetry manager and, crucially, **shapes the
policy** via an adaptive shadow price (see ALGORITHM.md §4).

---

## 5. Objective

Define a per-task scalar **decision cost** combining latency, deadline risk and
(secondarily) energy, scaled by priority:

$$
C_k(\ell) = \mathbb{E}[T_{k,\ell}]
          + w_d\,\phi(\rho_k)\,\bigl(1 - \Pr[T_{k,\ell}\le \delta_k - t]\bigr)\,D
          + w_e\,\mathbb{E}[E_{k,\ell}],
$$

with deadline-miss penalty $D$ (s-equivalent), priority factor $\phi$, and small
energy weight $w_e$. The expectations are taken over the belief.

The **system objective** over a run minimises the time-average decision cost
subject to the budget constraint of §4:

$$
\min_{\{S_k,\,x_k\}} \; \frac{1}{K}\sum_{k=1}^{K} C_k(x_k)
\quad\text{s.t.}\quad \text{(budget constraint §4)} .
$$

### 5.1 Scheduling regret

To isolate the cost of acting on stale information we define per-task
**scheduling regret** against an omniscient oracle that sees the true state:

$$
R_k = T_{k,x_k} - \min_{\ell \in \mathcal{L}_{i_k}} T_{k,\ell}^{\text{(true)}}\;\ge\;0 .
$$

Regret $=0$ iff the chosen placement is the realised best; it grows when belief
staleness causes a suboptimal placement. This is the central quantity the
telemetry decisions aim to reduce per unit of budget.

---

## 6. Why this is a joint problem

Placement quality depends on belief accuracy; belief accuracy costs budget;
budget is finite and shared across all future decisions. Choosing $S_k$ well
requires estimating how much a refresh would change $x_k$ **and** reserving
budget for future, possibly more urgent, tasks. Optimising placement and
telemetry **separately** is therefore sub-optimal — motivating the joint,
budget-aware value-of-information policy of the next document.

---

## 7. Modelling assumptions (stated for validity)

1. Background load is **exogenous** (cross-traffic), not induced by the
   scheduler's own placements — a common open-loop assumption; it isolates the
   effect of volatility/observation from queue feedback.
2. Realised completion uses the true state **sampled at task arrival**
   (snapshot at arrival granularity); this makes the oracle and regret
   well-defined.
3. Energy is estimated from analytic power models, not measured.
4. A location probe bundles a co-located link (RTT) observation at no extra
   budget cost (the same monitoring message carries both).

These assumptions are revisited under *Threats to validity* in the final report.
