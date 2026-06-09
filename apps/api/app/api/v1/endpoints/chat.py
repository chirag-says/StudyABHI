"""
Chat API Endpoints
General AI-powered chat for UPSC study assistance.
Uses Kimi K2.5 (via NVIDIA NIM API) for intelligent responses.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging
import json

from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== Schemas ====================

class GeneralChatRequest(BaseModel):
    """Request for general chat"""
    question: str = Field(..., min_length=1, max_length=5000)
    history: Optional[List[dict]] = None  # [{"role": "user/assistant", "content": "..."}]
    language: str = Field("en", description="Output language: en, hi, hinglish")
    stream: bool = Field(False, description="Enable streaming response")


class GeneralChatResponse(BaseModel):
    """Response from general chat"""
    answer: str
    model: str
    language: str


# ==================== System Prompt ====================

GENERAL_CHAT_SYSTEM_PROMPT = """You are an expert UPSC (Union Public Service Commission) study assistant with deep knowledge of:

1. **General Studies Papers (GS I-IV)**:
   - Indian History & Culture, World History, Geography
   - Indian Polity & Governance, Constitution
   - Indian Economy, Social Development
   - Science & Technology, Environment & Ecology
   - Ethics, Integrity & Aptitude

2. **Current Affairs**: Latest developments in India and the world relevant to UPSC

3. **Optional Subjects**: Deep knowledge in various optional subjects

Your communication style:
- Clear, structured, and exam-oriented explanations
- Use bullet points, headings, and organized formatting
- Include examples relevant to Indian context
- Mention constitutional articles, acts, and provisions when applicable
- Connect topics to current affairs
- Provide mnemonics and memory aids when helpful
- Suggest related topics for further study
- Be encouraging and supportive

When answering:
- Be accurate and precise — never fabricate information
- If you're unsure, clearly say so
- For opinion-based questions, present multiple perspectives
- Structure answers in UPSC answer writing format when appropriate
- Keep explanations concise but comprehensive

Remember: You're helping a UPSC aspirant prepare for one of the toughest exams in India. Be their best study companion."""


# ==================== Endpoints ====================

@router.post("/general", response_model=GeneralChatResponse)
async def general_chat(
    request: GeneralChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    General UPSC study chat powered by Kimi K2.5.
    
    Ask any question related to UPSC preparation and get
    comprehensive, exam-oriented answers.
    """
    try:
        from app.services.rag.pipeline import NvidiaKimiClient, MockLLMClient
        
        # Chat model: Mistral Medium 3.5 128B with its own dedicated API key
        if settings.LLM_PROVIDER == "nvidia" and settings.get_chat_api_key():
            llm_client = NvidiaKimiClient(
                model=settings.NVIDIA_CHAT_MODEL,
                api_key=settings.get_chat_api_key(),
            )
        else:
            llm_client = MockLLMClient()
            logger.warning("Using MockLLMClient — Set LLM_PROVIDER=nvidia and NVIDIA_CHAT_API_KEY for real AI responses")
        
        # Build prompt with conversation history
        prompt = _build_chat_prompt(request.question, request.history, request.language)
        
        # Generate response
        answer = await llm_client.generate(
            prompt=prompt,
            system_prompt=GENERAL_CHAT_SYSTEM_PROMPT,
            max_tokens=4096,
            temperature=0.7,
        )
        
        return GeneralChatResponse(
            answer=answer,
            model=getattr(llm_client, 'model', 'unknown'),
            language=request.language,
        )
        
    except Exception as e:
        logger.error(f"General chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/general/stream")
async def general_chat_stream(
    request: GeneralChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Streaming version of general chat.
    Returns Server-Sent Events (SSE) for real-time response display.
    """
    try:
        from app.services.rag.pipeline import NvidiaKimiClient, MockLLMClient
        
        if settings.LLM_PROVIDER == "nvidia" and settings.get_chat_api_key():
            llm_client = NvidiaKimiClient(
                model=settings.NVIDIA_CHAT_MODEL,
                api_key=settings.get_chat_api_key(),
            )
        else:
            # Fall back to non-streaming mock
            llm_client = MockLLMClient()
            mock_answer = await llm_client.generate(
                prompt=request.question,
                system_prompt=GENERAL_CHAT_SYSTEM_PROMPT,
            )
            
            async def mock_stream():
                # Send mock answer as a single chunk
                yield f"data: {json.dumps({'content': mock_answer})}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                mock_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        
        prompt = _build_chat_prompt(request.question, request.history, request.language)
        
        async def event_stream():
            try:
                async for chunk in llm_client.generate_stream(
                    prompt=prompt,
                    system_prompt=GENERAL_CHAT_SYSTEM_PROMPT,
                    max_tokens=4096,
                    temperature=0.7,
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        
    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start streaming: {str(e)}"
        )


# ==================== Helper Functions ====================

def _build_chat_prompt(
    question: str,
    history: Optional[List[dict]] = None,
    language: str = "en",
) -> str:
    """Build the chat prompt with conversation history and language instructions."""
    parts = []
    
    # Add conversation history context
    if history and len(history) > 0:
        parts.append("## Previous Conversation:")
        for msg in history[-6:]:  # Last 6 messages for context
            role = "Student" if msg.get("role") == "user" else "Tutor"
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")
        parts.append("")
    
    # Add the current question
    parts.append(f"## Student's Question:\n{question}")
    
    # Add language instruction
    if language == "hi":
        parts.append("\n\nIMPORTANT: Write your entire response in Hindi (Devanagari script).")
    elif language == "hinglish":
        parts.append("\n\nIMPORTANT: Write your response in Hinglish (Hindi words in Roman script, mixed with English technical terms).")
    
    return "\n".join(parts)
