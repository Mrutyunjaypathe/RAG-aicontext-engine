# 🧠 Production AI Knowledge System (RAG + Observability)

> A production-ready Retrieval-Augmented Generation (RAG) system with FastAPI backend, FAISS vector store, Google Gemini LLM, and a beautiful Web UI.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Run the Backend
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Open Web UI
Open `frontend/index.html` in your browser or serve with:
```bash
python -m http.server 3000 --directory frontend
```

---

## 📁 Project Structure

```
Ài-Final/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration management
│   ├── routers/
│   │   ├── upload.py        # /upload endpoint
│   │   ├── query.py         # /query endpoint
│   │   └── metrics.py       # /metrics endpoint
│   ├── services/
│   │   ├── ingestion.py     # Document ingestion pipeline
│   │   ├── embeddings.py    # Embedding generation
│   │   ├── retrieval.py     # FAISS retrieval
│   │   ├── llm.py           # LLM integration (Gemini/OpenAI)
│   │   └── observability.py # Logging & metrics
│   └── models/
│       ├── schemas.py       # Pydantic models
│       └── store.py         # In-memory/file metadata store
├── frontend/
│   ├── index.html           # Main web UI
│   ├── style.css            # Styling
│   └── app.js               # Frontend logic
├── data/
│   ├── uploads/             # Uploaded documents
│   ├── vectors/             # FAISS index files
│   └── logs/                # Observability logs
├── tests/
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   └── test_api.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🔑 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload PDF or TXT document |
| POST | `/query` | Ask a question over your documents |
| GET | `/metrics` | View observability metrics |
| GET | `/docs` | Interactive API documentation |

---

## 🛠️ Tech Stack

- **Backend**: FastAPI + Uvicorn
- **RAG**: LangChain + FAISS
- **LLM**: Google Gemini (free tier)
- **Embeddings**: Google Generative AI Embeddings
- **Observability**: Custom logging + JSON metrics
- **Frontend**: Vanilla HTML/CSS/JS (no frameworks)

---

## 📊 Features

- ✅ PDF & TXT document upload
- ✅ FAISS vector store with persistence
- ✅ Source citations in every response
- ✅ Latency tracking (p50, p95)
- ✅ Cost estimation per query
- ✅ Beautiful dark-mode Web UI
- ✅ Interactive API docs (Swagger)

---

*Built by Mrutyunjay Pathe*
