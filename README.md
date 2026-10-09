# Autonomous MirAI Student Policy Advisor

[![GitHub Repository](https://img.shields.io/badge/GitHub-mirai__rag-blue?logo=github)](https://github.com/v-sai-sujith/mirai_rag)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg?logo=streamlit)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-LCEL-1C3C3C.svg)](https://www.langchain.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange.svg)](https://www.trychroma.com/)

An end-to-end, production-ready Retrieval-Augmented Generation (RAG) system built to act as an autonomous student advisor for the **Mirai School of Technology Student Policy Handbook (2026)**.

---

## 1. Project Overview & Problem Statement

University administrations handle an overwhelming volume of repetitive student inquiries concerning:
- Minimum attendance thresholds and marks tiers
- Medical and duty leave documentation procedures
- Admit card eligibility and clearance policies
- Club formation rules, leadership elections, and event approvals
- Student codes of conduct and disciplinary guidelines

### The Core Challenge: Zero Hallucination
When students ask questions about policy rules, academic consequences, or disciplinary sanctions, **hallucinations or inaccurate advice are unacceptable**. Fabricating non-existent fine amounts or misquoting attendance rules could lead to academic debarment or administrative friction.

The **Autonomous MirAI Student Policy Advisor** solves this by strictly enforcing:
1. **Context Grounding**: Answers are synthesized **solely** from retrieved sections of the official policy handbook.
2. **Zero Extrapolation**: The LLM temperature is pinned to `0.0`, and base training assumptions are prohibited.
3. **Explicit Refusal & Non-Fabrication**: When a requested rule or fine does not exist in the policy, the system explicitly clarifies that no such fine or rule exists rather than fabricating details.

---

## 2. System Architecture

The application is structured into decoupled, production-grade layers:

```
┌────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                   │
│         (Interactive Chat UI & Ingestion Sidebar)      │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP REST (JSON / Multipart)
┌───────────────────────────▼────────────────────────────┐
│                   FastAPI Backend                      │
│             (/ingest, /chat, /health, /docs)           │
├────────────────────────────────────────────────────────┤
│                  LangChain LCEL Pipeline               │
│                                                        │
│  [Student Query]                                       │
│         │                                              │
│         ▼                                              │
│  [MultiQueryRetriever] ──► Query Expansion & Rewrite   │
│         │                                              │
│         ▼                                              │
│  [ChromaDB Vector Store] (GoogleGenerativeAIEmbeddings)│
│         │                                              │
│         ▼                                              │
│  [Context + Strict System Guardrails Prompt]           │
│         │                                              │
│         ▼                                              │
│  [ChatGoogleGenerativeAI (Gemini @ Temp=0.0)]          │
│         │                                              │
│         ▼                                              │
│  [Deterministic, Grounded Advice]                      │
└────────────────────────────────────────────────────────┘
```

### Key Technical Components:
- **Document Ingestion (`POST /ingest`)**: Uploaded PDFs are parsed via `PyPDFLoader` and split into semantic chunks via `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)`.
- **Vector Storage**: Chunks are embedded using `GoogleGenerativeAIEmbeddings` and stored in a persistent local `ChromaDB` instance (`./chroma_db`).
- **Multi-Query Retrieval**: Bridges the vocabulary gap between casual student language (e.g., *"got sick at Ratnam"*) and formal handbook provisions (e.g., *"Medical Leave, Duty Leave & Attendance Deviation Policy"*) by generating multiple diverse search formulations.
- **Guardrail Enforcement**: The system prompt strictly prohibits outside knowledge, ensures exact citation of thresholds and contacts, and disallows inventing fines.
- **LLM-as-a-Judge Evaluation**: `evaluate.py` benchmarks the pipeline against gold standard criteria across precision, multi-hop reasoning, procedural routing, and negative constraint compliance.

---

## 3. Repository Structure

```text
mirai_rag/
├── backend.py            # FastAPI service hosting /ingest and /chat LCEL pipeline
├── frontend.py           # Streamlit student-facing chat and administrative UI
├── evaluate.py           # Automated LLM-as-a-Judge certification audit script
├── requirements.txt      # Project Python dependencies
├── rag_eval_scores.csv   # Benchmarking audit results log (all 4 tests at 5/5)
├── data/                 # Directory containing the policy handbook PDF
│   └── Mirai_SoT_Policy_Handbook_2026.pdf
├── chroma_db/            # Local ChromaDB persistent vector database directory
├── .gitignore            # Git exclusion rules (virtualenvs, .env, caches)
└── README.md             # Standard Operating Procedures & project documentation
```

---

## 4. Local Setup Guide

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/v-sai-sujith/mirai_rag.git
cd mirai_rag
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```ini
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## 5. Execution Commands (Standard Operating Procedures)

### Step 1: Start the Backend Server (FastAPI)
Run Uvicorn from the project root:
```bash
uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```
- **API Health Check**: `http://localhost:8000/health`
- **Interactive Swagger Documentation**: `http://localhost:8000/docs`

### Step 2: Start the Frontend Application (Streamlit)
In a separate terminal window:
```bash
streamlit run frontend.py
```
- The web app will launch automatically at: `http://localhost:8501`

### Step 3: Ingest the Policy Handbook
You can index the document via either of two methods:
- **Via Streamlit UI**: In the left sidebar under *Policy Document Ingestion*, select `data/Mirai_SoT_Policy_Handbook_2026.pdf` and click **"Upload & Ingest Handbook"**.
- **Via cURL (REST API)**:
  ```bash
  curl -X POST "http://localhost:8000/ingest" \
    -H "accept: application/json" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@data/Mirai_SoT_Policy_Handbook_2026.pdf"
  ```

---

## 6. Automated Evaluation & Certification Results

To run the automated LLM-as-a-judge certification pipeline against the 4 benchmark queries:
```bash
python evaluate.py
```

The script benchmarks the live RAG pipeline and records the evaluations into `rag_eval_scores.csv`.

### Certification Audit Summary

| Test ID | Test Query | Evaluation Criteria | Score | Result |
|:---:|---|---|:---:|:---:|
| **`TEST_001`** | *"I have 72% attendance. How many attendance marks will I get?"* | Accurately identifies **4 marks** (60%–74.99% tier) and cites the 75% minimum threshold rule. | **5 / 5** |  **Passed** |
| **`TEST_002`** | *"I study at the Ratnam campus. I got sick and need medical leave. Who do I email and how many days do I have to submit my documents?"* | Multi-hop reasoning identifies **Yashaswini Ma’am** (Ratnam Campus Manager) and the **7-day** submission window. | **5 / 5** |  **Passed** |
| **`TEST_003`** | *"We want to start a new Cybersecurity society under the Tech Club. Do we ask Management directly?"* | Affirms **do not bypass faculty**, requires **40% batch support**, and routes proposal to the **Faculty Coordinator**. | **5 / 5** |  **Passed** |
| **`TEST_004`** | *"How much is the fine for smoking a cigarette on campus?"* | Negative constraint testing: identifies tobacco prohibition & Disciplinary Committee action; **strictly avoids fabricating a monetary fine**. | **5 / 5** |  **Passed** |

**Final Certification Score: 5.0 / 5.0 (100% Pass Rate)**

---

## 7. License & Credits
Developed as part of the **Autonomous MirAI Student Policy Advisor Capstone Project**. All institutional policy citations reflect the Mirai School of Technology Student Policy Handbook (2026).
