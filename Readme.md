# VyalaArchon Learning Platform

> **"We don't just find your quantum exposure — we certify your team to fix it."**

An enterprise multi-agent system that scans an organisation's codebase for post-quantum cryptography (PQC) vulnerabilities, generates role-based certification study plans for the engineering team, assesses readiness through grounded NIST-cited questions, and gives managers real-time visibility into team quantum readiness.

Built for the **Microsoft Agents League Hackathon** — Reasoning Agents track.

---

## The Problem

Quantum computers running Shor's algorithm will break RSA, ECDSA, and ECDH. The NSA CNSA 2.0 mandate requires national security systems to migrate to NIST-approved post-quantum cryptography by **2030**. Most engineering teams don't know where their exposure is, what to learn, or how to prioritise.

VyalaArchon fixes that.

---

## Demo

```
User: "Assess our payments-service repo and build a PQC study plan for the team."

→ Assessment Agent scans the repo
  Found: RSA-2048 in auth/jwt.py (CRITICAL — breakable in ~1.5 days at 2030 hardware)
  Found: ECDH-256 in tls/handshake.py (CRITICAL — breakable in ~41 minutes)

→ QASS Simulator builds Shor's circuit
  RSA-2048: 4,099 logical qubits · 122,970 physical qubits · gate depth 8.4B

→ Foundry IQ grounds the recommendation
  "Replace RSA-2048 with ML-DSA-44 (FIPS 204 §3.3)" [cited]

→ Confidence Gate validates (confidence: 0.92 ✓)

→ Learning Path Curator builds curriculum
  "Week 1: ML-KEM theory (3h, Tuesday/Thursday mornings)"

→ Study Plan Generator adapts to Work IQ signals
  EMP-001: 22h meetings/week → capped at 5h study/week, morning slots

→ Manager Insights Agent surfaces dashboard
  Team readiness: 43% · 3 CRITICAL gaps · NOT on track for 2030 CNSA 2.0
```

---

## 8-Step Reasoning Chain

| Step | Agent | What it does |
|------|-------|-------------|
| ① | Repo Scanner | GitHub + GitLab + local git, branch-aware |
| ② | AST Classifier | Tree-sitter + heuristics, zero false positives |
| ③ | QASS Simulator | Builds actual Qiskit circuit; estimates logical/physical qubits, gate depth, time-to-break at 2030 QLDPC error rates |
| ④ | Risk Scorer | CVSS-Q × QASS urgency multiplier, harvest-now-decrypt-later exposure |
| ⑤ | Foundry IQ Query | Grounded NIST FIPS 203/204/205 retrieval with citations |
| ⑥ | Plan Builder | Code-level migration guidance + hybrid transition timelines |
| ⑦ | Confidence Gate | Refuses to recommend if IQ confidence < 0.70 |
| ⑧ | Quantum Visualizer | SVG circuit diagram of the exact Shor's/Grover's attack |

---

## Multi-Agent Architecture

```
User Request
     │
     ▼
┌─────────────────────┐
│  Orchestrator Agent │  ← Intent classification + routing
└──────────┬──────────┘
           │
     ┌─────┴──────────────────────────────────┐
     │                                        │
     ▼                                        ▼
┌────────────────┐                 ┌──────────────────────┐
│ Assessment     │                 │ Manager Insights     │
│ Agent          │                 │ Agent                │
│ (8-step chain) │                 │ Fabric IQ semantic   │
└────────┬───────┘                 │ layer — team,roles,  │
         │                        │ readiness, 2030 risk  │
         ▼                        └──────────────────────┘
┌────────────────────┐
│ Learning Path      │
│ Curator Agent      │
│ Foundry IQ → NIST  │
│ study materials    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Study Plan         │
│ Generator Agent    │
│ Work IQ signals    │
│ + Fabric IQ roles  │
└────────────────────┘
```

---

## Microsoft IQ Integration

| IQ Layer | How it's used |
|----------|--------------|
| **Foundry IQ** | 4-source PQC knowledge base — NIST FIPS 203/204/205/206, CVE database, IETF RFCs, NSA CNSA 2.0. Every recommendation is cited. |
| **Work IQ** | Synthetic work signals (meeting load, focus hours, preferred study windows) adapt the study schedule to each engineer's real workload |
| **Fabric IQ** | Semantic ontology: employee → role → certification → skill gap → readiness score → manager action. Powers the insights dashboard. |

---

## Quantum Attack Surface Simulator (QASS)

The QASS builds actual Qiskit circuits for each vulnerability found and estimates real attack resources.

