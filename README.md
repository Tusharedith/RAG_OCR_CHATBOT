# 🧠 RAG Chatbot

A Retrieval-Augmented Generation (RAG) powered chatbot built with **Python (Flask backend)** and a **React + Tailwind frontend**.
It allows users to query information, retrieves relevant context from a knowledge base, and generates meaningful answers.



---

## 🎟️ Demo
<img width="1902" height="957" alt="image" src="https://github.com/user-attachments/assets/5068f32e-956d-4f3f-bfa2-1a0d83b93f18" />

https://github.com/user-attachments/assets/a0743db0-a73e-480a-8cce-f23132b85488

---

## 🚦 Workflow
Our RAG chatbot follows a two-phase process: Document Ingestion where uploaded files are chunked, embedded, and stored in a vector database, followed by Chat Interaction where user queries are matched against stored embeddings to retrieve relevant context for LLM-powered answer generation.

<img width="1555" height="674" alt="image" src="https://github.com/user-attachments/assets/ba95dd40-7090-41e6-8823-87d0c28cfa81" />

The diagram above illustrates the complete end-to-end flow from document upload to contextual answer delivery.




## ✨ Features

* RAG pipeline for intelligent responses
* REST API (Flask backend)
* Modern UI built with React + Tailwind
* File upload support
* Easy to run locally

---

## 📂 Project Structure

```
Rag_Chatbot/
│── server/ # Backend (Flask)
│ ├── pycache/ # Python cache files
│ ├── chroma_store/ # Vector database / embeddings store
│ ├── uploads/ # Uploaded files
│ ├── .env # Environment variables
│ ├── app.py # Flask entry point
│ ├── parsers.py # Parsing logic for documents
│ ├── rag.py # Retrieval-Augmented Generation logic
│ └── requirements.txt # Backend dependencies
│
│── venv/ # Python virtual environment (ignored in git)
│
│── web/ # Frontend (React + Tailwind + Vite)
│ ├── node_modules/ # Dependencies (ignored in git)
│ ├── public/ # Public assets
│ ├── src/ # React source code
│ │ ├── assets/ # Static assets
│ │ ├── components/ # Reusable components
│ │ │ ├── Chat.jsx # Chat UI component
│ │ │ └── Upload.jsx # File upload UI component
│ │ ├── App.jsx # Root React component
│ │ ├── index.css # Global styles
│ │ └── main.jsx # React entry point
│ ├── index.html # Main HTML file
│ ├── package.json # Frontend dependencies
│ ├── vite.config.js # Vite configuration
│ └── tailwind.config.js # Tailwind configuration
│
│── .gitignore # Ignored files
│── README.md # Project documentation
```

---

## 📦 Installation

### 🔹 Backend (Flask)

1. Clone the repository:

   ```bash
   git clone https://github.com/Tusharedith/Rag_Chatbot.git
   cd Rag_Chatbot
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the server:

   ```bash
   python app.py
   ```

   Server runs at: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

### 🔹 Frontend (React + Vite)

1. Navigate to the `web/` folder:

   ```bash
   cd web
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Start development server:

   ```bash
   npm run dev
   ```

   Frontend runs at: **[http://localhost:5173](http://localhost:5173)**

---

## 🚀 Usage

Once both backend and frontend are running:

* Open the React app in browser.
* Enter your query or upload a file.
* The chatbot will retrieve relevant context and generate a response.

Example API request (PowerShell):

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:5000/chat" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{"message": "What is the capital of France?"}'
```

---

## 🛠 Tech Stack

* **Python (Flask)**
* **React (Vite + Tailwind)**
* **RAG (Retrieval-Augmented Generation)**
* **Node.js** (for frontend build tools)

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to fork this repo and submit a PR.

---

## 📜 License

This project is licensed under the MIT License.
