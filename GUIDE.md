# EdgePilot — A Simple Guide to the Project

*Read this before the setup instructions in the [README](README.md). It explains the whole project from zero — no prior knowledge of edge computing, telemetry or scheduling assumed. By the end you should be able to explain EdgePilot to your professor in your own words.*

By the end of this guide you will understand:

- What problem we are solving.
- Why the problem matters.
- What exactly we built.
- What makes our approach different.
- How our algorithm works.
- How we test whether it is actually better.
- What the results mean.
- What your professor might ask.

---

## 1. The basic idea

Imagine a small device — a phone, a smart camera, a robot, an AR headset — that produces a task it needs to compute. For example a traffic camera that must detect vehicles, or an AR app that must process a camera frame in real time.

These tasks need computing power, and a small device often cannot do everything itself fast enough. So the real question is: **where should the task run?**

There are three choices.

**1. Local (on the device itself)**
- 👍 No data is sent anywhere, so no network delay.
- 👎 The device is weak, so heavy tasks take a long time.

**2. Edge (a nearby small server)**
- 👍 Much more powerful than the device, and close by, so low network delay.
- 👎 The nearby server may already be busy, or the network to it may be congested.

**3. Cloud (a big, far-away data centre)**
- 👍 Huge computing power.
- 👎 It is far away, so sending data there and back adds latency.

Choosing the best of these three for each task is called **task offloading**.

---

## 2. Why the decision is hard

Here is a small example. Suppose one task could run in:

| Where it runs | Time to finish |
|---|---|
| On the device (local) | 1.20 s |
| On a nearby edge server | 0.35 s |
| On the cloud | 0.55 s |

Right now the **edge server is best**. Easy.

But these numbers are **not fixed**. Suppose 40 other devices suddenly start using that edge server. Its time might jump from 0.35 s to 1.5 s — and now local is actually faster. Or the network gets congested and the cloud becomes the better choice.

So we **cannot** decide once and for all that "edge is best." The right answer changes from second to second, depending on current conditions. A good scheduler has to react to those changing conditions.

---

## 3. Telemetry — how the scheduler "sees" the network

To pick the right location, the scheduler needs to know the **current** state of the servers and network:

- How busy each server's CPU is (utilization).
- How long its queue is.
- How much bandwidth each network link has.
- How much latency / packet loss there is.

The act of **collecting this information is called telemetry.** Think of it as the monitoring system of the network — it tells the scheduler what is happening right now.

**Why we need it:** without telemetry, the scheduler is deciding blind. It might send a task to a server that looked free five seconds ago but is now overloaded.

**But telemetry is not free.** Imagine 1,000 devices all constantly asking 100 servers "how busy are you? how much bandwidth is left?" — those monitoring messages themselves use up bandwidth, energy and CPU. This cost is called **telemetry overhead** (or monitoring overhead).

---

## 4. The real research problem

This gives us two bad extremes:

**Approach A — Monitor everything, all the time.**
Information is always fresh, decisions are well-informed — but monitoring overhead is high. The monitoring traffic starts competing with the real work.

**Approach B — Monitor rarely.**
Overhead is low — but information gets stale, so the scheduler makes bad placement decisions.

Neither is good. So the central research question of this project is:

> **Can the scheduler intelligently decide *when* collecting fresh information is worth its cost — spending monitoring effort only where it actually improves the decision?**

That is the whole idea behind **EdgePilot**.

---

## 5. What we propose

**EdgePilot — Adaptive Telemetry-Budgeted Intelligent Task Offloading.**

For every task, EdgePilot makes **two decisions together**:

1. **Where** should this task run (local / edge / cloud)?
2. **Should we first spend some of our limited monitoring budget** to refresh our view of the servers before deciding?

### A concrete scenario

A task must finish within 500 ms. The scheduler's last monitoring update (10 seconds old) says:

| Server | Load seen 10 s ago |
|---|---|
| A | 25% |
| B | 60% |
| C | 95% |

Based on this, **Server A looks best**. But the info is 10 seconds old — what if A is now overloaded?

The scheduler can either:
- **Choice 1:** trust the old info and send the task to A immediately, or
- **Choice 2:** pay to ask A (and maybe B) for a fresh status, then decide.

Choice 2 costs monitoring budget. EdgePilot's job is to **work out whether that fresh information is worth the cost**. That is the key innovation.

---

## 6. The proposed algorithm: ABVI-Edge

**ABVI-Edge = Adaptive Budgeted Value-of-Information Edge scheduler.**

Breaking the name down:

- **Adaptive** — it changes its behaviour based on conditions.
- **Budgeted** — it has a limited monitoring budget.
- **Value of Information** — it calculates whether fresh information is worth getting.
- **Edge scheduler** — it decides where each task runs.

It has four parts.

