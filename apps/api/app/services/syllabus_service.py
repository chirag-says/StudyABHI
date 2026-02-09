"""
Syllabus Service
Business logic for syllabus management
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.syllabus import ExamType, ExamStage, Paper, Subject, Topic
from app.schemas.syllabus import (
    ExamTypeCreate, ExamTypeUpdate,
    ExamStageCreate, ExamStageUpdate,
    PaperCreate, PaperUpdate,
    SubjectCreate, SubjectUpdate,
    TopicCreate, TopicUpdate,
)


class SyllabusService:
    """Service class for syllabus-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== ExamType ====================
    
    async def list_exam_types(self, include_stages: bool = False) -> List[ExamType]:
        """List all exam types"""
        query = select(ExamType).where(ExamType.is_active == True)
        
        if include_stages:
            query = query.options(selectinload(ExamType.exam_stages))
        
        query = query.order_by(ExamType.order)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_exam_type(self, exam_type_id: str) -> Optional[ExamType]:
        """Get exam type by ID"""
        result = await self.db.execute(
            select(ExamType)
            .options(selectinload(ExamType.exam_stages))
            .where(ExamType.id == exam_type_id)
        )
        return result.scalar_one_or_none()
    
    async def get_exam_type_by_code(self, code: str) -> Optional[ExamType]:
        """Get exam type by code"""
        result = await self.db.execute(
            select(ExamType).where(ExamType.code == code.lower())
        )
        return result.scalar_one_or_none()
    
    async def create_exam_type(self, data: ExamTypeCreate) -> ExamType:
        """Create new exam type"""
        exam_type = ExamType(
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            is_active=data.is_active,
            order=data.order,
        )
        self.db.add(exam_type)
        await self.db.flush()
        await self.db.refresh(exam_type)
        return exam_type
    
    async def update_exam_type(
        self, exam_type_id: str, data: ExamTypeUpdate
    ) -> Optional[ExamType]:
        """Update exam type"""
        exam_type = await self.get_exam_type(exam_type_id)
        if not exam_type:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(exam_type, field, value)
        
        await self.db.flush()
        await self.db.refresh(exam_type)
        return exam_type
    
    # ==================== ExamStage ====================
    
    async def list_stages(self, exam_type_id: str) -> List[ExamStage]:
        """List stages for an exam type"""
        result = await self.db.execute(
            select(ExamStage)
            .where(ExamStage.exam_type_id == exam_type_id)
            .where(ExamStage.is_active == True)
            .order_by(ExamStage.order)
        )
        return list(result.scalars().all())
    
    async def get_stage(self, stage_id: str) -> Optional[ExamStage]:
        """Get stage by ID"""
        result = await self.db.execute(
            select(ExamStage)
            .options(selectinload(ExamStage.papers))
            .where(ExamStage.id == stage_id)
        )
        return result.scalar_one_or_none()
    
    async def create_stage(self, data: ExamStageCreate) -> ExamStage:
        """Create new exam stage"""
        stage = ExamStage(
            exam_type_id=data.exam_type_id,
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            is_active=data.is_active,
            order=data.order,
        )
        self.db.add(stage)
        await self.db.flush()
        await self.db.refresh(stage)
        return stage
    
    async def update_stage(
        self, stage_id: str, data: ExamStageUpdate
    ) -> Optional[ExamStage]:
        """Update stage"""
        stage = await self.get_stage(stage_id)
        if not stage:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(stage, field, value)
        
        await self.db.flush()
        await self.db.refresh(stage)
        return stage
    
    # ==================== Paper ====================
    
    async def list_papers(self, stage_id: str) -> List[Paper]:
        """List papers for a stage"""
        result = await self.db.execute(
            select(Paper)
            .where(Paper.exam_stage_id == stage_id)
            .where(Paper.is_active == True)
            .order_by(Paper.order)
        )
        return list(result.scalars().all())
    
    async def get_paper(self, paper_id: str) -> Optional[Paper]:
        """Get paper by ID"""
        result = await self.db.execute(
            select(Paper)
            .options(selectinload(Paper.subjects))
            .where(Paper.id == paper_id)
        )
        return result.scalar_one_or_none()
    
    async def create_paper(self, data: PaperCreate) -> Paper:
        """Create new paper"""
        paper = Paper(
            exam_stage_id=data.exam_stage_id,
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            max_marks=data.max_marks,
            duration_minutes=data.duration_minutes,
            is_qualifying=data.is_qualifying,
            is_active=data.is_active,
            order=data.order,
        )
        self.db.add(paper)
        await self.db.flush()
        await self.db.refresh(paper)
        return paper
    
    async def update_paper(
        self, paper_id: str, data: PaperUpdate
    ) -> Optional[Paper]:
        """Update paper"""
        paper = await self.get_paper(paper_id)
        if not paper:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(paper, field, value)
        
        await self.db.flush()
        await self.db.refresh(paper)
        return paper
    
    # ==================== Subject ====================
    
    async def list_subjects(self, paper_id: str) -> List[Subject]:
        """List subjects for a paper"""
        result = await self.db.execute(
            select(Subject)
            .where(Subject.paper_id == paper_id)
            .where(Subject.is_active == True)
            .order_by(Subject.order)
        )
        return list(result.scalars().all())
    
    async def get_subject(self, subject_id: str) -> Optional[Subject]:
        """Get subject by ID"""
        result = await self.db.execute(
            select(Subject)
            .options(selectinload(Subject.topics))
            .where(Subject.id == subject_id)
        )
        return result.scalar_one_or_none()
    
    async def create_subject(self, data: SubjectCreate) -> Subject:
        """Create new subject"""
        subject = Subject(
            paper_id=data.paper_id,
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            weightage=data.weightage,
            is_active=data.is_active,
            order=data.order,
        )
        self.db.add(subject)
        await self.db.flush()
        await self.db.refresh(subject)
        return subject
    
    async def update_subject(
        self, subject_id: str, data: SubjectUpdate
    ) -> Optional[Subject]:
        """Update subject"""
        subject = await self.get_subject(subject_id)
        if not subject:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(subject, field, value)
        
        await self.db.flush()
        await self.db.refresh(subject)
        return subject
    
    # ==================== Topic ====================
    
    async def list_topics(
        self, 
        subject_id: str, 
        parent_id: Optional[str] = None,
        include_children: bool = False
    ) -> List[Topic]:
        """List topics for a subject"""
        query = select(Topic).where(Topic.subject_id == subject_id)
        
        if parent_id:
            query = query.where(Topic.parent_id == parent_id)
        else:
            query = query.where(Topic.parent_id.is_(None))  # Root topics only
        
        if include_children:
            query = query.options(selectinload(Topic.children))
        
        query = query.where(Topic.is_active == True).order_by(Topic.order)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_topic(self, topic_id: str) -> Optional[Topic]:
        """Get topic by ID with children"""
        result = await self.db.execute(
            select(Topic)
            .options(
                selectinload(Topic.children),
                selectinload(Topic.parent)
            )
            .where(Topic.id == topic_id)
        )
        return result.scalar_one_or_none()
    
    async def create_topic(self, data: TopicCreate) -> Topic:
        """Create new topic"""
        # Determine level based on parent
        level = 0
        if data.parent_id:
            parent = await self.get_topic(data.parent_id)
            if parent:
                level = parent.level + 1
        
        topic = Topic(
            subject_id=data.subject_id,
            parent_id=data.parent_id,
            code=data.code.lower(),
            name=data.name,
            description=data.description,
            level=level,
            importance=data.importance,
            estimated_hours=data.estimated_hours,
            is_active=data.is_active,
            order=data.order,
        )
        self.db.add(topic)
        await self.db.flush()
        await self.db.refresh(topic)
        return topic
    
    async def update_topic(
        self, topic_id: str, data: TopicUpdate
    ) -> Optional[Topic]:
        """Update topic"""
        topic = await self.get_topic(topic_id)
        if not topic:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(topic, field, value)
        
        # Update level if parent changed
        if data.parent_id is not None:
            if data.parent_id:
                parent = await self.get_topic(data.parent_id)
                topic.level = parent.level + 1 if parent else 0
            else:
                topic.level = 0
        
        await self.db.flush()
        await self.db.refresh(topic)
        return topic
    
    async def delete_topic(self, topic_id: str) -> bool:
        """Delete topic (soft delete)"""
        topic = await self.get_topic(topic_id)
        if not topic:
            return False
        
        topic.is_active = False
        await self.db.flush()
        return True
    
    # ==================== Full Syllabus Tree ====================
    
    async def get_full_syllabus(self, exam_code: str) -> Optional[dict]:
        """Get complete syllabus tree for an exam"""
        exam_type = await self.get_exam_type_by_code(exam_code)
        if not exam_type:
            return None
        
        # Build the tree structure
        stages = await self.list_stages(exam_type.id)
        
        tree = {
            "exam_type": exam_type,
            "stages": []
        }
        
        for stage in stages:
            stage_data = {
                "stage": stage,
                "papers": []
            }
            
            papers = await self.list_papers(stage.id)
            for paper in papers:
                paper_data = {
                    "paper": paper,
                    "subjects": []
                }
                
                subjects = await self.list_subjects(paper.id)
                for subject in subjects:
                    subject_data = {
                        "subject": subject,
                        "topics": await self._get_topic_tree(subject.id)
                    }
                    paper_data["subjects"].append(subject_data)
                
                stage_data["papers"].append(paper_data)
            
            tree["stages"].append(stage_data)
        
        return tree
    
    async def _get_topic_tree(self, subject_id: str, parent_id: Optional[str] = None) -> List[dict]:
        """Recursively build topic tree"""
        topics = await self.list_topics(subject_id, parent_id)
        result = []
        
        for topic in topics:
            topic_data = {
                "topic": topic,
                "children": await self._get_topic_tree(subject_id, topic.id)
            }
            result.append(topic_data)
        
        return result
