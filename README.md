# 🧠 Multi-Modal RAG Chatbot with OCR

A production-ready Retrieval-Augmented Generation (RAG) chatbot featuring **multi-modal PDF ingestion** (text, tables, figures, OCR), **table-aware retrieval**, and **local LLM inference**. Built with **FastAPI**, **Ollama Mistral-7B**, **ChromaDB**, and a **React + Tailwind CSS** frontend.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3.1-61dafb.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---
<img width="1666" height="635" alt="image" src="https://github.com/user-attachments/assets/1b39fe00-6b2d-4e13-8091-fc4114a3c55f" />


## 🎯 Key Features

### 📄 Multi-Modal PDF Processing
- **Text Extraction**: Narrative content with footnote detection
- **Table Extraction**: Row-wise format preserving headers and units (Camelot lattice)
- **Figure Detection**: Automatic caption extraction from images
- **OCR Support**: Tesseract OCR for scanned pages and non-extractable content
- **Modular Architecture**: Separate extractors for each modality

### 🔍 Advanced Retrieval
- **Table Label Locking**: Filters to specific tables when explicitly mentioned (e.g., "Table 1")
- **Scenario Table Rejection**: Excludes multiplier/simulation tables for baseline queries
- **Modality-Aware Reranking**: 15x boost for table chunks on data queries
- **Hybrid Search**: Combines vector similarity with metadata filtering

### 🤖 Local LLM Integration
- **Ollama Mistral-7B**: CPU-optimized inference (num_gpu=0)
- **Faithful Generation**: Enforces exact numeric copying from tables
- **Empty Result Handling**: Returns "Table X not found" messages
- **ChatGPT-Style Citations**: Clickable 🔗 markers with source tooltips

### 💾 Vector Database
- **ChromaDB**: Persistent storage with 384-dimensional embeddings
- **Sentence Transformers**: all-MiniLM-L6-v2 model
- **Modality Prefixes**: [TABLE], [FIGURE], [OCR] tags for enhanced retrieval

---

## 📂 Project Structure

```
RAG_OCR_CHATBOT/
├── server/                          # Backend (FastAPI)
│   ├── ingestion/                   # Modular PDF extraction package
│   │   ├── __init__.py              # MultiModalParser orchestrator
│   │   ├── pdf_text.py              # Text extraction (unstructured + pdfplumber)
│   │   ├── pdf_tables.py            # Table extraction (Camelot lattice)
│   │   └── pdf_images.py            # OCR extraction (Tesseract + Poppler)
│   ├── chroma_db/                   # ChromaDB persistent storage
│   ├── uploads/                     # Uploaded PDF files
│   ├── app.py                       # FastAPI entry point & endpoints
│   ├── models.py                    # Pydantic schemas (DocumentElement, Citation)
│   ├── embeddings.py                # SentenceTransformer + ModalityReranker
│   ├── vector_store.py              # ChromaDB wrapper
│   ├── retrieval.py                 # Hybrid retrieval + table label locking
│   ├── generation.py                # Ollama LLM generation + citations
│   ├── evaluation.py                # Metrics (not yet implemented)
│   └── requirements.txt             # Python dependencies
│
├── web/                             # Frontend (React + Vite + Tailwind)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.jsx             # Chat interface with citations
│   │   │   └── Upload.jsx           # PDF upload component
│   │   ├── App.jsx                  # Root component
│   │   ├── main.jsx                 # React entry point
│   │   └── index.css                # Global styles
│   ├── package.json                 # Node.js dependencies
│   ├── vite.config.js               # Vite configuration
│   └── tailwind.config.js           # Tailwind CSS config
│
├── poppler/                         # Poppler 23.11.0 (pdf2image dependency)
├── .venv/                           # Python virtual environment
├── .gitignore                       # Git exclusions
└── README.md                        # This file
```

---

## 📦 Installation

### Prerequisites

