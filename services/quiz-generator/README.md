# Quiz Generator Service

AI-powered quiz generation from study materials.

## Purpose

This service enables:
- Automatic quiz generation from text/documents
- Multiple question types (MCQ, True/False, Fill-in-blank)
- Difficulty adaptation based on performance
- Spaced repetition scheduling

## Tech Stack

- FastAPI for API
- OpenAI/Ollama for question generation
- PostgreSQL for quiz storage
- Redis for caching

## Structure

```
quiz-generator/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Configuration
│   ├── models/           # Quiz models
│   ├── services/         # Business logic
│   │   ├── generator.py  # Quiz generation
│   │   ├── evaluator.py  # Answer evaluation
│   │   └── scheduler.py  # Spaced repetition
│   └── main.py           # Application entry
├── Dockerfile
└── requirements.txt
```

## API Endpoints (Planned)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate` | Generate quiz from text |
| POST | `/generate-from-topic` | Generate quiz from topic |
| POST | `/evaluate` | Evaluate quiz answers |
| GET | `/quizzes` | List generated quizzes |
| GET | `/quiz/:id` | Get quiz by ID |

## Development

```bash
# TODO: Implement Quiz Generator service
```
