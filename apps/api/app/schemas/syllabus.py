"""
Syllabus Schemas
Pydantic models for syllabus-related request/response validation
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== ExamType ====================

class ExamTypeBase(BaseModel):
    """Base schema for ExamType"""
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    order: int = 0


class ExamTypeCreate(ExamTypeBase):
    """Schema for creating an ExamType"""
    pass


class ExamTypeUpdate(BaseModel):
    """Schema for updating an ExamType"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class ExamTypeResponse(ExamTypeBase):
    """Schema for ExamType response"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ExamTypeWithStages(ExamTypeResponse):
    """ExamType with nested stages"""
    exam_stages: List["ExamStageResponse"] = []


# ==================== ExamStage ====================

class ExamStageBase(BaseModel):
    """Base schema for ExamStage"""
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    order: int = 0


class ExamStageCreate(ExamStageBase):
    """Schema for creating an ExamStage"""
    exam_type_id: str


class ExamStageUpdate(BaseModel):
    """Schema for updating an ExamStage"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class ExamStageResponse(ExamStageBase):
    """Schema for ExamStage response"""
    id: str
    exam_type_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Paper ====================

class PaperBase(BaseModel):
    """Base schema for Paper"""
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    max_marks: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_qualifying: bool = False
    is_active: bool = True
    order: int = 0


class PaperCreate(PaperBase):
    """Schema for creating a Paper"""
    exam_stage_id: str


class PaperUpdate(BaseModel):
    """Schema for updating a Paper"""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    max_marks: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_qualifying: Optional[bool] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class PaperResponse(PaperBase):
    """Schema for Paper response"""
    id: str
    exam_stage_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Subject ====================

class SubjectBase(BaseModel):
    """Base schema for Subject"""
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    weightage: Optional[int] = Field(None, ge=0, le=100)
    is_active: bool = True
    order: int = 0


class SubjectCreate(SubjectBase):
    """Schema for creating a Subject"""
    paper_id: str


class SubjectUpdate(BaseModel):
    """Schema for updating a Subject"""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    weightage: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None
    order: Optional[int] = None


class SubjectResponse(SubjectBase):
    """Schema for Subject response"""
    id: str
    paper_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ==================== Topic ====================

class TopicBase(BaseModel):
    """Base schema for Topic"""
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    importance: str = "medium"  # low, medium, high, critical
    estimated_hours: Optional[int] = None
    is_active: bool = True
    order: int = 0


class TopicCreate(TopicBase):
    """Schema for creating a Topic"""
    subject_id: str
    parent_id: Optional[str] = None  # For subtopics


class TopicUpdate(BaseModel):
    """Schema for updating a Topic"""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    importance: Optional[str] = None
    estimated_hours: Optional[int] = None
    parent_id: Optional[str] = None
    is_active: Optional[bool] = None
    order: Optional[int] = None


class TopicResponse(TopicBase):
    """Schema for Topic response"""
    id: str
    subject_id: str
    parent_id: Optional[str] = None
    level: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TopicWithChildren(TopicResponse):
    """Topic with nested children"""
    children: List["TopicWithChildren"] = []


# ==================== Full Syllabus Tree ====================

class SyllabusTreeResponse(BaseModel):
    """Complete syllabus tree structure"""
    exam_types: List[ExamTypeWithStages]


# Update forward references
ExamTypeWithStages.model_rebuild()
TopicWithChildren.model_rebuild()
