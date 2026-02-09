"""
UPSC Syllabus Database Seeder
Seeds the database with UPSC syllabus structure from the syllabus data.
Run with: python -m app.scripts.seed_syllabus
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.syllabus import ExamType, ExamStage, Paper, Subject, Topic
from app.services.upsc_syllabus_data import UPSC_SYLLABUS, RECOMMENDED_BOOKS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed_syllabus(db: AsyncSession):
    """Seed the database with UPSC syllabus structure"""
    
    # Check if already seeded
    result = await db.execute(
        select(ExamType).where(ExamType.code == "upsc_cse")
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        logger.info("Syllabus already seeded. Skipping...")
        return
    
    logger.info("Starting syllabus seeding...")
    
    # Create Exam Type
    exam_data = UPSC_SYLLABUS["exam_type"]
    exam_type = ExamType(
        code=exam_data["code"],
        name=exam_data["name"],
        description=exam_data["description"],
        is_active=True
    )
    db.add(exam_type)
    await db.flush()
    logger.info(f"Created exam type: {exam_type.name}")
    
    # Create Stages, Papers, Subjects, Topics
    for stage_data in UPSC_SYLLABUS["stages"]:
        stage = ExamStage(
            exam_type_id=exam_type.id,
            code=stage_data["code"],
            name=stage_data["name"],
            description=stage_data.get("description"),
            order=1 if stage_data["code"] == "prelims" else 2
        )
        db.add(stage)
        await db.flush()
        logger.info(f"Created stage: {stage.name}")
        
        for paper_data in stage_data.get("papers", []):
            paper = Paper(
                stage_id=stage.id,
                code=paper_data["code"],
                name=paper_data["name"],
                max_marks=paper_data.get("max_marks"),
                duration_minutes=paper_data.get("duration_minutes"),
                is_qualifying=paper_data.get("is_qualifying", False),
                passing_marks=paper_data.get("passing_marks")
            )
            db.add(paper)
            await db.flush()
            logger.info(f"  Created paper: {paper.name}")
            
            for subject_data in paper_data.get("subjects", []):
                subject = Subject(
                    paper_id=paper.id,
                    code=subject_data["code"],
                    name=subject_data["name"],
                    weightage=subject_data.get("weightage", 0),
                    description=f"Subject covering {subject_data['name']}"
                )
                db.add(subject)
                await db.flush()
                logger.info(f"    Created subject: {subject.name}")
                
                for topic_data in subject_data.get("topics", []):
                    topic = Topic(
                        subject_id=subject.id,
                        code=topic_data["code"],
                        name=topic_data["name"],
                        importance=topic_data.get("importance", "medium"),
                        estimated_hours=topic_data.get("estimated_hours", 5)
                    )
                    db.add(topic)
                    await db.flush()
                    
                    # Create subtopics as child topics
                    for subtopic_data in topic_data.get("subtopics", []):
                        subtopic = Topic(
                            subject_id=subject.id,
                            parent_id=topic.id,
                            code=subtopic_data["code"],
                            name=subtopic_data["name"],
                            importance=topic_data.get("importance", "medium"),
                            estimated_hours=subtopic_data.get("estimated_hours", 2)
                        )
                        db.add(subtopic)
    
    await db.commit()
    logger.info("Syllabus seeding completed successfully!")


async def main():
    """Main entry point for seeding"""
    async with AsyncSessionLocal() as db:
        try:
            await seed_syllabus(db)
        except Exception as e:
            logger.error(f"Error seeding syllabus: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
