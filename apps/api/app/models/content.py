"""
Content Models
Learning content management - Articles, Notes, PDFs
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, DateTime, Table
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.models.base import TimestampMixin


class ContentType(str, enum.Enum):
    """Type of content"""
    ARTICLE = "article"  # Long-form educational content
    NOTE = "note"        # Quick notes/summaries
    PDF = "pdf"          # PDF documents
    VIDEO = "video"      # Video content (future)
    QUIZ = "quiz"        # Quiz/Practice questions


class DifficultyLevel(str, enum.Enum):
    """Content difficulty level"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class Language(str, enum.Enum):
    """Supported languages"""
    EN = "en"           # English
    HI = "hi"           # Hindi
    HINGLISH = "hinglish"  # Mixed Hindi-English


class ContentStatus(str, enum.Enum):
    """Content publication status"""
    DRAFT = "draft"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Content(Base, TimestampMixin):
    """
    Main content model for articles, notes, and other learning materials.
    
    Features:
    - Multi-language support (en, hi, hinglish)
    - Difficulty levels
    - Tagging with syllabus topics
    - Version tracking
    - View/engagement metrics
    """
    __tablename__ = "contents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic Info
    title = Column(String(300), nullable=False, index=True)
    slug = Column(String(350), unique=True, nullable=False, index=True)  # URL-friendly
    subtitle = Column(String(500), nullable=True)
    
    # Content
    content_type = Column(String(20), default=ContentType.ARTICLE.value, nullable=False)
    body = Column(Text, nullable=True)  # Main content (markdown/HTML)
    summary = Column(Text, nullable=True)  # Brief summary
    
    # Metadata
    language = Column(String(20), default=Language.EN.value, nullable=False)
    difficulty = Column(String(20), default=DifficultyLevel.INTERMEDIATE.value)
    status = Column(String(20), default=ContentStatus.DRAFT.value)
    
    # For PDF/Video content
    file_url = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)  # For videos
    
    # Reading/Learning metadata
    estimated_read_time = Column(Integer, nullable=True)  # Minutes
    word_count = Column(Integer, nullable=True)
    
    # Engagement metrics
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    bookmark_count = Column(Integer, default=0)
    
    # SEO
    meta_title = Column(String(200), nullable=True)
    meta_description = Column(String(500), nullable=True)
    
    # Author
    author_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Publishing
    published_at = Column(DateTime, nullable=True)
    
    # Versioning
    version = Column(Integer, default=1)
    
    # Feature flags
    is_featured = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)  # Paid content
    
    # Relationships
    author = relationship("User", backref="contents")
    topics = relationship("Topic", secondary="content_topics", back_populates="contents")
    tags = relationship("ContentTag", secondary="content_tag_associations", back_populates="contents")
    
    def __repr__(self):
        return f"<Content {self.slug}>"
    
    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-friendly slug from title"""
        import re
        slug = title.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = slug.strip('-')
        return slug[:350]


class ContentTag(Base, TimestampMixin):
    """
    Tags for content categorization
    Separate from syllabus topics - for flexible tagging
    
    Examples: current-affairs-2024, pyq, ncert, important
    """
    __tablename__ = "content_tags"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(20), default="#6366f1")  # For UI display
    
    # Relationships
    contents = relationship("Content", secondary="content_tag_associations", back_populates="tags")
    
    def __repr__(self):
        return f"<ContentTag {self.slug}>"


# Association table for Content <-> Tag (Many-to-Many)
content_tag_associations = Table(
    "content_tag_associations",
    Base.metadata,
    Column("content_id", String(36), ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("content_tags.id", ondelete="CASCADE"), primary_key=True),
)


class ContentRevision(Base, TimestampMixin):
    """
    Content version history for tracking changes
    """
    __tablename__ = "content_revisions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String(36), ForeignKey("contents.id", ondelete="CASCADE"), nullable=False)
    
    version = Column(Integer, nullable=False)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=True)
    
    # Who made the change
    editor_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_summary = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<ContentRevision {self.content_id} v{self.version}>"
