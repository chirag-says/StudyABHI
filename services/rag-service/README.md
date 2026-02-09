# RAG Service

Retrieval Augmented Generation service for intelligent Q&A using vector embeddings.

## Purpose

This service enables:
- Document ingestion and vectorization
- Semantic search over study materials
- AI-powered question answering
- Context-aware responses using LangChain

## Tech Stack

- FastAPI for API
- LangChain for RAG pipeline
- Qdrant for vector storage
- OpenAI/Ollama for LLM

## Structure

```
rag-service/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Configuration
│   ├── services/         # Business logic
│   │   ├── embeddings.py # Document embedding
│   │   ├── retriever.py  # Vector search
│   │   └── generator.py  # Response generation
│   └── main.py           # Application entry
├── Dockerfile
└── requirements.txt
```

## API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ingest` | Ingest documents |
| POST | `/query` | Ask a question |
| GET | `/documents` | List documents |
| DELETE | `/documents/:id` | Delete document |

## Development

```bash
# TODO: Implement RAG service
```
