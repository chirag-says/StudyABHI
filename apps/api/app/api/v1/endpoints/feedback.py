"""
User Feedback System
Schema + API endpoints for collecting feedback with minimal friction
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum

from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import Base, get_db
from app.models.base import TimestampMixin
from app.core.dependencies import get_current_user
from app.models.user import User


# ============================================================
# DATABASE MODELS
# ============================================================

class FeedbackType(str, Enum):
    AI_ANSWER = "ai_answer"
    QUIZ = "quiz"
    ROADMAP = "roadmap"
    GENERAL = "general"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"


class Feedback(Base, TimestampMixin):
    """
    User feedback storage with minimal schema for flexibility
    """
    __tablename__ = "user_feedback"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Feedback type and rating
    feedback_type = Column(String(30), nullable=False)
    rating = Column(Integer, nullable=True)  # 1-5 or thumbs up/down (1/0)
    
    # Context - what was the feedback about
    context_type = Column(String(50), nullable=True)  # "rag_query", "quiz_result", etc.
    context_id = Column(String(36), nullable=True)  # ID of the related item
    
    # Content
    comment = Column(Text, nullable=True)
    
    # JSON for flexible additional data
    extra_data = Column(JSON, nullable=True, default={})
    # Example: {"question": "...", "answer": "...", "was_helpful": true}
    
    # Tracking
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)
    
    # Source page/component
    source_page = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", backref="feedback")


class FeedbackSummary(Base, TimestampMixin):
    """
    Aggregated feedback metrics (updated daily)
    """
    __tablename__ = "feedback_summaries"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(DateTime, nullable=False)
    
    # Counts
    total_feedback = Column(Integer, default=0)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    
    # Breakdown by type
    ai_answer_positive = Column(Integer, default=0)
    ai_answer_negative = Column(Integer, default=0)
    quiz_rating_avg = Column(Integer, nullable=True)
    roadmap_rating_avg = Column(Integer, nullable=True)
    
    # NPS-style score
    nps_score = Column(Integer, nullable=True)


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class QuickFeedbackRequest(BaseModel):
    """Quick thumbs up/down feedback"""
    helpful: bool
    context_type: str = Field(..., description="ai_answer, quiz, roadmap")
    context_id: Optional[str] = None
    

class QuickFeedbackResponse(BaseModel):
    success: bool
    message: str = "Thanks for your feedback!"


class DetailedFeedbackRequest(BaseModel):
    """Detailed feedback with optional comment"""
    feedback_type: str = Field(..., description="ai_answer, quiz, roadmap, general, bug_report")
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=2000)
    context_type: Optional[str] = None
    context_id: Optional[str] = None
    metadata: Optional[dict] = None


class DetailedFeedbackResponse(BaseModel):
    id: str
    message: str
    

class FeedbackStatsResponse(BaseModel):
    """Admin feedback statistics"""
    total_feedback: int
    positive_percentage: float
    ai_answer_rating: float
    roadmap_rating: float
    recent_comments: List[dict]


# ============================================================
# API ROUTER
# ============================================================

router = APIRouter()


@router.post("/quick", response_model=QuickFeedbackResponse)
async def submit_quick_feedback(
    request: QuickFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Quick feedback (thumbs up/down) - minimal friction
    
    Use after:
    - AI answers a question
    - Quiz completion
    - Viewing roadmap recommendations
    """
    feedback = Feedback(
        user_id=current_user.id,
        feedback_type=request.context_type,
        rating=1 if request.helpful else 0,
        context_type=request.context_type,
        context_id=request.context_id,
        extra_data={"helpful": request.helpful}
    )
    
    db.add(feedback)
    await db.commit()
    
    return QuickFeedbackResponse(
        success=True,
        message="Thanks! Your feedback helps us improve."
    )


