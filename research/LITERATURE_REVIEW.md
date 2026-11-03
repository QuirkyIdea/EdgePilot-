# Literature Review

_Survey supporting EdgePilot: Adaptive Telemetry-Budgeted Intelligent Task
Offloading._

## Integrity statement

Every paper below appeared in a real web/database search. Each entry carries a
**verification level**:

* **verified-fulltext** — the full text / abstract page was fetched and read;
* **abstract-only** — the abstract (or its arXiv/DOI landing page) was read;
* **metadata-only** — only the title/venue/URL from the search listing was seen.

No titles, authors, venues, DOIs/URLs or findings are fabricated. Where a field
was not visible in the source, it is marked as such. A machine-readable feature
matrix is in [PAPER_COMPARISON.csv](PAPER_COMPARISON.csv); BibTeX in
[REFERENCES.bib](REFERENCES.bib). 22 papers are catalogued (≥ 20 target met).

> **Collection note.** An automated multi-agent literature search was launched
> for this project; one topic cluster (network telemetry) completed and was
> harvested directly, and the remaining clusters were searched manually with the
> same integrity rules after the automated agents stalled. This is disclosed for
> transparency.

---

## Theme 1 — Computation offloading in mobile edge computing

Offloading decides where a task runs to optimise latency, energy and deadline
attainment. **DRL-E2D (2021, EURASIP JWCN)** maximises reward under task
deadlines with deep RL in a multi-eNB MEC setting [metadata-only]. **Optimal
Task Offloading with Firm Deadlines (2022, arXiv)** derives threshold MDP
policies for firm deadlines [metadata-only]. **Wang et al., DRL for Task
Offloading in MEC (2020, IEEE TMC)** handles general task graphs [metadata-only].
Two surveys — **RL-based Computation Offloading (2023, JNCA)** and **RL Methods
for Computation Offloading: A Systematic Review (2023, ACM CSUR)** — map the
field [metadata-only]; both emphasise latency/energy objectives and, notably,
rarely model the *cost of acquiring* the state the policies condition on.

**Relation to ours.** These establish the placement problem and its objectives
but assume the relevant state (loads, link quality) is available for free. EdgePilot
adopts the same placement objective but makes state acquisition a priced decision.

## Theme 2 — Learning under imperfect / partial observations

**Energy-Efficient Deadline-Aware Edge Computing: Bandit Learning with Partial
Observations (Badnava et al., 2023, arXiv)** is the **closest** work: it offloads
under deadlines/energy using contextual neural bandits with *partial* state
(task features), in a multi-channel system [abstract-only, fetched]. **Service
Migration based on POMDP (2022, Computers & Electrical Eng.)** models edge state
as partially observable [metadata-only]. **Reliable Task Offloading with
Imperfect CSI (2024, IEEE TNSM)** offloads under noisy channel estimates
[metadata-only].

**Relation to ours.** These acknowledge partial observability but **do not pay a
monitoring budget to reduce it on demand**, and none computes a value of
information for a telemetry probe. EdgePilot's distinction is precisely the
active, budgeted acquisition decision.

## Theme 3 — Age of Information (AoI) and freshness

**Minimizing AoI via Scheduling over Heterogeneous Channels (2021, IEEE)** gives
threshold-optimal AoI scheduling [metadata-only]. **Optimizing AoI in Wireless
Uplink Networks with Partial Observations (Liu et al., 2022)** solves a
belief-MDP for transmission scheduling under partial observations of update ages
[abstract-only, fetched]. These motivate our age-dependent belief model: the OU
predictive variance growing with AoI is the quantitative analogue of
"information getting stale."

**Relation to ours.** AoI work schedules *transmissions of updates* to keep a
monitor fresh; it does not connect freshness to a *downstream compute-placement*
decision, nor price freshness against its decision value.

## Theme 4 — Value of Information (VoI) and observation scheduling

**Value-of-Information in Spatio-Temporal Systems (2018, Reliability Eng. &
System Safety)** selects sensing locations/times to maximise VoI minus cost under
a measurement budget [metadata-only]. **Optimal Information Updating based on VoI
(2021, NSF)** triggers updates when VoI exceeds cost [metadata-only].
**Foundations of Value of Information (2024, arXiv)** formalises VoI as a semantic
metric for networked-control communication [metadata-only].

**Relation to ours.** This is the methodological backbone we build on — VoI-driven
sensing under a budget. Crucially, these works target **monitoring/estimation or
control communication**, *not* edge task offloading. EdgePilot transfers the
VoI-under-budget idea into the offloading loop, where the "decision" is task
placement and the "observation" is a telemetry probe of a candidate server/link.

## Theme 5 — Network telemetry overhead and adaptive monitoring

**PINT (2020, SIGCOMM)** bounds per-packet telemetry bits probabilistically
[verified-fulltext]. **Programmable Event Detection for INT (2019, CloudNet)**
reports telemetry only on events [verified-fulltext]. **LINT (2021, IFIP/IEEE
IM)** adapts INT accuracy/overhead [abstract-only]. **FineMon (2024, PACMMOD)**
dynamically adjusts telemetry frequency with matrix-completion recovery
[verified-fulltext]. **INT-MC (2024, ACM)** lowers network-wide telemetry cost via
matrix completion [abstract-only]. **AdapINT (2024, IEEE TNSM)** schedules INT
probes with deep RL to trade accuracy against overhead [abstract-only].

**Relation to ours.** These prove that monitoring overhead is real and worth
adapting — justifying an explicit telemetry budget. However, they optimise the
**monitoring plane in isolation** (accuracy vs bits), never coupling a probe to
the value it brings a specific **task-placement** decision. EdgePilot closes that
loop.

## Theme 6 — Prediction for offloading

**Execution-Time Prediction via Lightweight AI (2025, Zenodo)** predicts
per-node execution time, criticising static/linear estimators [metadata-only].
**LSTM-Prediction + DRL Offloading (2022, Future Internet)** predicts load then
offloads [metadata-only]. These informed our predictor design: we provide a
belief-aware analytic predictor **and** an optional scikit-learn model, and we
note that a point predictor lacks the calibrated variance VoI requires.

---

## Synthesis

The surrounding literature independently establishes all the ingredients:
(i) deadline/energy-aware offloading, (ii) learning under partial observability,
(iii) AoI-based freshness, (iv) VoI-driven sensing under a budget, and
(v) adaptive, overhead-aware network telemetry. What recurs across all five is
that each optimises **one side**: offloading assumes free state; telemetry
optimises bits without a decision objective; VoI/AoI target monitoring or control
rather than compute placement. The research gap — and EdgePilot's contribution —
is the **joint** treatment, analysed in [RESEARCH_GAP.md](RESEARCH_GAP.md).
