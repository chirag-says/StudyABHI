import sys
import os
import asyncio

# Ensure we can import app modules - Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.document import Document
from app.services.document_service import DocumentService
from app.services.rag.embeddings import EmbeddingPipeline

# Ensure we can import app modules
sys.path.append(os.getcwd())

async def reindex_documents():
    print("🚀 Starting re-indexing process...")
    
    # Initialize services
    db = AsyncSessionLocal()
    embedding_pipeline = EmbeddingPipeline()
    
    try:
        # Get all documents
        result = await db.execute(select(Document))
        documents = result.scalars().all()
        
        print(f"📄 Found {len(documents)} documents in database.")
        
        count = 0
        for doc in documents:
            file_path = doc.file_path
            
            # Fix path if it's relative
            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path)
            
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                continue
                
            print(f"🔄 Processing: {doc.title} ({file_path})")
            
            # Read file content (basic text extraction for now)
            try:
                import fitz  # PyMuPDF
                with fitz.open(file_path) as pdf:
                    text_content = ""
                    for page in pdf:
                        text_content += page.get_text()
                
                if not text_content.strip():
                    print("⚠️ No text extracted (empty or image-based PDF)")
                    continue
                    
                # Add to vector store
                print(f"   - Adding to vector store (Length: {len(text_content)} chars)...")
                
                # Create chunks manually for the script
                chunk_size = 1000
                chunks = []
                for i in range(0, len(text_content), chunk_size):
                    chunk_text = text_content[i:i + chunk_size]
                    chunks.append({
                        "id": f"{doc.id}_{i}",
                        "content": chunk_text,
                        "document_id": str(doc.id),
                        "chunk_type": "paragraph",
                        "syllabus_tags": [],
                        "source": doc.title
                    })

                await embedding_pipeline.index_chunks(
                    chunks=chunks,
                    user_id=str(doc.user_id)
                )
                count += 1
                print("   ✅ Indexed successfully")
                
            except Exception as e:
                print(f"❌ Error processing {doc.title}: {e}")
                
        print(f"\n🎉 Finished! Re-indexed {count} documents.")
        
    finally:
        await db.close()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reindex_documents())
