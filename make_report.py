# -*- coding: utf-8 -*-
"""Generate the UROP project report for EdgePilot in the sample's format."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(ROOT, "results", "figures")

doc = Document()

# ---- base style: Book Antiqua 12pt, matching the sample ----
normal = doc.styles["Normal"]
normal.font.name = "Book Antiqua"
normal.font.size = Pt(12)
rpr = normal.element.get_or_add_rPr()
rfonts = rpr.get_or_add_rFonts()
rfonts.set(qn("w:ascii"), "Book Antiqua")
rfonts.set(qn("w:hAnsi"), "Book Antiqua")
rfonts.set(qn("w:cs"), "Book Antiqua")
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.5

# margins
for s in doc.sections:
    s.top_margin = Inches(1.0)
    s.bottom_margin = Inches(1.0)
    s.left_margin = Inches(1.0)
    s.right_margin = Inches(1.0)


def ctr(text, bold=False, size=12, italic=False, after=0, before=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(text)
    r.bold = bold
    r.italic = italic
    r.font.size = Pt(size)
    r.font.name = "Book Antiqua"
    return p


def body(text, justify=True):
    p = doc.add_paragraph(text)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if justify else WD_ALIGN_PARAGRAPH.LEFT
    return p


def h_section(num, text):
    """Numbered main heading like the sample (bold 18pt)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"{num}. {text}")
    r.bold = True
    r.font.size = Pt(18)
    r.font.name = "Book Antiqua"
    return p


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(18)
    r.font.name = "Book Antiqua"
    return p