- **Python 3.12+**
- **Node.js 18+** (for frontend)
- **Ollama** (for local LLM inference)
- **Tesseract OCR** (for scanned content)
- **Poppler** (for PDF to image conversion)

### 1️⃣ Clone Repository

```bash
git clone https://github.com/Tusharedith/RAG_OCR_CHATBOT.git
cd RAG_OCR_CHATBOT
```

---

### 2️⃣ Backend Setup (FastAPI + Python)

#### Install Ollama & Mistral Model
```bash
# Download from https://ollama.ai/download
ollama pull mistral:latest
ollama serve  # Runs at http://localhost:11434
```

#### Install Tesseract OCR
**Windows**: Download installer from [GitHub Releases](https://github.com/UB-Mannheim/tesseract/wiki)
```powershell
# Install silently to default location
tesseract-setup.exe /S
```

**Linux/macOS**:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS (Homebrew)
brew install tesseract
```

#### Install Poppler
**Windows**: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
```powershell
# Extract to D:\RAG_OCR_CHATBOT\poppler\poppler-23.11.0\Library\bin
# Or update path in ingestion/pdf_images.py line 34
```

**Linux/macOS**:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS (Homebrew)
brew install poppler
```

#### Setup Python Environment
```bash
cd server
python -m venv ../.venv

# Windows
..\.venv\Scripts\activate

# macOS/Linux
source ../.venv/bin/activate

pip install -r requirements.txt
```

#### Run Backend Server
```bash
# From server/ directory with activated venv
python app.py
# Or
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at: **http://0.0.0.0:8000**

---

### 3️⃣ Frontend Setup (React + Vite)

```bash
cd web
npm install
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 🚀 Usage

### Upload PDF Document
1. Open **http://localhost:5173** in browser
2. Click **Upload** button and select PDF file
3. Backend processes document (text → tables → images/OCR)
4. System creates modality-tagged chunks and stores embeddings

### Query the Chatbot
**Example queries:**
- *"According to Table 1, what is the real GDP growth projection for 2024?"*
- *"Summarize the main findings from Figure 3"*
- *"What does the report say about inflation trends?"*

**Table Label Locking**: When you explicitly mention "Table X", the system:
1. Extracts table number from query
2. Filters retrieved chunks to ONLY that table
3. Rejects scenario/multiplier tables for baseline questions
4. Returns "Table X not found" if table doesn't exist

### API Endpoints

#### Upload Document
```bash
curl -X POST http://0.0.0.0:8000/upload \
  -F "file=@economic_report.pdf"
```

**Response:**
```json
{
  "message": "Document uploaded successfully",
  "chunks": 127,
  "modalities": {
    "TEXT": 89,
    "TABLE": 24,
    "FIGURE": 11,
    "IMAGE_OCR": 3
  }
}
```

#### Query Chatbot
```bash
curl -X POST http://0.0.0.0:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the GDP projection for 2025?"
  }'
```

**Response:**
```json
{
  "answer": "According to Table 1, the real GDP growth projection for 2025 is 2.7%.",
  "citations": [
    {
      "id": "cite_1",
      "label": "Table 1",
      "page": 12,
      "modality": "TABLE",
      "excerpt": "Real GDP growth (%): 2025: 2.7"
    }
  ]
}
```

---

## 🏗️ Architecture

### Ingestion Pipeline

```
PDF Upload → MultiModalParser
  ├─→ TextExtractor (unstructured.io + pdfplumber)
  │    └─→ Filters figure captions, detects footnotes
  ├─→ TableExtractor (Camelot lattice)
  │    └─→ Row-wise format: "Real GDP (%): 2023: 1.2 | 2024: 2.0"
  └─→ ImageExtractor (Tesseract + Poppler)
       └─→ Creates IMAGE_OCR chunks for scanned pages

→ ModalityAwareChunker
   ├─→ Text: Sliding window (500 chars, 100 overlap)
   └─→ Table/Figure/OCR: Atomic chunks (no splitting)

→ EmbeddingManager
   └─→ Adds modality prefixes: [TABLE], [FIGURE], [OCR]

→ ChromaDB Storage (384-dim vectors)
```

### Retrieval Pipeline

```
User Query → EmbeddingManager
  └─→ Encodes query with semantic search

→ Table Reference Detection
   ├─→ Regex: "table (\d+|[ivxlcdm]+)"
   └─→ If found: Filter to specific table chunks only

→ Vector Search (ChromaDB)
   └─→ Retrieves top-k candidates (k=5)

→ ModalityReranker
   ├─→ Table query? → 15x boost for TABLE chunks
   └─→ Scenario table? → Reject if query is baseline

→ Context Assembly (top 3 chunks)
```

### Generation Pipeline

```
Retrieved Context → Ollama Mistral-7B
  ├─→ Temperature: 0.1 (low hallucination)
  ├─→ CPU mode: num_gpu=0, num_thread=4
  └─→ Prompt: "CRITICAL - Copy table values EXACTLY"

→ Answer + Citation Extraction
   ├─→ Parse sources from context
   ├─→ Create clickable 🔗 markers
   └─→ Return JSON with citations array

→ Frontend Rendering
   └─→ Tooltips show excerpt on hover
```

---

## 🛠 Tech Stack

### Backend
- **FastAPI** 0.109.0 - Modern async web framework
- **Ollama** - Local LLM inference (Mistral-7B)
- **ChromaDB** 0.4.22 - Vector database
- **SentenceTransformers** 2.3.1 - Embeddings (all-MiniLM-L6-v2)
- **unstructured** 0.12.4 - PDF text extraction
- **pdfplumber** 0.10.3 - Fallback PDF parsing
- **Camelot-py** 0.11.0 - Table extraction (lattice)
- **pytesseract** 0.3.10 - OCR engine
- **pdf2image** 1.17.0 - PDF to image conversion
- **Pydantic** 2.5.3 - Data validation
- **pydantic-ai** 0.0.13 - AI model integration
- **LangChain** 0.1.4 - LLM orchestration framework
- **Anthropic** 0.18.1 - Claude API support

### Frontend
- **React** 18.3.1 - UI framework
- **Vite** 6.0.5 - Build tool
- **Tailwind CSS** 3.4.17 - Styling
- **Axios** 1.7.9 - HTTP client

### External Tools
- **Tesseract OCR** 5.3.3 - OCR engine
- **Poppler** 23.11.0 - PDF rendering

---

## ⚙️ Configuration

### Ollama Settings ([generation.py](server/generation.py#L16-L21))
```python
{
    "temperature": 0.1,       # Low hallucination
    "num_gpu": 0,             # CPU-only (set to 1 for GPU)
    "num_thread": 4,          # CPU threads
    "num_predict": 800        # Max tokens
}
```

### Embedding Model ([embeddings.py](server/embeddings.py#L11))
```python
model_name = "sentence-transformers/all-MiniLM-L6-v2"
dimensions = 384
```

### Retrieval Parameters ([retrieval.py](server/retrieval.py#L21-L23))
```python
vector_k = 5                  # Initial candidates
rerank_top_n = 3              # Final context chunks
table_boost_factor = 15.0     # Table query multiplier
```

### Chunking Strategy ([ingestion/__init__.py](server/ingestion/__init__.py#L104-L109))
```python
text_chunk_size = 500         # Characters
overlap = 100                 # Overlap between chunks
atomic_chunking = True        # Tables/figures not split
```

### Tesseract Path ([ingestion/pdf_images.py](server/ingestion/pdf_images.py#L33))
```python
pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Poppler Path ([ingestion/pdf_images.py](server/ingestion/pdf_images.py#L34))
```python
poppler_path = r"D:\Rag_Chatbot-main\poppler\poppler-23.11.0\Library\bin"
```

---

## 🧪 Testing

### Test Table Query
```bash
curl -X POST http://0.0.0.0:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "According to Table 1, what is the inflation rate for 2024?"
  }'