### 6.1 Value of Information (VoI) — the most important idea

Suppose the scheduler currently believes:
- Server A will take 0.8 s
- Server B will take 0.6 s

So it would pick **B**. But those estimates are uncertain (the data is old).

- **Case 1:** if a fresh check would reveal A is actually 0.3 s and B is actually 1.1 s, then the information **changes the decision** (now A wins). The information was **valuable**.
- **Case 2:** if a fresh check would just confirm A ≈ 0.8 s and B ≈ 0.6 s, the decision **stays the same**. The information was **not worth paying for**.

This is the difference between ordinary monitoring and **Value of Information**. VoI asks:

> *How much better could my decision get if I obtained fresh information?*

A simple way to write it:

```
VoI = (expected cost of my decision now)  −  (expected cost of my decision after refreshing)
```

Crucially, EdgePilot does **not** just check "is this data old?" It estimates whether new data could actually **change the placement**. It computes this by **Monte-Carlo sampling** — drawing many possible "true" values of a server's state from what it currently believes, and seeing how often the decision would flip. (It samples from its *belief*, never from the hidden true state.)

So VoI is high only when a server is **both** uncertain (old, unsure) **and** a plausible winner. A server that is stale but irrelevant, or relevant but already fresh, gets ~zero VoI and is not probed.

### 6.2 Telemetry budget

The system is allowed only a limited amount of monitoring in a time window — say, the equivalent of 100 checks. It **cannot monitor everything**, so it must spend those checks carefully, only on servers likely to matter.

We express the budget as a normalized number **β** (beta):
- **β = 1.0** means "you could afford to check everything, every time."
- **β = 0.3** means "you get 30% of that — a 70% reduction."