def h_sub(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(13)
    r.font.name = "Book Antiqua"
    return p


def bullet(text):
    p = doc.add_paragraph(text, style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for r in p.runs:
        r.font.name = "Book Antiqua"
        r.font.size = Pt(12)
    return p


def caption(text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(10.5)
    r.font.name = "Book Antiqua"
    return p


def add_figure(path, width=5.9):
    if os.path.exists(path):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        run = p.add_run()
        run.add_picture(path, width=Inches(width))


def shade_header(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "D9D9D9")
    tcPr.append(shd)


def add_table(header, rows, widths=None, bold_last=False, font=9.5):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htext in enumerate(header):
        hdr[i].text = ""
        pr = hdr[i].paragraphs[0]
        pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = pr.add_run(htext)
        run.bold = True
        run.font.size = Pt(font)
        run.font.name = "Book Antiqua"
        shade_header(hdr[i])
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        emph = bold_last and ri == len(rows) - 1
        for i, val in enumerate(row):
            cells[i].text = ""
            pr = cells[i].paragraphs[0]
            pr.alignment = WD_ALIGN_PARAGRAPH.CENTER if i > 0 else WD_ALIGN_PARAGRAPH.LEFT
            run = pr.add_run(str(val))
            run.font.size = Pt(font)
            run.font.name = "Book Antiqua"
            run.bold = emph
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ============================================================= TITLE PAGE
ctr("EdgePilot: Adaptive Telemetry-Budgeted Intelligent Task "
    "Offloading for Dynamic Edge Computing Environments",
    bold=True, size=16, after=18, before=24)

ctr("UROP Project submitted to the", size=12, after=2)
ctr("SRM University – AP, Andhra Pradesh", size=12, after=2)
ctr("for the partial fulfillment of the requirements to award the degree of",
    size=12, after=14)

ctr("Bachelor of Technology", bold=True, size=13, after=0)
ctr("in", size=12, after=0)
ctr("Computer Science and Engineering", bold=True, size=13, after=2)
ctr("School of Engineering and Sciences", bold=True, size=13, after=18)

ctr("Submitted by", size=12, after=2)
ctr("Saunaak Mukherji | AP23110010447", bold=True, size=13, after=18)

ctr("Under the Guidance of", size=12, after=2)
ctr("Dr. Hemanth Kumar", bold=True, size=13, after=18)

ctr("SRM University–AP", bold=True, size=12, after=0)
ctr("Neerukonda, Mangalagiri,", bold=True, size=12, after=0)
ctr("Guntur, Andhra Pradesh – 522 240", bold=True, size=12, after=0)
ctr("November, 2026", bold=True, size=12, after=0)

doc.add_page_break()

# ============================================================= CERTIFICATE
h1("Certificate")
body(
    "This is to certify that the work presented in this report, entitled "
    "“EdgePilot: Adaptive Telemetry-Budgeted Intelligent Task Offloading "
    "for Dynamic Edge Computing Environments”, has been carried out by "
    "Saunaak Mukherji (Registration No. AP23110010447) under my supervision as "
    "part of the Undergraduate Research Opportunity Programme (UROP) in the "
    "Department of Computer Science and Engineering, SRM University–AP. "
    "The work embodied in this report is original and has been conducted by the "
    "candidate in a satisfactory and sincere manner. To the best of my "
    "knowledge, the content of this report has not been submitted elsewhere for "
    "the award of any degree or diploma.")
doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph("Dr. Hemanth Kumar")
p.runs[0].bold = True
body("Supervisor, UROP", justify=False)
body("Department of Computer Science and Engineering", justify=False)
body("SRM University–AP", justify=False)

doc.add_page_break()

# ============================================================= ACKNOWLEDGEMENTS
h1("Acknowledgements:")
body(
    "I would like to express my sincere gratitude to my mentor, Dr. Hemanth "
    "Kumar, for the guidance, patience and encouragement extended to me "
    "throughout this project. His willingness to discuss ideas whenever I "
    "approached him, and the clarity with which he helped me separate a genuine "
    "research question from a merely engineering exercise, shaped the direction "
    "of this work in a way that I could not have managed on my own. The "
    "confidence he placed in me pushed me to keep the investigation honest — "
    "to verify claims against the literature rather than assume them, and to let "
    "the measurements decide what to conclude.")
body(
    "I am also thankful to the Department of Computer Science and Engineering "
    "and the School of Engineering and Sciences at SRM University–AP for "
    "providing the Undergraduate Research Opportunity Programme, which gave me "
    "the time and the structure to attempt a research-grade project while still "
    "an undergraduate. Finally, I thank my family and friends for their "
    "constant support during the long stretches of implementation, debugging "
    "and writing that this work demanded.")

doc.add_page_break()

# ============================================================= ABSTRACT
h1("Abstract")
body(
    "Offloading decisions in mobile edge computing degrade whenever the "
    "scheduler acts on a stale view of volatile network and server state; yet "
    "continuously monitoring that state itself consumes communication and "
    "computation resources. This project studies a scheduler that treats the act "
    "of monitoring as a first-class, budgeted decision rather than as a free "
    "background process. We propose ABVI-Edge (Adaptive Budgeted "
    "Value-of-Information Edge scheduler), a white-box policy that, for every "
    "task, jointly decides (i) whether spending a unit of a finite telemetry "
    "budget to refresh a candidate location’s state is worth its expected "
    "improvement to the placement decision — its value of information "
    "(VoI) — and (ii) where to place the task. Telemetry spending is paced "
    "over time by an adaptive budget shadow price and amplified by task urgency. "
    "To evaluate the idea without physical hardware, a reproducible "
    "discrete-event simulator was built (20–50 end devices, 3–10 "
    "heterogeneous edge servers and a remote cloud, with Ornstein–Uhlenbeck "
    "load and congestion dynamics). ABVI-Edge is compared against seven "
    "baselines across twelve experiments using twenty random seeds and paired "
    "significance tests. Under the medium scenario, ABVI-Edge reduces average "
    "task completion time by 9.8–31.9% and deadline violations by "
    "72–99% relative to the strongest baselines (all p < 10⁻¹⁰), "
    "while dominating the quality-versus-monitoring-overhead frontier: at equal "
    "monitoring spend it is faster and misses fewer deadlines than periodic or "
    "freshness-threshold telemetry, and it self-limits telemetry use even when "
    "budget is abundant. An ablation confirms that the value-of-information, "
    "uncertainty-estimation and adaptive-acquisition components are each "
    "necessary. The platform, experiments and statistics are fully "
    "reproducible.")
h_sub("Keywords")
body(
    "Edge computing; computation offloading; value of information; age of "
    "information; telemetry budget; deadline-aware scheduling; partial "
    "observability; discrete-event simulation.", justify=False)

doc.add_page_break()

# ============================================================= 1. INTRODUCTION
h_section(1, "Introduction")
body(
    "Edge computing moves computation close to where data is produced so that "
    "latency-sensitive applications — augmented reality, industrial "
    "control, real-time analytics on sensor streams — do not have to pay "
    "the full round-trip cost of reaching a distant data centre. In this "
    "setting a recurring question arises for every computational task that a "
    "device generates: should the task run locally on the device’s own "
    "modest processor, be offloaded to a nearby edge server, or be sent all the "
    "way to the cloud? The answer is rarely fixed. It depends on conditions that "
    "change from one second to the next — how heavily each edge server is "
    "currently loaded, how much bandwidth a link has at this instant, whether a "
    "path has become congested — and on the properties of the task itself, "
    "such as how much computation it needs and how soon its deadline falls.")
body(
    "A scheduler that decides on the basis of outdated information makes "
    "mistakes that, in hindsight, were avoidable: it offloads a task to an edge "
    "server that has just become congested, or it keeps a task local when a "
    "neighbouring edge had capacity to spare. The obvious remedy is to monitor "
    "everything, all the time, so that the scheduler always has a fresh picture "
    "of the system. But monitoring is not free. Every telemetry message that "
    "reports a server’s utilization or a link’s congestion consumes "
    "bandwidth, energy and processing. At the scale of hundreds of devices and "
    "many servers, this monitoring plane begins to compete with the very data "
    "plane it is meant to serve. The tension is therefore fundamental: decision "
    "quality improves with fresher information, but freshness costs resources.")
body(
    "This project is built around that tension — decision quality versus "
    "monitoring overhead. Rather than treating telemetry as a fixed background "
    "process running at some pre-set period, we ask whether a scheduler can "
    "decide, moment by moment, when observing is actually worth it. The central "
    "research question is the following:")
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.left_indent = Inches(0.4)
p.paragraph_format.right_indent = Inches(0.4)
r = p.add_run(
    "Can a value-of-information-driven scheduling policy jointly optimise task "
    "placement and telemetry acquisition under a constrained monitoring budget, "
    "while maintaining acceptable task-execution performance in dynamic edge "
    "computing environments?")
r.italic = True
body(
    "To answer it we propose a scheduler, ABVI-Edge, which for every task first "
    "asks whether it is worth spending part of a finite, shared telemetry budget "
    "to reduce its uncertainty about the candidate locations, and only then "
    "decides where to run the task. The decision to observe is driven by the "
    "value of information — the expected reduction in decision cost that a "
    "fresh observation would bring — priced against an adaptive shadow "
    "price that paces the budget across time and scaled by how urgent the task "
    "is. Importantly, the budget is not a cosmetic parameter shown on a "
    "dashboard; it genuinely shapes which probes the policy is willing to buy.")
h_sub("Objectives of the project")
bullet("To formulate task placement and telemetry acquisition as a single "
       "joint decision problem under partial observability and an explicit "
       "monitoring budget, with age-dependent uncertainty.")
bullet("To design a transparent, non-learning scheduling algorithm (ABVI-Edge) "
       "that decides where to place each task and whether a fresh telemetry "
       "probe is worth its cost.")
bullet("To build a reproducible, configurable discrete-event simulator of an "
       "edge–cloud system that requires no physical hardware.")
bullet("To compare the proposed policy fairly against seven baselines on "
       "identical workloads, using many random seeds and proper statistical "
       "tests.")
bullet("To establish, through an ablation study, which components of the "
       "algorithm are actually responsible for any observed improvement.")
h_sub("Organisation of the report")
body(
    "Section 2 surveys the surrounding literature — computation "
    "offloading, age of information, value of information, and adaptive network "
    "telemetry — and identifies the specific gap this work addresses. "
    "Section 3 presents the system model in full: the entities, the dynamics, "
    "the partial-observability belief, the monitoring budget and the objective; "
    "it then develops the proposed ABVI-Edge algorithm, describes the "
    "simulation environment and baselines, and reports the experimental "
    "results. Section 4 draws concluding remarks, Section 5 outlines future "
    "work, and the references follow.")

# ============================================================= 2. LITERATURE SURVEY
h_section(2, "Literature Survey")
body(
    "The problem studied here sits at the meeting point of several mature but "
    "largely separate bodies of research. A systematic reading of the recent "
    "literature (2018–2026, with a few foundational works) was carried out "
    "to understand what has already been achieved and to make sure the proposed "
    "contribution is not simply a restatement of an existing result. Each paper "
    "consulted was recorded together with a verification level — whether "
    "its full text, only its abstract, or only its metadata was accessible "
    "— so that no finding is overstated and no citation is fabricated.")

h_sub("2.1 Computation offloading and placement")
body(
    "A large literature optimises where a task should execute in order to "
    "minimise latency, energy, or deadline violations. Wang et al. (IEEE "
    "Transactions on Mobile Computing, 2020) and the deadline-constrained "
    "energy-aware formulation in the EURASIP Journal on Wireless Communications "
    "and Networking (2021) are representative, as are the firm-deadline Markov "
    "decision process of 2022 and the two comprehensive surveys of "
    "reinforcement-learning-based offloading (Journal of Network and Computer "
    "Applications, 2023; ACM Computing Surveys, 2023). These works are powerful, "
    "but they almost always assume that the state needed to make a decision "
    "— server loads, link conditions — is already available to the "
    "scheduler. The cost of obtaining that state is treated as outside the "
    "problem.")

h_sub("2.2 Offloading under partial or imperfect observations")
body(
    "A second thread accepts that the scheduler does not have perfect "
    "information. Badnava et al. (2023), the closest related work to this "
    "project, studies energy-efficient, deadline-aware edge computing as a "
    "bandit-learning problem with partial observations over multiple channels. "
    "Related efforts cast service migration as a partially observable Markov "
    "decision process (2022) and study reliable offloading under imperfect "
    "channel state information (IEEE Transactions on Network and Service "
    "Management, 2024). These methods act well under uncertainty, but they do "
    "not actively decide to acquire more information at a priced cost — "
    "they live with whatever observations arrive.")

h_sub("2.3 Age of Information and Value of Information")
body(
    "Age of Information (AoI) quantifies how stale the most recent update about "
    "a remote quantity is; a body of work minimises AoI by scheduling "
    "transmissions over heterogeneous channels (2021) or under partial "
    "observation in wireless uplinks (2022). Value of Information (VoI) goes a "
    "step further and asks how much a fresh observation would actually improve "
    "a decision, so that observations can be bought selectively under a budget. "
    "Foundational and applied VoI work — spatio-temporal sensor scheduling "
    "(2018), optimal information updating based on VoI (2021), and a recent "
    "semantic VoI metric for networked control (2024) — establishes the "
    "machinery, but targets generic estimation or control tasks rather than the "
    "specific decision of where to offload a computational task.")

h_sub("2.4 Adaptive network telemetry")
body(
    "On the systems side, a very active line of research reduces monitoring "
    "overhead directly on the monitoring plane: probabilistic in-band telemetry "
    "(PINT, SIGCOMM 2020), programmable event-triggered telemetry (CloudNet "
    "2019), accuracy-adaptive lightweight telemetry (LINT, 2021), adaptive "
    "fine-grained monitoring (FineMon, 2024), matrix-completion-based "
    "network-wide telemetry (INT-MC, 2024) and a deep-reinforcement-learning "
    "telemetry controller (AdapINT, 2024). All of these make monitoring cheaper "
    "or smarter, but they optimise the telemetry system in isolation — the "
    "savings are not coupled to any downstream task-placement decision.")

h_sub("2.5 Synthesis and the research gap")
body(
    "Reading these threads together, a clear pattern emerges. Offloading under "
    "deadlines and energy is well solved when state is available. Acting under "
    "partial observations is solved with bandits and POMDPs. Keeping a monitor "
    "fresh (AoI) and valuing an observation under a measurement budget (VoI) is "
    "solved — but in monitoring and control contexts, not for offloading. "
    "Reducing telemetry overhead adaptively is solved — but on the network "
    "plane alone. What the survey did not find was a single method that closes "
    "the loop between the monitoring plane and the offloading decision: one that "
    "treats a telemetry probe as a per-decision action priced against an "
    "explicit monitoring budget, chooses what to observe by its value of "
    "information for the placement decision specifically, and does so jointly "
    "with the placement itself in a dynamic, deadline-driven edge environment. "
    "The closest point, Badnava et al. (2023), never pays to refresh state and "
    "uses neither AoI/VoI nor a monitoring budget.")
body(
    "This defines the gap addressed in this project, stated deliberately "
    "narrowly and candidly. The individual ingredients — VoI, AoI, budgeted "
    "sensing, adaptive telemetry, partial-observation offloading — are all "
    "established and are not claimed to be new. What appears to be "
    "under-explored is their joint, decision-coupled, budgeted integration for "
    "computation offloading. If a reader knows of a paper combining all three "
    "pillars — offloading, an explicit telemetry budget and VoI-driven "
    "acquisition — then the contribution should be understood more "
    "narrowly as the specific shadow-price pacing and urgency-weighted myopic "
    "VoI formulation developed here, together with its empirical "
    "characterisation of the quality-versus-overhead frontier, which remain a "
    "concrete and reproducible contribution regardless. The feature-by-feature "
    "comparison that supports this assessment is given in Table 1.")

caption("Table 1. Feature comparison of representative related work against the "
        "combination studied in this project. A tick indicates the feature is "
        "present; a dash indicates it is absent.")
add_table(
    ["Work (year)", "Offloading", "Telemetry-aware", "Monitoring budget",
     "AoI", "VoI", "Joint place+probe"],
    [
        ["Wang, TMC (2020)", "✓", "–", "–", "–", "–", "–"],
        ["Firm-deadline MDP (2022)", "✓", "–", "–", "–", "–", "–"],
        ["Badnava et al. (2023)", "✓", "partial", "–", "–", "–", "–"],
        ["AoI scheduling (2021–22)", "–", "✓", "✓", "✓", "–", "–"],
        ["VoI sensing (2018–24)", "–", "✓", "✓", "part", "✓", "–"],
        ["PINT / FineMon / AdapINT", "–", "✓", "part", "–", "–", "–"],
        ["ABVI-Edge (this work)", "✓", "✓", "✓", "✓", "✓", "✓"],
    ],
    widths=[1.7, 0.85, 1.0, 1.0, 0.55, 0.55, 1.1],
    bold_last=True, font=9)

# ============================================================= 3. SYSTEM MODEL
h_section(3, "System Model")
body(
    "This section specifies the system that the simulator implements, the "
    "proposed algorithm that operates within it, the experimental setup, and "
    "the results obtained. The same symbols are used throughout.")

h_sub("3.1 Entities and dynamics")
body(
    "The environment contains N ∈ [20, 50] end devices, each of which "
    "generates tasks and can execute them locally on a weak processor; M ∈ "
    "[3, 10] heterogeneous edge servers of differing capacity; and a single "
    "remote cloud that is fast to compute on but reached over a high-latency, "
    "bandwidth-limited wide-area link. For a task originating at a device, the "
    "set of candidate processing locations is therefore the device itself, every "
    "edge server, and the cloud. Tasks arrive as a Poisson process. Each task "
    "carries an arrival time, a compute demand (in millions of cycles), input "
    "and output data sizes, an absolute deadline, and a priority level; demands "
    "and sizes are drawn from log-normal distributions, and each deadline is set "
    "relative to a scheduler-independent reference completion time scaled by a "
    "random slack factor, so that no single policy is favoured.")
body(
    "Each processing location has a fixed capacity and a time-varying "
    "utilization driven by exogenous background load. The utilization is modelled "
    "as a mean-reverting Ornstein–Uhlenbeck (OU) process, which captures "
    "the way real server load drifts and reverts rather than jumping randomly. "
    "The compute time of a task on a location inflates with utilization in the "
    "manner of an M/M/1 queue: as a server approaches saturation its effective "
    "service rate collapses. Every network link has a base bandwidth, a base "
    "one-way latency, and a time-varying multiplicative congestion factor that "
    "follows a log-space OU process, so transfer time grows and latency "
    "stretches as a path becomes congested. The completion time of an offloaded "
    "task is the sum of the input-transfer time, the remote compute time, and "
    "the output-transfer time; a locally executed task pays only its local "
    "compute time. Energy is an estimated quantity derived from analytic power "
    "models for device computation, device transmission and server computation; "
    "it is never presented as a hardware measurement.")

h_sub("3.2 Partial observability and the belief")
body(
    "Crucially, the scheduler does not observe the true utilizations and "
    "congestions directly. Instead it keeps a belief for each quantity: the last "
    "observed value together with the time at which it was observed. The Age of "
    "Information of a belief is simply the elapsed time since that last "
    "observation. Because the underlying process is Ornstein–Uhlenbeck, the "
    "predictive distribution of the current value, given an observation of a "
    "certain age, is Gaussian with a mean that decays from the observed value "
    "towards the long-run average and a variance that grows with age towards the "
    "stationary variance. In plain terms, the older an observation is, the less "
    "the scheduler should trust it, and this loss of trust is quantified exactly "
    "rather than guessed. This closed-form, age-dependent uncertainty is what "
    "makes a principled value-of-information calculation possible.")

h_sub("3.3 Decision variables, monitoring budget and objective")
body(
    "For each task the policy makes two coupled decisions: a telemetry set — "
    "which locations to probe (refresh) before committing, where probing a "
    "location resets its Age of Information to zero and costs one unit of "
    "monitoring traffic — and a placement — where the task actually "
    "executes. The monitoring budget is made explicit. Over a budget window the "
    "total monitoring traffic is bounded by a normalized budget β times the "
    "cost of probing every probeable location on every decision. Thus β = 1 "
    "means the system could in principle observe everything, every time, while "
    "β = 0.3 means a seventy-percent reduction against that reference. The "
    "budget is a hard constraint enforced by the telemetry manager and, more "
    "importantly, it actively shapes the policy through the adaptive shadow "
    "price described below.")
body(
    "The per-task objective is a decision cost that combines expected completion "
    "time, the risk of missing the deadline (weighted by a penalty and by task "
    "priority) and, secondarily, estimated energy, with all expectations taken "
    "over the belief. The system minimises the time-average of this cost subject "
    "to the budget constraint. To isolate specifically the cost of acting on "
    "stale information, we also define scheduling regret: the realised "
    "completion time of the chosen placement minus the completion time the task "
    "would have had under the placement an omniscient oracle (one that sees the "
    "true state) would have selected. Regret is zero exactly when the chosen "
    "placement turns out to be the realised best, and it grows when stale beliefs "
    "cause a misplacement. Regret is the central quantity that telemetry "
    "decisions aim to reduce per unit of budget spent. The problem is genuinely "
    "joint: placement quality depends on belief accuracy, belief accuracy costs "
    "budget, and the budget is finite and shared across all future tasks, so "
    "optimising placement and telemetry separately is sub-optimal.")

h_sub("3.4 The proposed algorithm: ABVI-Edge")
body(
    "ABVI-Edge (Adaptive Budgeted Value-of-Information Edge scheduler) is a "
    "white-box controller — it uses no training, no reward shaping and no "
    "reinforcement learning. On each task arrival it first computes, for every "
    "candidate location, the decision cost under the current belief, and the "
    "best achievable cost. It then considers buying information. The value of "
    "information of probing a location is defined as the expected reduction in "
    "decision cost that revealing that location’s true state would bring. "
    "This expectation is estimated by drawing a small number of Monte-Carlo "
    "samples from the age-dependent belief — never from the ground truth "
    "— and, for each sample, asking what the decision cost would be after "
    "the reveal. An inner minimum captures the key insight that information only "
    "helps when the revealed value could actually flip the decision relative to "
    "the best alternative candidate. Consequently the value of information is "
    "large exactly when a location is both uncertain (old, high variance) and a "
    "plausible winner; a location that is stale but irrelevant, or relevant but "
    "already fresh, has near-zero value and is not probed. This is deliberately "
    "more intelligent than a fixed rule such as “refresh whenever staleness "
    "exceeds a threshold”, which ignores whether the refresh would change "
    "anything at all.")
body(
    "Each probe draws on the shared budget, so it must be priced. ABVI-Edge "
    "prices a probe with an adaptive shadow price that rises when the budget is "
    "being spent faster than an even-pacing schedule would allow, and falls when "
    "spending is behind schedule — thereby automatically reserving budget "
    "for future, potentially more valuable decisions. The willingness to pay is "
    "further scaled by task urgency: a task with a tight deadline or high "
    "priority tolerates a higher price for the same value of information. The "
    "policy then acquires information greedily and sequentially: it repeatedly "
    "probes the location with the greatest positive net value (urgency times "
    "value of information, minus the shadow price), re-evaluating all beliefs "
    "after each probe because resolving one location changes the value of "
    "resolving another, and it stops as soon as no remaining probe is worth its "
    "price, a per-decision probe cap is reached, or the budget is exhausted. "
    "Finally it places the task at the lowest-cost candidate under the updated "
    "belief. Pseudocode is given in Figure 1.")

# pseudocode as monospace block
pc = doc.add_paragraph()
pc.paragraph_format.left_indent = Inches(0.3)
pc.paragraph_format.space_after = Pt(2)
pc_lines = (
    "decide(task k at time t):\n"
    "    slack  <- deadline_k - t\n"
    "    costs  <- belief_cost(k, t)            # cost C(l) for all candidates\n"
    "    if adaptive acquisition enabled:\n"
    "        lambda <- shadow_price(t)\n"
    "        repeat up to max_probes times:\n"
    "            if budget cannot afford one probe: break\n"
    "            C*  <- min_l costs[l];  m* <- best expected time\n"
    "            urg <- urgency(k, t, m*)\n"
    "            l^, net <- argmax over unprobed l of (urg * VoI(l) - lambda)\n"
    "            if l^ is None or net <= 0: break   # no probe worth buying\n"
    "            observe(l^)                        # spend 1 probe, reveal state\n"
    "            costs <- belief_cost(k, t)         # beliefs changed; re-evaluate\n"
    "    x_k <- argmin_l costs[l]                   # place under updated belief\n"
    "    return (x_k, probed)"
)
r = pc.add_run(pc_lines)
r.font.name = "Consolas"
r.font.size = Pt(9)
caption("Figure 1. ABVI-Edge decision procedure for a single task. The loop is "
        "greedy and sequential; it buys a probe only when its urgency-weighted "
        "value of information exceeds the adaptive budget price.")
body(
    "The per-decision time complexity is O(P·K·R), where K is the number "
    "of candidate locations, R the number of value-of-information samples and P "
    "the per-decision probe cap — all small constants (tens), involving no "
    "inner simulation — so the measured decision time is only a few "
    "milliseconds. The space complexity is linear in the number of candidates. "
    "A reinforcement-learning agent was deliberately avoided: the "
    "value-of-information computation requires a calibrated predictive variance, "
    "which the OU belief supplies in closed form but a point-prediction "
    "regressor does not; and a white-box policy is interpretable (every probe is "
    "justified by a logged number), reproducible, and free of training-data and "
    "reward-shaping pitfalls. Edge cases are handled explicitly: a zero budget "
    "degrades gracefully to estimate-based placement without any probing; a "
    "failed edge server becomes infeasible and is automatically excluded, with a "
    "run-time fallback to the cloud; and an impossible deadline is counted as a "
    "violation rather than causing a crash.")

h_sub("3.5 Simulation environment, baselines and metrics")
body(
    "Everything runs in a discrete-event simulator written in Python; no "
    "physical devices or servers are required, which is precisely what makes the "
    "study tractable. The OU state is advanced between Poisson task arrivals, "
    "the realised execution of each task is evaluated under the true state at "
    "its arrival, and an omniscient oracle is evaluated alongside so that regret "
    "is well defined. Ten preset scenarios are provided — light, medium and "
    "heavy workloads, a sudden workload spike, network congestion, edge-server "
    "failure, highly heterogeneous capacities, tight deadlines, a limited "
    "telemetry budget, and a rapidly changing network — all driven by "
    "reproducible random seeds. A fairness guarantee, enforced by automated "
    "tests, ensures that every scheduler faces identical per-seed task arrivals, "
    "topology and environmental traces, so that no algorithm is advantaged by a "
    "different workload.")
body(
    "ABVI-Edge is compared against seven baselines of increasing sophistication: "
    "local-only execution; cloud-only execution; random offloading; "
    "nearest-edge placement; lowest-estimated-time placement, which is greedy on "
    "the stale belief but never probes; periodic telemetry, which probes all "
    "locations on a fixed period; and freshness-aware telemetry, which probes a "
    "location whenever its Age of Information exceeds a threshold. The first four "
    "are naive or heuristic references; the last three are genuine telemetry "
    "strategies that let us ask whether ABVI-Edge’s selectivity is actually "
    "worth anything. More than twenty metrics are recorded, including average, "
    "median and 95th-percentile completion time, deadline-violation rate, "
    "success rate, average and 95th-percentile scheduling regret, estimated "
    "energy, telemetry requests and bytes, normalized telemetry and monitoring "
    "overhead, average information age, edge utilization, throughput and "
    "per-decision wall-clock time.")

h_sub("3.6 Experimental results")
body(
    "All headline numbers are means over twenty random seeds. The full "
    "experimental suite comprises twelve experiments (A–L): an algorithm "
    "comparison, a telemetry-budget sweep, six sensitivity sweeps (workload "
    "intensity, cloud latency, edge bandwidth, deadline slack, device count and "
    "edge count), three stress scenarios (workload spike, congestion and edge "
    "failure) and an ablation. The main comparison under the medium scenario "
    "(30 devices, 5 edges, β = 0.3) is given in Table 2.")

caption("Table 2. Experiment A — algorithm comparison, medium scenario, "
        "means over 20 seeds. Lower is better for all columns except telemetry "
        "count, which is a cost. The last row is the proposed policy.")
add_table(
    ["Scheduler", "Compl. (s)", "p95 (s)", "Viol.", "Regret (s)",
     "Energy (J)", "Telem.", "Decide (ms)"],
    [
        ["Local-only", "3.626", "9.672", "0.953", "3.308", "4.352", "0", "0.002"],
        ["Cloud-only", "0.479", "0.816", "0.119", "0.160", "0.509", "0", "0.001"],
        ["Random", "1.138", "3.761", "0.356", "0.818", "1.187", "0", "0.010"],
        ["Nearest-edge", "0.646", "1.825", "0.205", "0.328", "0.622", "0", "0.004"],
        ["Lowest-est-time", "0.431", "0.848", "0.084", "0.112", "0.530", "0", "0.720"],
        ["Periodic-telemetry", "0.361", "0.668", "0.034", "0.043", "0.569", "1033", "0.694"],
        ["Freshness-aware", "0.374", "0.699", "0.041", "0.054", "0.563", "719", "0.687"],
        ["ABVI-Edge (ours)", "0.326", "0.568", "0.010", "0.007", "0.561", "1838", "2.859"],
    ],
    widths=[1.55, 0.8, 0.65, 0.6, 0.75, 0.75, 0.6, 0.85],
    bold_last=True, font=9)
body(
    "ABVI-Edge achieves the best completion time, 95th-percentile latency, "
    "deadline-violation rate and regret. Against the strongest telemetry "
    "baseline, periodic telemetry, it improves completion time by 9.8% "
    "(p = 2.4×10⁻¹⁴), deadline violations by 71.7% "
    "(p = 8×10⁻¹²) and regret by 82.8% "
    "(p = 4×10⁻¹⁹); against cloud-only it improves completion "
    "by 31.9% and violations by 91.9%. One nuance is reported openly: in this "
    "particular scenario the budget is ample, so ABVI-Edge issues more probes "
    "than periodic telemetry (1838 versus 1033). The efficiency claim is "
    "therefore “better quality within budget” here, and is established "
    "rigorously by the budget sweep (where overhead is matched) and by the "
    "ablation (where removing the value-of-information component spends more "
    "telemetry for worse results).")
add_figure(os.path.join(FIG, "expA_algorithm_comparison.png"), width=6.0)
caption("Figure 2. Experiment A — comparison of all eight schedulers across "
        "the principal performance metrics (means over 20 seeds).")
body(
    "The budget sweep (Experiment B) is the decisive test, because it varies the "
    "normalized budget β and asks how each telemetry strategy trades quality "
    "against overhead. From β ≥ 0.1 onward ABVI-Edge is strictly better "
    "on both completion time and deadline violations than periodic and "
    "freshness telemetry, which plateau because their probe policies are rate- "
    "or threshold-capped and blind to value. At a normalized telemetry of about "
    "0.10, ABVI-Edge already beats periodic telemetry’s best operating "
    "point — better quality at equal monitoring spend. Strikingly, even when "
    "the budget is unlimited (β = 1.0), ABVI-Edge consumes only about "
    "nineteen percent of the reference monitoring cost, because the "
    "value-of-information test gates spending: once no probe is worth its price, "
    "it simply stops. It does not waste budget merely because budget is "
    "available. Only at the very tightest budgets (β ≤ 0.05) do all "
    "telemetry methods saturate and ABVI-Edge’s advantage shrinks to a tie "
    "— selectivity needs enough budget to express itself, and this is "
    "reported rather than hidden.")
add_figure(os.path.join(FIG, "expB_budget_pareto.png"), width=5.4)
caption("Figure 3. Experiment B — the quality-versus-monitoring-overhead "
        "frontier. ABVI-Edge (upper-left) dominates periodic and "
        "freshness-threshold telemetry and reaches operating points they never "
        "achieve.")
body(
    "Across the six sensitivity sweeps (Experiments C–H) ABVI-Edge retains "
    "the lowest completion-time and violation curves, with its margin over "
    "cloud-only widening as edges become more attractive (more bandwidth, more "
    "edges) and as deadlines tighten — precisely the regimes where "
    "correctly selecting an uncongested edge, which requires fresh information, "
    "matters most. The three stress scenarios (Experiments I–K) tell the "
    "same story even more sharply: the advantage is largest under network "
    "congestion, where completion time falls by 20.7% and violations by 72% "
    "relative to the best baseline, because volatility is exactly what makes "
    "stale information damaging; and the policy handles a mid-run edge-server "
    "failure gracefully.")
caption("Table 3. Experiment L — ablation at β = 0.2. Each row removes "
        "one component of ABVI-Edge. The full policy is the first row.")
add_table(
    ["Variant", "Completion (s)", "Violations", "Regret (s)", "Telemetry"],
    [
        ["full (all components)", "0.330", "0.009", "0.010", "1672"],
        ["no value-of-information", "0.386", "0.046", "0.065", "2159"],
        ["no uncertainty estimation", "0.432", "0.089", "0.113", "0"],
        ["no adaptive acquisition", "0.440", "0.077", "0.121", "0"],
        ["no urgency weighting", "0.332", "0.012", "0.013", "1341"],
        ["no budget pacing", "0.328", "0.010", "0.008", "1773"],
    ],
    widths=[1.9, 1.2, 1.0, 1.0, 1.0], font=10)
body(
    "The ablation is the clearest evidence that the advantage comes from smart "
    "allocation rather than sheer probe volume. Removing the "
    "value-of-information component degrades completion time (0.330 to 0.386) "
    "and violations (0.009 to 0.046) while spending more telemetry (1672 to "
    "2159) — more monitoring, worse outcomes. Removing uncertainty "
    "estimation or adaptive acquisition collapses probing to zero and regresses "
    "the policy to stale-estimate performance, confirming that both are "
    "essential. Urgency weighting gives a small, consistent gain at lower "
    "telemetry cost, and budget pacing matters more as β shrinks. "
    "Statistically, with twenty seeds per configuration, mean, standard "
    "deviation and 95% confidence intervals are reported, and headline "
    "comparisons use a paired Wilcoxon signed-rank test cross-checked with a "
    "paired t-test; all thirty-four headline comparisons in Experiment A are "
    "significant at the five-percent level except ABVI-versus-freshness on "
    "energy, which is expected because both offload similarly.")

# ============================================================= CONCLUDING
h1("Concluding Remarks:")
body(
    "This project set out to test a single idea: that a scheduler can do better "
    "by treating the act of monitoring as a budgeted, value-driven decision made "
    "jointly with task placement, rather than as a free background process. The "
    "evidence collected supports that idea. The proposed policy, ABVI-Edge, "
    "spends monitoring effort where it actually changes decisions — it "
    "refreshes exactly the pivotal candidate locations, which is why it beats "
    "stale-estimate scheduling; it avoids spending on locations that are stale "
    "but irrelevant or already fresh enough, which is why it beats blind "
    "periodic and freshness-threshold telemetry; and it stops probing once "
    "beliefs are good enough, which is why it self-limits even when budget is "
    "abundant. The scheduling-regret metric makes this mechanism legible: "
    "ABVI-Edge drives regret down to a near-zero 0.007 seconds while consuming "
    "only a fraction of the achievable monitoring cost.")
body(
    "It is equally important to be candid about the limits of these claims. The "
    "background load in the simulator is exogenous (open-loop): the "
    "scheduler’s own placements do not feed back into queue growth, which a "
    "closed-loop queueing model would capture. Realised completion time is "
    "evaluated using the state at a task’s arrival rather than integrated "
    "over its whole execution. Energy is an estimated quantity from analytic "
    "power models, not a hardware measurement, and is never presented "
    "otherwise. The value-of-information computation is myopic — single-step "
    "per task — rather than a full sequential, POMDP-optimal information "
    "value. The OU predictive belief is treated as Gaussian and truncated, so "
    "its tails are approximate. Finally, the results are simulation-based, so "
    "absolute numbers depend on the chosen distributions; for that reason the "
    "emphasis throughout has been on relative trends and sensitivity sweeps "
    "rather than on point values. The novelty is also stated narrowly: the "
    "individual ingredients are established, and it is their joint, "
    "decision-coupled, budgeted integration for offloading that is the "
    "under-explored contribution. Within these honest bounds, the central "
    "hypothesis holds: treating telemetry acquisition as a budgeted, "
    "value-driven decision jointly with placement measurably improves offloading "
    "in dynamic edge environments, with the benefit concentrated exactly where "
    "theory predicts — in volatile, deadline-pressured conditions.")

# ============================================================= FUTURE WORK
h1("Future Work:")
body(
    "Several directions follow naturally from this study. The most significant "
    "is to replace the myopic, single-step value-of-information estimate with a "
    "sequential formulation — a partially observable Markov decision "
    "process, possibly with a learned belief — so that the value of a probe "
    "accounts for its effect on future decisions and not only the present one; "
    "this is where a reinforcement-learning extension would genuinely add value, "
    "and it is noted precisely because it was deliberately avoided in the core "
    "design to keep the mechanism under study transparent. A second direction is "
    "to move from the current open-loop load model to a closed-loop queueing "
    "model in which the scheduler’s own placements influence future "
    "utilization, coupling decisions and load. A third is to extend the "
    "value-of-information calculation to batches of correlated probes and to "
    "exploit correlation between neighbouring locations’ states, rather "
    "than treating each probe independently. Beyond the model itself, the policy "
    "should be validated against real telemetry traces instead of synthetic OU "
    "dynamics, and the estimated energy model should be checked against a "
    "hardware-in-the-loop measurement. Finally, fairness across devices — "
    "ensuring that the budget and the resulting quality are shared equitably "
    "rather than monopolised by the most urgent tasks — is an important "
    "objective that the current cost function does not yet address. Each of "
    "these would strengthen either the realism or the generality of the result "
    "without changing the core finding on which the project rests.")

# ============================================================= REFERENCES
h1("References")
refs = [
    "R. Ben Basat, S. Ramanathan, Y. Li, G. Antichi, M. Yu, and M. "
    "Mitzenmacher, “PINT: Probabilistic In-band Network Telemetry,” in "
    "Proc. ACM SIGCOMM, 2020. [Online]. Available: "
    "https://arxiv.org/pdf/2007.03731",
    "J. Vestin, A. Kassler, D. Bhamare, K.-J. Grinnemo, J.-O. Andersson, and "
    "G. Pongracz, “Programmable Event Detection for In-Band Network "
    "Telemetry,” in Proc. IEEE CloudNet, 2019. [Online]. Available: "
    "https://arxiv.org/abs/1909.12101",
    "S. R. Chowdhury, R. Boutaba, et al., “LINT: Accuracy-adaptive and "
    "Lightweight In-band Network Telemetry,” in Proc. IFIP/IEEE IM, 2021.",
    "H. Ji, K. Xie, J. Wen, Q. Zhang, G. Xie, and W. Liang, “FineMon: An "
    "Innovative Adaptive Network Telemetry Scheme for Fine-Grained, "
    "Multi-Metric Data Monitoring,” Proc. ACM on Management of Data "
    "(PACMMOD), 2024. doi: 10.1145/3639267.",
    "“INT-MC: Low-Overhead In-Band Network-Wide Telemetry Based on Matrix "
    "Completion,” ACM, 2024. [Online]. Available: "
    "https://dl.acm.org/doi/10.1145/3700433",
    "“AdapINT: A Flexible and Adaptive In-Band Network Telemetry System "
    "Based on Deep Reinforcement Learning,” IEEE Trans. Network and "
    "Service Management, 2024. [Online]. Available: "
    "https://arxiv.org/pdf/2310.19331",
    "B. Badnava, K. Roach, K. Cheung, M. Hashemi, and N. B. Shroff, "
    "“Energy-Efficient Deadline-Aware Edge Computing: Bandit Learning with "
    "Partial Observations in Multi-Channel Systems,” arXiv preprint, 2023. "
    "[Online]. Available: https://arxiv.org/abs/2308.06647",
    "J. Wang et al., “Deep Reinforcement Learning for Task Offloading in "
    "Mobile Edge Computing Systems,” IEEE Trans. Mobile Computing, 2020.",
    "“Energy-aware Task Offloading with Deadline Constraint in Mobile Edge "
    "Computing,” EURASIP J. Wireless Communications and Networking, 2021. "
    "[Online]. Available: "
    "https://link.springer.com/article/10.1186/s13638-021-01941-3",
    "“Optimal Task Offloading Policy in Edge Computing Systems with Firm "
    "Deadlines,” arXiv preprint, 2022. [Online]. Available: "
    "https://arxiv.org/pdf/2210.15855",
    "“A Comprehensive Survey on Reinforcement-Learning-based Computation "
    "Offloading Techniques in Edge Computing Systems,” J. Network and "
    "Computer Applications, 2023.",
    "“Reinforcement Learning Methods for Computation Offloading: A "
    "Systematic Review,” ACM Computing Surveys, 2023. doi: 10.1145/3603703.",
    "“Minimizing Age of Information via Scheduling over Heterogeneous "
    "Channels,” 2021. [Online]. Available: "
    "https://par.nsf.gov/biblio/10284912",
    "J. Liu, R. Zhang, A. Gong, and H. Chen, “Optimizing Age of "
    "Information in Wireless Uplink Networks with Partial Observations,” "
    "arXiv preprint, 2022. [Online]. Available: https://arxiv.org/abs/2202.03152",
    "“Value-of-Information in Spatio-Temporal Systems: Sensor Placement and "
    "Scheduling,” Reliability Engineering & System Safety, 2018.",
    "“Optimal Information Updating based on Value of Information,” 2021. "
    "[Online]. Available: https://par.nsf.gov/servlets/purl/10163521",
    "“Foundations of Value of Information: A Semantic Metric for Networked "
    "Control Systems Tasks,” arXiv preprint, 2024. [Online]. Available: "
    "https://arxiv.org/abs/2403.11927",
    "“Service Migration for Mobile Edge Computing based on Partially "
    "Observable Markov Decision Processes,” Computers & Electrical "
    "Engineering, 2022.",
    "“Reliable Task Offloading in Sustainable Edge Computing with Imperfect "
    "Channel State Information,” IEEE Trans. Network and Service "
    "Management, 2024. doi: 10.1109/TNSM.2024.3456568.",
    "“Task Offloading Based on LSTM Prediction and Deep Reinforcement "
    "Learning for Efficient Edge Computing in IoT,” Future Internet "
    "(MDPI), 2022. doi: 10.3390/fi14020030.",
]
for i, rtext in enumerate(refs, 1):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Inches(0.35)
    p.paragraph_format.first_line_indent = Inches(-0.35)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(f"[{i}]  {rtext}")
    r.font.size = Pt(11)
    r.font.name = "Book Antiqua"

out = os.path.join(ROOT, "EdgePilot_UROP_Report_Saunaak_Mukherji.docx")
doc.save(out)
print("saved:", out)
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables))
