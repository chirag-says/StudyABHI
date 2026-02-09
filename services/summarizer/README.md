# Summarizer Service

Content summarization service for notes and articles.

## Purpose

This service enables:
- Text summarization (extractive & abstractive)
- Key points extraction
- Topic categorization
- Notes generation from documents

## Tech Stack

- FastAPI for API
- Hugging Face Transformers for summarization
- OpenAI for advanced summarization
- Redis for caching

## Structure

```
summarizer/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Configuration
│   ├── services/         # Business logic
│   │   ├── summarizer.py # Summarization logic
│   │   ├── extractor.py  # Key points extraction
│   │   └── categorizer.py # Topic categorization
│   └── main.py           # Application entry
├── Dockerfile
└── requirements.txt
```

## API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/summarize` | Summarize text |
| POST | `/summarize-url` | Summarize from URL |
| POST | `/extract-keypoints` | Extract key points |
| POST | `/categorize` | Categorize content |

## Development

```bash
# TODO: Implement Summarizer service
```
