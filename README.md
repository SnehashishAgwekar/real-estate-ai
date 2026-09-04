# EstateAgent AI: Intelligent Real Estate Ecosystem

An advanced, multi-agent real estate platform powered by Large Language Models (LLMs) and Computer Vision. This project integrates conversational AI for property discovery with an automated visual verification engine to detect fraudulent listing configurations.

##  Key Features

* **Multi-Agent Orchestration:** Utilizes LangGraph and Gemini 3.6-Flash to route user queries intelligently across different domains (SQL databases, Vector RAG, and Live Web Search).
* **Property Room & BHK Verification:** An automated computer vision pipeline that independently verifies a seller's claimed BHK (Bedroom, Hall, Kitchen) configuration using uploaded photographs.
* **Visual Fraud Detection:** Prevents users from artificially inflating room counts by detecting duplicate angles of the same physical room using vector embeddings and cosine similarity.
* **Modern Stack:** Built on FastAPI, React, PostgreSQL, and Qdrant, orchestrated seamlessly via Docker Compose.

##  System Architecture & Tech Stack

### Frontend (Client-Side)
* **Framework:** React.js
* **Styling:** Tailwind CSS (Dark theme blueprint UI)
* **State Management:** React Hooks with local storage session caching

### Backend (Server-Side)
* **Framework:** FastAPI (Python)
* **Concurrency:** `run_in_threadpool` for non-blocking CPU-bound AI inference
* **Relational Database:** PostgreSQL (Property listings, structured data)
* **Vector Database:** Qdrant (Brochure archives, RAG)

### Artificial Intelligence & Machine Learning
* **LLM Engine:** Gemini 3.6-Flash
* **Agent Framework:** LangGraph (Node-based decision routing)
* **Web Search:** Tavily API
* **Vision Classification:** Places365 (ResNet18 architecture) via PyTorch
* **Visual Embeddings:** OpenAI CLIP (ViT-B-32) via `sentence-transformers`

---

##  Deep Dive: The BHK Verification Engine

A standout feature of this platform is the anti-fraud verification pipeline, which operates in two distinct phases:

### Phase 1: Scene Classification (Places365)
When a user uploads property photos, the backend passes each image through a pretrained **Places365 ResNet18 Convolutional Neural Network (CNN)**. The model outputs a raw scene category (e.g., `bedchamber`, `hotel_room`), which our logic maps to standardized real estate labels (e.g., `bedroom`). It returns these classifications with a Softmax confidence percentage.

### Phase 2: Visual Deduplication (CLIP)
A naive system can be tricked by uploading four photos of the exact same bedroom to claim a "4 BHK". To solve this, all images classified as bedrooms are passed through **OpenAI's CLIP (ViT-B-32)** model. 
* The model generates a dense, 512-dimensional vector embedding for each image.
* The system calculates the **Cosine Similarity** between all bedroom embeddings.
* Images with a similarity score of **≥ 0.90** are mathematically clustered as "duplicate angles of the same physical room."
* The final verdict relies exclusively on the *unique* room count, ensuring high integrity in property listings.

---

##  Local Setup & Installation

### Prerequisites
* Docker and Docker Compose
* Python 3.10+
* Node.js v18+

### 1. Infrastructure Setup
Ensure your `.env` file is configured in the root directory with the necessary API keys (`TAVILY_API_KEY`, `GOOGLE_API_KEY`).
```bash
docker-compose up -d
