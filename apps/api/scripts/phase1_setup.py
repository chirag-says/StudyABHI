"""
Phase 1 Setup — deletes old DBs, creates vector directory, verifies imports.
Run: python scripts/phase1_setup.py
"""
import os
import sys
from pathlib import Path

# Set working dir to apps/api
script_dir = Path(__file__).parent
api_dir = script_dir.parent
os.chdir(api_dir)
sys.path.insert(0, str(api_dir))

print("=== Phase 1 Setup ===\n")

# 1. Delete old databases
for db in ["upsc.db", "upsc_dev.db", "database.db"]:
    p = Path(db)
    if p.exists():
        p.unlink()
        print(f"  ✓ Deleted {db}")
    else:
        print(f"  - {db} not found (already clean)")

# 2. Create data/vectors directory
vectors_dir = Path("data/vectors")
vectors_dir.mkdir(parents=True, exist_ok=True)
print(f"\n  ✓ Created {vectors_dir}/")

# 3. Verify critical imports
print("\n=== Import Check ===")

try:
    from app.core.config import settings
    print(f"  ✓ config loaded: APP_NAME={settings.APP_NAME}")
    print(f"  ✓ NVIDIA_EMBED_MODEL={settings.NVIDIA_EMBED_MODEL}")
    print(f"  ✓ NVIDIA_EMBED_DIM={settings.NVIDIA_EMBED_DIM}")
    print(f"  ✓ VECTOR_STORAGE_PATH={settings.VECTOR_STORAGE_PATH}")
    print(f"  ✓ LLM_PROVIDER={settings.LLM_PROVIDER}")
    api_key_set = bool(settings.NVIDIA_API_KEY)
    print(f"  ✓ NVIDIA_API_KEY={'SET ✓' if api_key_set else 'NOT SET ✗'}")
except Exception as e:
    print(f"  ✗ Config error: {e}")
    sys.exit(1)

try:
    import faiss
    print(f"\n  ✓ faiss-cpu available")
except ImportError:
    print(f"\n  ✗ faiss-cpu not installed — run: pip install faiss-cpu")

try:
    import numpy
    print(f"  ✓ numpy available ({numpy.__version__})")
except ImportError:
    print(f"  ✗ numpy not installed")

try:
    import httpx
    print(f"  ✓ httpx available (used for NVIDIA API calls)")
except ImportError:
    print(f"  ✗ httpx not installed")

try:
    from app.services.rag.embeddings import EmbeddingPipeline, NvidiaEmbeddingModel
    print(f"  ✓ EmbeddingPipeline import OK (uses NvidiaEmbeddingModel)")
except Exception as e:
    print(f"  ✗ EmbeddingPipeline import failed: {e}")

try:
    from app.services.rag.pipeline import NvidiaKimiClient, create_rag_pipeline
    print(f"  ✓ NvidiaKimiClient import OK")
except Exception as e:
    print(f"  ✗ NvidiaKimiClient import failed: {e}")

try:
    from app.core.dependencies import get_current_user, get_embedding_pipeline
    print(f"  ✓ dependencies import OK (get_embedding_pipeline available)")
except Exception as e:
    print(f"  ✗ dependencies import failed: {e}")

print("\n=== Setup Complete ===")
print("Next: Run the server with:")
print("  uvicorn app.main:app --reload --port 8000")
