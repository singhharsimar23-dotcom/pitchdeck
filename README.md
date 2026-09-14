# 🧠 Grounded Pitch — AI-Native Startup Pressure Tester

<div align="center">

![Gemini](https://img.shields.io/badge/Powered%20By-Gemini%202.5%20Flash-blue?style=for-the-badge&logo=google&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![GCP](https://img.shields.io/badge/Google%20Cloud-Deployed-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**The world''s most rigorous AI system for pressure-testing startup pitches.**
Not a slide maker. A verification engine that happens to produce world-class decks.

</div>

---

## ⚡ What Is This?

Most AI pitch tools make your story *look* good. **Grounded Pitch makes it *true*.**

This system runs your startup concept through a **12-stage adversarial pipeline** backed by real-time data from SEC EDGAR, USPTO PatentsView, GitHub, and Bayesian arithmetic engines — then builds a deck where every single claim is grounded, evidence-weighted, and confidence-scored.

> **Think of it as:** A YC partner, a hedge fund analyst, and a forensic accountant reviewing your deck simultaneously — in ~6 seconds.

---

## 🎯 Core Philosophy

> *"A claim without evidence is fiction. A deck without grounding is theater."*

This is **not** a GPT wrapper that rewrites your bullet points into fancier language. Every slide goes through:

1. **Injection Defense** — Blocks prompt manipulation before a single token of your real deck is generated
2. **Business Model Classification** — Detects SaaS, marketplace, deep-tech, consumer models and applies model-specific logic
3. **Bottom-Up Math Engine** — Bayesian arithmetic for TAM/SAM/SOM. If your $50B claim doesn't survive unit-economics math, it gets flagged
4. **System-of-Record Verification** — Live queries to SEC EDGAR, USPTO, GitHub
5. **Evidence Graph** — Every claim scored on a 0-1 confidence scale using multi-tier evidence chains
6. **Living Deck** — Edit any slide in natural language; dependent slides auto-recalculate for mathematical consistency

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GROUNDED PITCH SYSTEM                    │
├──────────────┬──────────────────────┬─────────────────────┤
│  STAGE 0     │  STAGE 1-3           │  STAGE 4-8          │
│  Injection   │  Intake + Business   │  SoR Verification   │
│  Screening   │  Model Detection +   │  · SEC EDGAR 10-K   │
│              │  Bottom-Up Math      │  · USPTO Patents    │
│              │                      │  · GitHub Velocity  │
├──────────────┴──────────────────────┴─────────────────────┤
│  STAGE 9-12: Slide Assembly + Evidence Graph + Living Deck  │
│  Dependency-Aware Conversational Editing with Re-grounding  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **AI Model** | Gemini 2.5 Flash (Google Vertex AI) |
| **Backend** | FastAPI + Python 3.10 |
| **Frontend** | Vanilla JS + CSS (Zero framework dependencies) |
| **Streaming** | Server-Sent Events — sub-150ms time-to-first-slide |
| **Storage** | Firestore (pitchdeck DB) + localStorage fallback |
| **SoR Data** | SEC EDGAR, USPTO PatentsView, GitHub API |
| **Deployment** | Google Cloud Run (serverless, auto-scaling) |

---

## ✨ Features

### 🔬 Pressure Testing Engine
- **Adversarial Questionnaire** — 5-8 targeted intake questions calibrated to the specific business model
- **Business Model Classifier** — SaaS, marketplace, deep-tech, consumer with model-specific logic
- **Bottom-Up Math Validation** — Rejects unsupported TAM claims; builds math from unit economics up
- **Injection Defense** — Blocks prompt manipulation attempts before execution

### 📊 System-of-Record Integrations
- **SEC EDGAR Full-Text Search** — Real competitor 10-K filings for ACV and margin benchmarks
- **USPTO PatentsView** — Validates IP moat claims against live patent grant data
- **GitHub Velocity** — Measures engineering traction for deep-tech claims
- **Stripe Connect** — Optional revenue verification for traction claims

### 🎨 The Gamma-Grade Studio Experience
- **3-Stage Generation Flow**: Intake → Outline → Streaming Deck Assembly
- **Gamma-style Side Edit Panel** — Click any slide → chat to edit → AI recalculates dependencies
- **Living Dock** — Always-present bottom bar for global deck edits
- **Fullscreen Present Mode** — Keynote-quality presentation with thumbnail strip
- **Evidence View** — Per-claim confidence rings and source provenance
- **Telemetry View** — Live stage latency, token usage, and pipeline trace

### 🔄 The Living Deck
- **Dependency Mapper** — Revenue changes → gross margin slides auto-update
- **Confidence Arithmetic** — Evidence-weighted composite scores per claim (0–100%)
- **Grounding Re-verification** — Edits that touch factual claims trigger live SoR re-checks
- **History Persistence** — Firestore + localStorage dual-layer session history

---

## 🚀 Quickstart

### Prerequisites
- Python 3.10+
- Google Cloud account with Vertex AI enabled
- `gcloud` CLI authenticated

### Local Setup

```bash
# Clone the repo
git clone https://github.com/singhharsimar23-dotcom/pitchdeck.git
cd pitchdeck

# Install dependencies
pip install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Run locally
python main.py
```

Open `http://localhost:8080` — the full studio loads.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | Required |
| `PORT` | Server port | `8080` |

---

## 🐳 Self-Hosting

### Google Cloud Run (Recommended)

```bash
# Build and deploy in one command
gcloud run deploy pitchdeck \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300
```

### Docker

```bash
docker build -t pitchdeck .
docker run -p 8080:8080 -e GOOGLE_CLOUD_PROJECT=your-project pitchdeck
```

---

## 🧪 Adversarial Test Presets

6 built-in red-team scenarios to validate the engine:

| Preset | Tests For |
|--------|-----------|
| **Deliberately Thin Input** | Multiple `INSUFFICIENT_INPUT` verdicts |
| **Fake $50B Market Claim** | Bottom-up math contradicts top-down; score < 50 |
| **Obscure Fictional Category** | All SoR returns `insufficient_data` — zero hallucination |
| **Deep-Tech + GitHub + SEC** | USPTO, GitHub velocity, EDGAR all triggered |
| **Prompt Injection Attack** | Hard block at Stage 0; no slides generated |
| **Two-Sided Marketplace** | GMV/take-rate math; liquidity risk flagged |

---

## 📁 Project Structure

```
pitchdeck/
├── main.py                 # FastAPI app — all API endpoints
├── pipeline.py             # 12-stage adversarial pipeline (core engine)
├── agents.py               # Structured agent callers
├── sor_integrations.py     # SEC EDGAR, USPTO, GitHub adapters
├── cost_config.py          # Token + cost tracking
├── eval_harness.py         # Automated evaluation harness
├── stripe_connect.py       # Stripe Connect OAuth integration
├── deploy_cloudrun.py      # Cloud Run deployment helper
├── Dockerfile              # Production container
├── requirements.txt
└── static/
    ├── index.html          # SPA shell (1,400+ lines)
    ├── app.js              # Frontend state machine (2,900+ lines)
    └── styles.css          # Design system (5,000+ lines)
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/intake` | Injection screen + intake questions |
| `POST` | `/api/outline` | Generate outline from concept + QA |
| `POST` | `/api/magic-stream` | **SSE** — full pipeline with live events |
| `POST` | `/api/edit` | Natural language edit with dependency recalculation |
| `POST` | `/api/sor/check` | On-demand SoR live diagnostic |
| `GET`  | `/api/presets` | Get adversarial presets |
| `POST` | `/api/history/save` | Save deck to Firestore |
| `GET`  | `/api/history/list` | List past sessions |
| `GET`  | `/api/history/{id}` | Load specific deck |

---

## 🧠 The Evidence Graph

Every claim is scored via Bayesian evidence weighting:

```
Evidence Tiers (weight):
  audited_filing      → 1.00  (SEC 10-K, audited financials)
  independent_study   → 0.85  (peer-reviewed, CB Insights)
  crowd_corroboration → 0.70  (multiple independent sources)
  single_platform     → 0.55  (single source)
  founder_stated      → 0.40  (unverified founder claim)
  model_estimate      → 0.25  (AI-generated estimate)
```

Multi-source corroboration adds independence bonuses stacking up to +15%.

---

## 🛡️ Anti-Hallucination Guarantees

Hard rules enforced at the prompt level — cannot be overridden:

- ❌ **No invented numbers** — Every metric traces to a SoR query or founder input
- ❌ **No fabricated competitors** — Competitor data comes from SEC EDGAR or is labeled `FOUNDER_STATED`
- ❌ **No unsupported market sizes** — TAM must survive bottom-up arithmetic
- ❌ **No passive hedging** — "Could potentially" and "might possibly" are blocked
- ✅ **Explicit refusals** — Insufficient evidence → slide says so rather than inventing content

---

## 🤝 Contributing

Pull requests welcome. Run the eval harness before submitting:

```bash
python eval_harness.py
```

---

## 📄 License

MIT

---

<div align="center">

**Built with Gemini 2.5 Flash · Grounded on real data · Zero hallucination tolerance**

*"The best pitch is the one that survives the hardest questions."*

</div>
