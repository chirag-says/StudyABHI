"""
Syllabus Models
Hierarchical structure for exam syllabus management
Supports: UPSC (Prelims/Mains), JEE, NEET
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Integer, Text, ForeignKey, Table, DateTime
)
from sqlalchemy.orm import relationship
from typing import Optional

from app.core.database import Base
from app.models.base import TimestampMixin


class ExamType(Base, TimestampMixin):
    """
    Top-level exam type (UPSC, JEE, NEET)
    
    Example:
    - UPSC Civil Services
    - JEE Main
    - NEET UG
    """
    __tablename__ = "exam_types"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(20), unique=True, nullable=False, index=True)  # upsc, jee, neet
    name = Column(String(100), nullable=False)  # "UPSC Civil Services"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)  # For sorting
    
    # Relationships
    exam_stages = relationship("ExamStage", back_populates="exam_type", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExamType {self.code}>"


class ExamStage(Base, TimestampMixin):
    """
    Stage/Paper within an exam
    
    Example for UPSC:
    - Prelims (Paper 1: GS, Paper 2: CSAT)
    - Mains (GS1, GS2, GS3, GS4, Essay, Optional)
    - Interview
    
    Example for JEE:
    - JEE Main
    - JEE Advanced
    """
    __tablename__ = "exam_stages"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_type_id = Column(String(36), ForeignKey("exam_types.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)  # prelims, mains, interview
    name = Column(String(100), nullable=False)  # "Preliminary Examination"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Relationships
    exam_type = relationship("ExamType", back_populates="exam_stages")
    papers = relationship("Paper", back_populates="exam_stage", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExamStage {self.code}>"


class Paper(Base, TimestampMixin):
    """
    Individual paper within a stage
    
    Example for UPSC Prelims:
    - GS Paper 1 (General Studies)
    - GS Paper 2 (CSAT)
    
    Example for UPSC Mains:
    - Essay
    - GS Paper 1 (Indian Heritage & Culture)
    - GS Paper 2 (Governance, Constitution)
    - GS Paper 3 (Technology, Environment)
    - GS Paper 4 (Ethics)
    """
    __tablename__ = "papers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    exam_stage_id = Column(String(36), ForeignKey("exam_stages.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)  # gs1, gs2, essay
    name = Column(String(150), nullable=False)  # "General Studies Paper 1"
    description = Column(Text, nullable=True)
    max_marks = Column(Integer, nullable=True)  # 200
    duration_minutes = Column(Integer, nullable=True)  # 120
    is_qualifying = Column(Boolean, default=False)  # CSAT is qualifying
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Relationships
    exam_stage = relationship("ExamStage", back_populates="papers")
    subjects = relationship("Subject", back_populates="paper", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Paper {self.code}>"


class Subject(Base, TimestampMixin):
    """
    Subject/Section within a paper
    
    Example for UPSC Prelims GS1:
    - History
    - Geography
    - Polity
    - Economy
    - Science & Technology
    - Environment
    - Current Affairs
    """
    __tablename__ = "subjects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    paper_id = Column(String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), nullable=False, index=True)  # history, geography
    name = Column(String(150), nullable=False)  # "Indian History"
    description = Column(Text, nullable=True)
    weightage = Column(Integer, nullable=True)  # Approximate % in exam
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Relationships
    paper = relationship("Paper", back_populates="subjects")
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subject {self.code}>"


class Topic(Base, TimestampMixin):
    """
    Topic within a subject (can be hierarchical - topics can have subtopics)
    
    Example for History:
    - Ancient India
      - Indus Valley Civilization
      - Vedic Period
      - Mauryan Empire
    - Medieval India
      - Delhi Sultanate
      - Mughal Empire
    - Modern India
      - British Rule
      - Freedom Movement
    """
    __tablename__ = "topics"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(String(36), ForeignKey("topics.id", ondelete="CASCADE"), nullable=True)  # For subtopics
    
    code = Column(String(100), nullable=False, index=True)  # ancient-india, mauryan-empire
    name = Column(String(200), nullable=False)  # "Mauryan Empire"
    description = Column(Text, nullable=True)
    
    # Hierarchy level (0 = root topic, 1 = subtopic, 2 = sub-subtopic, etc.)
    level = Column(Integer, default=0)
    
    # Learning metadata
    importance = Column(String(20), default="medium")  # low, medium, high, critical
    estimated_hours = Column(Integer, nullable=True)  # Estimated study time
    
    is_active = Column(Boolean, default=True)
    order = Column(Integer, default=0)
    
    # Relationships
    subject = relationship("Subject", back_populates="topics")
    parent = relationship("Topic", remote_side=[id], back_populates="children")
    children = relationship("Topic", back_populates="parent", cascade="all, delete-orphan")
    
    # Content associations (via association table)
    contents = relationship("Content", secondary="content_topics", back_populates="topics")
    
    def __repr__(self):
        return f"<Topic {self.code}>"
    
    @property
    def full_path(self) -> str:
        """Get full topic path like 'History > Ancient India > Mauryan Empire'"""
        parts = [self.name]
        parent = self.parent
        while parent:
            parts.insert(0, parent.name)
            parent = parent.parent
        return " > ".join(parts)


# Association table for Content <-> Topic (Many-to-Many)
content_topics = Table(
    "content_topics",
    Base.metadata,
    Column("content_id", String(36), ForeignKey("contents.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", String(36), ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)