@router.post("/detailed", response_model=DetailedFeedbackResponse)
async def submit_detailed_feedback(
    request: DetailedFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Detailed feedback with rating and comment
    
    Use for:
    - Feature requests
    - Bug reports
    - Detailed improvement suggestions
    """
    feedback = Feedback(
        user_id=current_user.id,
        feedback_type=request.feedback_type,
        rating=request.rating,
        comment=request.comment,
        context_type=request.context_type,
        context_id=request.context_id,
        extra_data=request.metadata or {}
    )
    
    db.add(feedback)
    await db.commit()
    
    return DetailedFeedbackResponse(
        id=feedback.id,
        message="Thank you for your detailed feedback! We read every submission."
    )


@router.post("/ai-answer/{answer_id}")
async def feedback_ai_answer(
    answer_id: str,
    helpful: bool,
    comment: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Specific endpoint for AI answer feedback
    Called when user clicks 👍 or 👎 after an AI response
    """
    feedback = Feedback(
        user_id=current_user.id,
        feedback_type=FeedbackType.AI_ANSWER.value,
        rating=1 if helpful else 0,
        context_type="rag_answer",
        context_id=answer_id,
        comment=comment,
        extra_data={"helpful": helpful}
    )
    
    db.add(feedback)
    await db.commit()
    
    return {"success": True}


class RoadmapFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


@router.post("/roadmap/usefulness")
async def feedback_roadmap_usefulness(
    request: RoadmapFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rate roadmap usefulness (1-5 stars)
    Show after user completes a week of tasks
    """
    feedback = Feedback(
        user_id=current_user.id,
        feedback_type=FeedbackType.ROADMAP.value,
        rating=request.rating,
        context_type="weekly_roadmap",
        comment=request.comment,
        extra_data={"rating": request.rating}
    )
    
    db.add(feedback)
    await db.commit()
    
    return {
        "success": True,
        "message": f"Thanks for rating your roadmap experience!"
    }


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get feedback statistics (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Total feedback
    total_result = await db.execute(
        select(func.count(Feedback.id)).where(Feedback.created_at >= cutoff)
    )
    total = total_result.scalar() or 0
    
    # Positive (rating >= 1 for thumbs up, >= 4 for 5-star)
    positive_result = await db.execute(
        select(func.count(Feedback.id)).where(
            Feedback.created_at >= cutoff,
            Feedback.rating >= 1
        )
    )
    positive = positive_result.scalar() or 0
    
    # AI answer average
    ai_result = await db.execute(
        select(func.avg(Feedback.rating)).where(
            Feedback.feedback_type == FeedbackType.AI_ANSWER.value,
            Feedback.created_at >= cutoff
        )
    )
    ai_avg = ai_result.scalar() or 0
    
    # Roadmap average
    roadmap_result = await db.execute(
        select(func.avg(Feedback.rating)).where(
            Feedback.feedback_type == FeedbackType.ROADMAP.value,
            Feedback.created_at >= cutoff
        )
    )
    roadmap_avg = roadmap_result.scalar() or 0
    
    # Recent comments
    comments_result = await db.execute(
        select(Feedback).where(
            Feedback.comment.isnot(None),
            Feedback.created_at >= cutoff
        ).order_by(Feedback.created_at.desc()).limit(10)
    )
    recent = comments_result.scalars().all()
    
    return FeedbackStatsResponse(
        total_feedback=total,
        positive_percentage=(positive / total * 100) if total > 0 else 0,
        ai_answer_rating=float(ai_avg) if ai_avg else 0,
        roadmap_rating=float(roadmap_avg) if roadmap_avg else 0,
        recent_comments=[
            {
                "type": f.feedback_type,
                "comment": f.comment,
                "rating": f.rating,
                "created_at": f.created_at.isoformat() if f.created_at else None
            }
            for f in recent
        ]
    )


# ============================================================
# FRONTEND INTEGRATION EXAMPLES
# ============================================================

"""
## React Component Example

```jsx
// QuickFeedback.jsx
import { useState } from 'react';

export function QuickFeedback({ contextType, contextId, onFeedback }) {
  const [submitted, setSubmitted] = useState(false);
  
  const submit = async (helpful) => {
    await fetch('/api/v1/feedback/quick', {
      method: 'POST',
      body: JSON.stringify({ helpful, context_type: contextType, context_id: contextId }),
    });
    setSubmitted(true);
    onFeedback?.(helpful);
  };
  
  if (submitted) return <span className="text-sm text-gray-500">Thanks!</span>;
  
  return (
    <div className="flex gap-2">
      <button onClick={() => submit(true)} className="hover:scale-110">👍</button>
      <button onClick={() => submit(false)} className="hover:scale-110">👎</button>
    </div>
  );
}
```

## Usage in AI Answer Component

```jsx
<div className="ai-answer">
  <p>{answer}</p>
  <div className="flex items-center gap-2 mt-4">
    <span className="text-sm">Was this helpful?</span>
    <QuickFeedback contextType="ai_answer" contextId={answerId} />
  </div>
</div>
```

## Roadmap Rating Modal (show weekly)

```jsx
// RoadmapRating.jsx
export function RoadmapRating({ onClose }) {
  const [rating, setRating] = useState(0);
  
  const submit = async () => {
    await fetch('/api/v1/feedback/roadmap/usefulness', {
      method: 'POST',
      body: JSON.stringify({ rating }),
    });
    onClose();
  };
  
  return (
    <Modal>
      <h3>How useful was this week's roadmap?</h3>
      <StarRating value={rating} onChange={setRating} />
      <button onClick={submit}>Submit</button>
      <button onClick={onClose}>Skip</button>
    </Modal>
  );
}
```
"""
