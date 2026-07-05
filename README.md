# 🕸️ RingTrace — Graph-Based UPI Fraud Ring Detector

**Submitted to HACKHAZARDS '26 by NAMESPACE — Neo4j Track**

Most fraud detection looks at transactions one at a time. RingTrace models UPI
transactions as a **graph** and finds *fraud rings* — not just individual
flagged payments:

- 🔁 **Cyclic laundering rings** — money that loops through 4-6 accounts and
  returns to the sender
- 📤 **Fan-out mule clusters** — one account rapidly paying many brand-new,
  never-used accounts
- 🔗 **Shared-device clusters** — accounts that look unrelated but secretly
  share a device ID or phone number, revealing a single operator behind
  multiple "different" identities

An LLM agent then explains *why* each pattern was flagged, in plain English
or Hindi — so a bank analyst (or a judge) doesn't need to read raw Cypher
output to understand the risk.

> ⚠️ **Honesty note:** the dataset used in this demo is synthetically
> generated (see `data/generate_data.py`) with deliberately planted fraud
> patterns, since real UPI transaction data isn't publicly available. The
> detection architecture — Cypher queries + graph traversal — is built to
> run against real transaction feeds in production without modification.

## 🏗️ Architecture

```
Synthetic transaction data (or real feed in production)
        ↓
   Neo4j AuraDB — accounts as nodes, transactions as PAID relationships
        ↓
   Detection layer (agents/detection.py)
   ├── Cycle detection (variable-length path query)
   ├── Fan-out detection (new-account payment burst)
   └── Shared-device/phone clustering
        ↓
   Explainer Agent (agents/explainer.py) — Groq Llama 3.3 70B
   translates raw graph findings into plain-language risk explanations
        ↓
   Streamlit UI — network graph visualization + analyst explanation
```

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Graph Database | Neo4j AuraDB (free tier) |
| Detection Logic | Cypher — cycle detection, fan-out, clustering |
| LLM Explainer | Groq API — Llama 3.3 70B |
| Frontend | Streamlit + streamlit-agraph |
| Data | Synthetic generator with planted fraud patterns |

## 🚀 Setup & Run

### 1. Create a free Neo4j AuraDB instance
Go to [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/aura-free/), create
an instance, and save the connection URI + password it gives you.

### 2. Clone and install
```bash
git clone <your-repo-url>
cd ringtrace
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your Neo4j AuraDB and Groq API credentials
```
Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 4. Generate synthetic data + load into Neo4j
```bash
python data/generate_data.py
python data/load_to_neo4j.py
```

### 5. Run the app
```bash
streamlit run ui/app.py
```

## 📁 Project Structure
```
ringtrace/
├── data/
│   ├── generate_data.py      # synthetic account/transaction generator
│   ├── load_to_neo4j.py      # loads CSVs into AuraDB
│   ├── accounts.csv          # generated
│   └── transactions.csv      # generated
├── agents/
│   ├── detection.py          # Cypher fraud-detection queries
│   └── explainer.py          # LLM explanation agent
├── ui/
│   └── app.py                # Streamlit interface
├── requirements.txt
├── .env.example
└── README.md
```

## 🎯 Why Graphs for Fraud Detection

Fraud rings are, by definition, a *relationship* problem — a single flagged
transaction rarely tells you anything, but the pattern of how money moves
between accounts reveals rings that relational databases and row-by-row
scoring models miss entirely. This is why graph databases are the standard
tool real fraud teams reach for once they move past simple rule-based
flagging.

## 👤 Builder
**Manisha Baloda** — B.Tech CSE (AI/ML), Lovely Professional University
GitHub: [@manishabaloda4-cloud](https://github.com/manishabaloda4-cloud)

## 📄 License
MIT License