The budget is a **hard limit**, and (as we'll see) it genuinely changes the algorithm's behaviour — it is not just a number shown on a screen.

### 6.3 Adaptive shadow price

Think of having ₹1,000 to spend across a whole day. If you blow ₹900 by morning, you must be stingy in the evening. If you've barely spent anything, you can relax.

The algorithm does the same with its monitoring budget using a value called **λ(t)** (the "shadow price" — the *price* it charges itself for one probe):

- Spending the budget **too fast** → λ **rises** → probes become "expensive" → it becomes choosy.
- Spending **too slowly** → λ **falls** → probing is encouraged.

This automatically **reserves budget for future tasks** that might need it more. (λ is not real money — it's a mathematical penalty representing how scarce the budget currently is.)

### 6.4 Task urgency

Not all tasks are equally time-critical:

| Task | Deadline |
|---|---|
| A | 100 ms (very tight) |
| B | 5 s (relaxed) |

A wrong placement for Task A likely misses its deadline; Task B has slack. So EdgePilot is **more willing to pay for information** when a task is urgent. This is called **urgency-weighted telemetry acquisition**.

---

## 7. How ABVI-Edge actually decides (step by step)

For each arriving task:

1. Estimate the **cost** of every candidate location (local, each edge, cloud) using the current belief. Note the current best.
2. Compute the current **shadow price λ** (how scarce is my budget right now?).
3. Repeat up to a few times (the probe cap):
   - For each candidate we haven't probed yet, compute its **net value = urgency × VoI − λ**.
   - Pick the candidate with the highest net value.
   - If that value is **positive** and we can **afford** a probe → **probe it** (spend one unit of budget, refresh its state), then re-estimate all costs.
   - If no probe has positive net value → **stop probing**.
4. Place the task at the **cheapest** candidate under the now-updated belief.

In plain words: *"Keep buying fresh information only while it's worth more than its current price — then make the best decision you can."*

It uses **no machine learning and no training** — it is a transparent, "white-box" controller where every probe is justified by a number you can log and check. (We chose this on purpose: the VoI math needs a proper measure of uncertainty, which the simple analytic model gives us directly, and a transparent policy is easier to trust and reproduce.)

---

## 8. How we built and tested it

**No physical hardware is needed.** Everything runs in a **simulator** written in Python — a program that models the whole edge–cloud system:

- 20–50 devices, 3–10 edge servers, and one cloud.
- Server loads and network congestion drift realistically over time (using a standard "mean-reverting" random process, so load wanders up and down rather than jumping randomly).
- Tasks arrive randomly, each with its own size, deadline and priority.
- Everything uses fixed random seeds, so any run can be **exactly reproduced**.

### We compare ABVI-Edge against 7 baselines

| Baseline | What it does |
|---|---|
| Local-only | Always run on the device |
| Cloud-only | Always send to the cloud |
| Random | Pick a location at random |
| Nearest-edge | Always use the closest edge |
| Lowest-est-time | Pick the best guess, but **never** refresh info |
| Periodic-telemetry | Refresh **everything** on a fixed timer |
| Freshness-aware | Refresh a server when its info is "too old" |

The last three are real monitoring strategies — they let us test whether ABVI-Edge's *smart* probing actually beats *blind* probing. **Every algorithm faces the exact same tasks and conditions** (this fairness is enforced by automated tests), so no one gets an easier workload.

### How we measure success

Over 20 random seeds (repeat runs), we record average/median/95th-percentile completion time, deadline-violation rate, **scheduling regret** (see below), estimated energy, telemetry used, and more. We report averages with confidence intervals and use proper **statistical significance tests** (paired Wilcoxon + t-test).

> **Scheduling regret** is a key metric: it compares our chosen placement to the placement a magical "all-seeing oracle" (who knows the true state) would have picked. **Regret = 0** means we made the perfect choice. High regret means stale information caused a bad placement. Regret directly measures *the cost of acting on old information* — exactly what telemetry is meant to reduce.

---

## 9. What the results mean

On the medium scenario (30 devices, 5 edges, β = 0.3, averaged over 20 seeds), **ABVI-Edge is the best on every quality metric**:

| Scheduler | Completion (s) | p95 (s) | Violations | Regret (s) |
|---|---|---|---|---|
| Cloud-only | 0.479 | 0.816 | 0.119 | 0.160 |
| Lowest-est-time | 0.431 | 0.848 | 0.084 | 0.112 |
| Freshness-aware | 0.374 | 0.699 | 0.041 | 0.054 |
| Periodic-telemetry | 0.361 | 0.668 | 0.034 | 0.043 |
| **ABVI-Edge (ours)** | **0.326** | **0.568** | **0.010** | **0.007** |

Versus the strongest baseline (Periodic-telemetry): **9.8% faster**, **72% fewer deadline violations**, **83% less regret** — and all differences are statistically significant.

Three deeper findings:

1. **It dominates the quality-vs-overhead trade-off.** When we sweep the budget β, ABVI-Edge gives better quality than periodic/freshness telemetry *at the same monitoring cost* — and it keeps improving where they plateau.
2. **It self-limits.** Even with an *unlimited* budget (β = 1.0), it uses only ~19% of the "monitor everything" cost — once no probe is worth its price, it simply stops. It does not waste budget just because it's available.
3. **Every component matters (ablation).** If we remove the Value-of-Information part, performance gets **worse** while spending **more** telemetry — the clearest proof that the advantage comes from *smart allocation*, not from just probing more.

---

## 10. Honesty notes (state these up front)

- **Energy is estimated** from analytic power models — it is *not* a hardware measurement.
- **Background load is "open-loop"** — our own placements don't feed back into server queues (a common simplifying assumption).
- **VoI is "myopic"** — it looks one task ahead, not far into the future.
- **"ABVI-Edge" is a working name, not a proven novelty claim.** The individual ingredients (VoI, budgets, adaptive telemetry) already exist; what is under-explored is **combining them and coupling the monitoring decision directly to the offloading decision**. The report states this narrowly and honestly.

---

## 11. Questions your professor might ask (with short answers)

**Q: Isn't this just "refresh if data is old"?**
No. An age threshold ignores whether refreshing would change anything. VoI measures whether fresh data could actually *flip the placement decision*, and only then pays for it.

**Q: Why not reinforcement learning?**
Because VoI needs a *calibrated measure of uncertainty*, which our analytic belief model provides directly. A trained point-predictor gives a number but no reliable uncertainty, so it can't drive VoI. A white-box policy is also interpretable and reproducible. (RL is listed as future work.)

**Q: How do you know the comparison is fair?**
All eight schedulers run on identical tasks, topology and conditions for each seed — enforced by tests. We also show the one regime (very tight budgets) where ABVI-Edge only ties, rather than hiding it.

**Q: Why does ABVI-Edge sometimes use *more* probes than Periodic?**
When the budget is generous, it can afford more. The efficiency claim is "better quality at equal spend," proven by the budget sweep — and the ablation shows that removing smart probing spends *more* for *worse* results.

**Q: Is the result statistically real?**
Yes — 20 seeds, confidence intervals, and paired significance tests; nearly all headline differences have p-values far below 0.05.

**Q: What is "regret" again?**
The gap between our placement and the best possible placement (known only to an all-seeing oracle). It isolates how much stale information is costing us.

---

## 12. How to run it

See the [README](README.md) for exact commands. In short:

```bash
# backend + full experiments
cd backend && pip install -r requirements.txt
python run_experiments.py --seeds 20      # produces the CSVs and figures
pytest -q                                  # 50 validation tests

# API + dashboard
uvicorn app.main:app --reload --port 8000  # backend API
cd ../frontend && npm install && npm run dev   # dashboard at http://localhost:5173
```

The dashboard lets you change the configuration, click **Run comparison**, and watch all eight schedulers compete on live simulation output — nothing is hardcoded.