```

**Expected behavior:**
1. System detects "Table 1" reference
2. Filters chunks where section contains "table 1"
3. Rejects scenario tables (multiplier/simulation keywords)
4. Returns answer ONLY from Table 1 or "Table 1 not found"

### Test OCR Content
Upload a scanned PDF and verify IMAGE_OCR chunks are created:
```bash
# Check ChromaDB for IMAGE_OCR modality
curl http://0.0.0.0:8000/debug/chunks | grep IMAGE_OCR
```

---

## 📊 Performance

- **Embedding Speed**: ~50 chunks/second (CPU)
- **Retrieval Latency**: ~200ms for 1000 chunks
- **Generation Time**: 3-5 seconds (Mistral-7B CPU)
- **Memory Usage**: ~4GB RAM (with model loaded)
- **Chunk Limit**: Tested with 10,000+ chunks

---

## 🐛 Troubleshooting

### Ollama Connection Error
```bash
# Check if Ollama is running
ollama list
ollama serve

# Test model
ollama run mistral:latest "Hello"
```

### Tesseract Not Found
```python
# Update path in server/ingestion/pdf_images.py
pytesseract.tesseract_cmd = r"YOUR_TESSERACT_PATH"
```

### Poppler Not Found
```python
# Update path in server/ingestion/pdf_images.py
poppler_path = r"YOUR_POPPLER_PATH\bin"
```

### ChromaDB Persistence Issues
```bash
# Clear database
rm -rf server/chroma_db/*
# Restart backend to reinitialize
```

### CORS Errors
Check [app.py](server/app.py#L18-L23) allows frontend origin:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🔒 Security Notes

- **Local Inference**: No API keys, all processing local
- **File Upload**: Only PDF files allowed (MIME type check)
- **Path Traversal**: Upload directory is isolated
- **SQL Injection**: Not applicable (ChromaDB is embedded)
- **XSS Protection**: React auto-escapes user input

---

## 🚧 Known Limitations

1. **Handwritten Text**: OCR accuracy depends on scan quality
2. **Complex Tables**: Nested/merged cells may not parse correctly
3. **Multi-Column PDFs**: Layout detection can struggle
4. **Large Files**: >50MB PDFs may timeout (adjust in production)
5. **CPU Inference**: Generation is slower than GPU (3-5s vs <1s)

---

## 🗺️ Roadmap

- [x] Modular ingestion package (text, tables, images)
- [x] Pydantic-AI integration for enhanced model handling
- [x] LangChain integration for LLM orchestration
- [x] Evaluation module foundation (evaluation.py)
- [ ] GPU acceleration for Ollama
- [ ] Multi-document querying
- [ ] Conversational memory (chat history)
- [ ] Advanced table parsing (merged cells)
- [ ] Complete evaluation metrics (RAGAS framework)
- [ ] Streaming responses (SSE)
- [ ] Docker containerization
- [ ] Production deployment guide

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Open Pull Request

**Development Guidelines:**
- Follow PEP 8 for Python code
- Use ESLint config for JavaScript
- Add docstrings to new functions
- Test table queries before submitting
- Update README if adding features

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Tushar Edith**
- GitHub: [@Tusharedith](https://github.com/Tusharedith)
- Repository: [RAG_OCR_CHATBOT](https://github.com/Tusharedith/RAG_OCR_CHATBOT)

---

## 🙏 Acknowledgments

- **Ollama Team** - Local LLM inference
- **LangChain Community** - RAG inspiration
- **unstructured.io** - PDF parsing library
- **ChromaDB Team** - Vector database
- **Mistral AI** - Open-source LLM

---

## 📞 Support

For issues or questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Search [GitHub Issues](https://github.com/Tusharedith/RAG_OCR_CHATBOT/issues)
3. Open new issue with reproduction steps

---

**⭐ Star this repo if you find it useful!**