**RSA-2048 (Shor's algorithm):**
- Logical qubits: **4,099** (Beauregard 2n+3 formula)
- Physical qubits: **122,970** (QLDPC at 2030 error rates)
- Gate depth: **8,388,608,000**
- Time to break: **~1.5 days** at projected 2030 hardware
- Source: Gidney & Ekerå 2025 · Iceberg Quantum 2026 (arXiv:2602.11457)

**AES-128 (Grover's algorithm):**
- Grover iterations: **1.45 × 10¹⁹** — NOT breakable by 2030
- Effective key strength reduced: 128-bit → 64-bit
- Recommendation: upgrade to AES-256

---

## Foundry IQ Knowledge Base Setup

The knowledge base must be provisioned before the Azure agents will work.

### Step 1 — Create Azure AI Search service

```bash
az search service create \
  --name vyalaarchon-search \
  --resource-group your-rg \
  --sku basic \
  --location eastus
```

### Step 2 — Upload knowledge sources to Blob Storage

Download these documents and upload to an Azure Blob Storage container:

| Source | URL |
|--------|-----|
| NIST FIPS 203 (ML-KEM) | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.203.pdf |
| NIST FIPS 204 (ML-DSA) | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf |
| NIST FIPS 205 (SLH-DSA) | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.205.pdf |
| NIST FIPS 206 (FN-DSA) | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.206.pdf |
| NSA CNSA 2.0 | https://media.defense.gov/2022/Sep/07/2003071836/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS_.PDF |

### Step 3 — Create Foundry IQ knowledge base

In the Azure AI Foundry Portal:
1. Navigate to your project → **Knowledge bases**
2. Create new → name it `pqc-kb`
3. Add each Blob Storage document as a knowledge source
4. Enable **agentic retrieval** and **semantic reranking**
5. Copy the MCP endpoint URL to your `.env`

### Step 4 — Create project connections

In Foundry Portal → **Connections**:
- Add a **RemoteTool** connection for the KB MCP endpoint → name: `pqc-kb-connection`
- Add a **GitHub PAT** connection → name: `github-pat-connection`

---

## Installation

```bash
git clone https://github.com/somegg90-blip/Vyala-Microsoft-agents
cd Vyala-Microsoft-agents

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Azure credentials:

```bash
cp .env.example .env
```

---

## Running

### Scan a repository

```bash
python -m vyala-archon scan https://github.com/jpadilla/pyjwt --out report.json
```

### Start the API server

```bash
python -m vyala-archon serve
# Dashboard available at http://localhost:8000
```

### Run evals

```bash
pytest tests/test_evals.py -v
# Expected: 29 passed
```

---

## Project Structure

```
vyalaarchon/
├── agent/
│   ├── orchestrator.py        # Multi-agent router — intent → sub-agent
│   ├── curator.py             # Learning Path Curator (Foundry IQ)
│   ├── study_plan.py          # Study Plan Generator (Work IQ + Fabric IQ)
│   ├── manager_insights.py    # Manager Insights (Fabric IQ semantic layer)
│   ├── archon_agent.py        # Assessment Agent — 8-step pipeline core
│   ├── archon_agent_v2.py     # Enhanced scanner (GitHub + GitLab + local)
│   ├── qass.py                # Quantum Attack Surface Simulator
│   └── quantum_visualizer.py  # SVG circuit diagram generator
├── data/
│   ├── work_signals.json       # Synthetic Work IQ signals (per engineer)
│   ├── learner_performance.json # Synthetic learner performance data
│   └── team_data.json          # Synthetic team + Fabric IQ seed data
├── tests/
│   ├── conftest.py             # Azure mock + env setup
│   └── test_evals.py           # 29 eval tests across all agents
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Evaluation Results

```
29 passed in 0.37s

TestQASS                    9/9   ✓  Beauregard formula, Grover iterations, urgency multipliers
TestConfidenceGate          4/4   ✓  Refuse below 0.70, approve above, boundary, audit log
TestStudyPlan               6/6   ✓  Work IQ hour caps, milestones, Fabric IQ note
TestManagerInsights         6/6   ✓  Score bounds, actions, Fabric IQ note, 2030 risk
TestASTClassifier           4/4   ✓  RSA detect, comment FP suppression, import pre-filter
```

---

## Responsible AI

- **Confidence Gate**: refuses to output any recommendation with IQ retrieval confidence < 0.70. If the knowledge base can't ground a recommendation in NIST sources, the system explicitly refuses rather than hallucinating.
- **Audit trail**: every agent decision is logged with timestamp, confidence score, citations, and status.
- **Synthetic data only**: all demo data uses fabricated identifiers (EMP-001, TEAM-A). No real PII, no real credentials.
- **Human review flags**: low-confidence items are explicitly marked `NEEDS_HUMAN_REVIEW` and excluded from automated remediation.

---

## Security

- Never commit `.env` — it is in `.gitignore`
- Use `DefaultAzureCredential` (managed identity in production)
- No API keys in source code
- Public GitHub repositories only for scanning

---

## References

- Beauregard, S. (2003). Circuit for Shor's algorithm using 2n+3 qubits.
- Gidney, C. & Ekerå, M. (2025). How to factor 2048-bit RSA integers with less than a million noisy qubits.
- Iceberg Quantum (2026). Pinnacle Architecture — RSA-2048 factoring with QLDPC codes. arXiv:2602.11457
- NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard
- NIST FIPS 204: Module-Lattice-Based Digital Signature Standard
- NIST FIPS 205: Stateless Hash-Based Digital Signature Standard
- NSA CNSA 2.0 (2022): Commercial National Security Algorithm Suite 2.0

---

## License

MIT License — see LICENSE file.

> **Synthetic data notice**: All demo data in `/data/` uses fabricated identifiers and is for demonstration purposes only. No real employee data, customer data, or PII is included anywhere in this repository.