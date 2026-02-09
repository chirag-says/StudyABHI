"""
Content Schemas
Pydantic models for content-related request/response validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ContentTypeEnum(str, Enum):
    ARTICLE = "article"
    NOTE = "note"
    PDF = "pdf"
    VIDEO = "video"
    QUIZ = "quiz"


class DifficultyLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class LanguageEnum(str, Enum):
    EN = "en"
    HI = "hi"
    HINGLISH = "hinglish"


class ContentStatusEnum(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# ==================== ContentTag ====================

class ContentTagBase(BaseModel):
    """Base schema for ContentTag"""
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    color: str = "#6366f1"


class ContentTagCreate(ContentTagBase):
    """Schema for creating a ContentTag"""
    pass


class ContentTagUpdate(BaseModel):
    """Schema for updating a ContentTag"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = None


class ContentTagResponse(ContentTagBase):
    """Schema for ContentTag response"""
    id: str
    slug: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Content ====================

class ContentBase(BaseModel):
    """Base schema for Content"""
    title: str = Field(..., min_length=3, max_length=300)
    subtitle: Optional[str] = Field(None, max_length=500)
    content_type: ContentTypeEnum = ContentTypeEnum.ARTICLE
    body: Optional[str] = None
    summary: Optional[str] = None
    language: LanguageEnum = LanguageEnum.EN
    difficulty: DifficultyLevelEnum = DifficultyLevelEnum.INTERMEDIATE
    estimated_read_time: Optional[int] = None
    is_premium: bool = False


class ContentCreate(ContentBase):
    """Schema for creating Content"""
    topic_ids: List[str] = []  # Syllabus topic IDs
    tag_ids: List[str] = []    # Tag IDs
    
    # For PDFs/Videos
    file_url: Optional[str] = None
    duration_minutes: Optional[int] = None


class ContentUpdate(BaseModel):
    """Schema for updating Content"""
    title: Optional[str] = Field(None, min_length=3, max_length=300)
    subtitle: Optional[str] = Field(None, max_length=500)
    body: Optional[str] = None
    summary: Optional[str] = None
    language: Optional[LanguageEnum] = None
    difficulty: Optional[DifficultyLevelEnum] = None
    status: Optional[ContentStatusEnum] = None
    estimated_read_time: Optional[int] = None
    is_featured: Optional[bool] = None
    is_premium: Optional[bool] = None
    
    # Update associations
    topic_ids: Optional[List[str]] = None
    tag_ids: Optional[List[str]] = None
    
    # SEO
    meta_title: Optional[str] = Field(None, max_length=200)
    meta_description: Optional[str] = Field(None, max_length=500)


class ContentResponse(ContentBase):
    """Schema for Content response"""
    id: str
    slug: str
    status: str
    file_url: Optional[str] = None
    duration_minutes: Optional[int] = None
    word_count: Optional[int] = None
    view_count: int = 0
    like_count: int = 0
    bookmark_count: int = 0
    is_featured: bool = False
    author_id: Optional[str] = None
    published_at: Optional[datetime] = None
    version: int = 1
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContentDetailResponse(ContentResponse):
    """Detailed content response with relationships"""
    topics: List["TopicBriefResponse"] = []
    tags: List[ContentTagResponse] = []
    author: Optional["AuthorResponse"] = None


class ContentListResponse(BaseModel):
    """Paginated content list response"""
    items: List[ContentResponse]
    total: int
    page: int
    limit: int
    pages: int


# ==================== Brief Responses for Relationships ====================

class TopicBriefResponse(BaseModel):
    """Brief topic info for content relationships"""
    id: str
    code: str
    name: str
    
    class Config:
        from_attributes = True


class AuthorResponse(BaseModel):
    """Brief author info"""
    id: str
    full_name: str
    profile_image: Optional[str] = None
    
    class Config:
        from_attributes = True


# ==================== Content Filters ====================

class ContentFilterParams(BaseModel):
    """Query parameters for filtering content"""
    content_type: Optional[ContentTypeEnum] = None
    language: Optional[LanguageEnum] = None
    difficulty: Optional[DifficultyLevelEnum] = None
    status: Optional[ContentStatusEnum] = None
    topic_id: Optional[str] = None
    tag_id: Optional[str] = None
    author_id: Optional[str] = None
    is_featured: Optional[bool] = None
    is_premium: Optional[bool] = None
    search: Optional[str] = None  # Search in title/body
    
    # Pagination
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


# Update forward references
ContentDetailResponse.model_rebuild()
