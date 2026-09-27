# NEXUS — AI-Powered Adaptive Learning & Assessment Platform

Welcome to the **NEXUS** (formerly StudyHub) repository. This project is a comprehensive educational platform that helps students organize their learning, test their knowledge with AI-generated assessments, and receive personalized coaching.

## 🚀 Features

- **Subject & Material Management:** Upload study materials (PDFs, text) and organize them by subjects and topics.
- **AI-Powered Retrieval (RAG):** Ask natural language questions against your study materials and receive precise, source-grounded explanations.
- **Adaptive Assessments:** Automatically generate multiple-choice questions (MCQs) and interactive quizzes tailored to specific topics.
- **Personalized Roadmaps:** Get automated study plans and coaching recommendations based on your performance and weak spots.
- **Hybrid AI Architecture:** Intelligently routes tasks between powerful cloud models (OpenRouter) and secure local models (Ollama) to balance capability, privacy, and cost.

## 🛠️ Tech Stack

- **Frontend:** Next.js 15, React 19, Tailwind CSS, Radix UI primitives.
- **Backend:** Python, FastAPI, SQLite.
- **AI Engine:** Custom `slice` library for state persistence, multi-provider model routing, RAG chunking, and workflow state machines.

## 🚦 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm
- [Ollama](https://ollama.com/) (Required for local model execution)

### 1. Start the Backend

Start the FastAPI server from the project root:
```bash
python -m uvicorn studyhub.web.app:app --port 8100
```
Ensure your `.env` is configured with `OPENROUTER_API_KEY` for cloud reasoning features.

### 2. Start the Frontend

Navigate to the `frontend/` directory and start the Next.js development server:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3. Local AI Setup (Ollama)

NEXUS defaults to using `llama3.1` for local, cost-effective evaluation tasks. 
To ensure it runs smoothly, start Ollama and pull the required model:
```bash
ollama pull llama3.1
```



*For more details on our verification methodology, see our [Testing Report](NEXUS_Professional_Testing_Report.md).*

## 📖 Architecture & Documentation

This project utilizes an Agentic Slice architecture, showcasing autonomous API usage, state persistence, multi-step decomposition, and human-in-the-loop callbacks. 
Read more in the `docs/` folder for architectural decisions and design principles.
