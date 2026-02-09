"""
Syllabus API Endpoints
Routes for syllabus management - exams, stages, papers, subjects, topics
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin_user
from app.models.user import User
from app.services.syllabus_service import SyllabusService
from app.schemas.syllabus import (
    ExamTypeCreate, ExamTypeUpdate, ExamTypeResponse, ExamTypeWithStages,
    ExamStageCreate, ExamStageUpdate, ExamStageResponse,
    PaperCreate, PaperUpdate, PaperResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse,
    TopicCreate, TopicUpdate, TopicResponse, TopicWithChildren,
)

router = APIRouter()


# ==================== Exam Types ====================

@router.get("/exams", response_model=List[ExamTypeResponse])
async def list_exam_types(
    db: AsyncSession = Depends(get_db),
):
    """List all exam types (UPSC, JEE, NEET)"""
    service = SyllabusService(db)
    return await service.list_exam_types()


@router.get("/exams/{exam_id}", response_model=ExamTypeWithStages)
async def get_exam_type(
    exam_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get exam type by ID with stages"""
    service = SyllabusService(db)
    exam = await service.get_exam_type(exam_id)
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam type not found"
        )
    
    return exam


@router.get("/exams/code/{code}")
async def get_exam_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full syllabus tree for an exam by code (e.g. 'upsc')"""
    service = SyllabusService(db)
    tree = await service.get_full_syllabus(code)
    
    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Exam '{code}' not found"
        )
    
    return tree


@router.post("/exams", response_model=ExamTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_exam_type(
    data: ExamTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create new exam type (admin only)"""
    service = SyllabusService(db)
    
    # Check if code already exists
    existing = await service.get_exam_type_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam type with this code already exists"
        )
    
    return await service.create_exam_type(data)


@router.patch("/exams/{exam_id}", response_model=ExamTypeResponse)
async def update_exam_type(
    exam_id: str,
    data: ExamTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update exam type (admin only)"""
    service = SyllabusService(db)
    exam = await service.update_exam_type(exam_id, data)
    
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam type not found"
        )
    
    return exam


# ==================== Exam Stages ====================

@router.get("/stages", response_model=List[ExamStageResponse])
async def list_stages(
    exam_type_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List stages for an exam type"""
    service = SyllabusService(db)
    return await service.list_stages(exam_type_id)


@router.get("/stages/{stage_id}", response_model=ExamStageResponse)
async def get_stage(
    stage_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get stage by ID"""
    service = SyllabusService(db)
    stage = await service.get_stage(stage_id)
    
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not found"
        )
    
    return stage


@router.post("/stages", response_model=ExamStageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    data: ExamStageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create new exam stage (admin only)"""
    service = SyllabusService(db)
    return await service.create_stage(data)


@router.patch("/stages/{stage_id}", response_model=ExamStageResponse)
async def update_stage(
    stage_id: str,
    data: ExamStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update stage (admin only)"""
    service = SyllabusService(db)
    stage = await service.update_stage(stage_id, data)
    
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stage not found"
        )
    
    return stage


# ==================== Papers ====================

@router.get("/papers", response_model=List[PaperResponse])
async def list_papers(
    stage_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List papers for a stage"""
    service = SyllabusService(db)
    return await service.list_papers(stage_id)


@router.get("/papers/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get paper by ID"""
    service = SyllabusService(db)
    paper = await service.get_paper(paper_id)
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    return paper


@router.post("/papers", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    data: PaperCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create new paper (admin only)"""
    service = SyllabusService(db)
    return await service.create_paper(data)


@router.patch("/papers/{paper_id}", response_model=PaperResponse)
async def update_paper(
    paper_id: str,
    data: PaperUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update paper (admin only)"""
    service = SyllabusService(db)
    paper = await service.update_paper(paper_id, data)
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    return paper


# ==================== Subjects ====================

@router.get("/subjects", response_model=List[SubjectResponse])
async def list_subjects(
    paper_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List subjects for a paper"""
    service = SyllabusService(db)
    return await service.list_subjects(paper_id)


@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get subject by ID"""
    service = SyllabusService(db)
    subject = await service.get_subject(subject_id)
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    return subject


@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create new subject (admin only)"""
    service = SyllabusService(db)
    return await service.create_subject(data)


@router.patch("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update subject (admin only)"""
    service = SyllabusService(db)
    subject = await service.update_subject(subject_id, data)
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
    
    return subject


# ==================== Topics ====================

@router.get("/topics", response_model=List[TopicResponse])
async def list_topics(
    subject_id: str,
    parent_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List topics for a subject.
    
    If parent_id is not provided, returns root-level topics only.
    """
    service = SyllabusService(db)
    return await service.list_topics(subject_id, parent_id)


@router.get("/topics/{topic_id}", response_model=TopicWithChildren)
async def get_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get topic by ID with children"""
    service = SyllabusService(db)
    topic = await service.get_topic(topic_id)
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic


@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
async def create_topic(
    data: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Create new topic (admin only).
    
    Set parent_id to create a subtopic.
    """
    service = SyllabusService(db)
    return await service.create_topic(data)


@router.patch("/topics/{topic_id}", response_model=TopicResponse)
async def update_topic(
    topic_id: str,
    data: TopicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update topic (admin only)"""
    service = SyllabusService(db)
    topic = await service.update_topic(topic_id, data)
    
    if not topic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return topic


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_topic(
    topic_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Delete topic (soft delete, admin only)"""
    service = SyllabusService(db)
    
    if not await service.delete_topic(topic_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Topic not found"
        )
    
    return None
