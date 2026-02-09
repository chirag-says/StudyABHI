"""
Dynamic Roadmap Service
Generates and manages personalized study plans for UPSC preparation.
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging
import random

from app.models.roadmap import (
    UserStudyPlan, StudyPhase, DailyStudyTask, WeeklyPlan,
    PreparationLevel, StudyPreference, TaskStatus, TaskType
)
from app.models.learning import DailyProgress, TopicProficiency
from app.models.syllabus import Topic, Subject
from app.services.upsc_syllabus_data import UPSC_SYLLABUS, STUDY_PHASES, RECOMMENDED_BOOKS

logger = logging.getLogger(__name__)


class RoadmapService:
    """Service for managing dynamic study roadmaps"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Study Plan Management ====================
    
    async def create_study_plan(
        self,
        user_id: str,
        target_exam_year: int,
        preparation_level: str = "beginner",
        study_preference: str = "moderate",
        daily_study_hours: float = 6.0,
        optional_subject: Optional[str] = None,
        is_working: bool = False,
        preferred_study_time: str = "morning",
        medium: str = "english"
    ) -> UserStudyPlan:
        """Create a new personalized study plan"""
        
        # Calculate dates
        today = date.today()
        
        # Estimate prelims date (usually June of target year)
        target_prelims = date(target_exam_year, 6, 1)
        target_mains = date(target_exam_year, 9, 15)
        
        # Create the study plan
        study_plan = UserStudyPlan(
            user_id=user_id,
            target_exam_year=target_exam_year,
            optional_subject=optional_subject,
            preparation_level=preparation_level,
            study_preference=study_preference,
            daily_study_hours=daily_study_hours,
            preferred_study_time=preferred_study_time,
            is_working=is_working,
            medium=medium,
            plan_start_date=today,
            target_prelims_date=target_prelims,
            target_mains_date=target_mains,
            onboarding_completed=True
        )
        
        self.db.add(study_plan)
        await self.db.flush()
        
        # Create study phases based on time available
        await self._create_study_phases(study_plan)
        
        # Generate initial week's tasks
        await self.generate_weekly_tasks(user_id, study_plan.id)
        
        await self.db.commit()
        await self.db.refresh(study_plan)
        
        return study_plan
    
    async def _create_study_phases(self, study_plan: UserStudyPlan):
        """Create study phases based on available time until exam"""
        
        today = date.today()
        prelims_date = study_plan.target_prelims_date
        
        if not prelims_date:
            prelims_date = date(study_plan.target_exam_year, 6, 1)
        
        # Calculate weeks available
        days_available = (prelims_date - today).days
        weeks_available = days_available // 7
        
        # Adjust phase durations based on preparation level
        level_adjustments = {
            "beginner": {"foundation": 1.5, "prelims": 1.2, "revision": 0.8},
            "foundation": {"foundation": 1.0, "prelims": 1.3, "revision": 1.0},
            "intermediate": {"foundation": 0.5, "prelims": 1.3, "revision": 1.2},
            "advanced": {"foundation": 0.3, "prelims": 1.0, "revision": 1.5}
        }
        adj = level_adjustments.get(study_plan.preparation_level, level_adjustments["beginner"])
        
        # Calculate phase durations
        if weeks_available > 40:
            # Long preparation period
            foundation_weeks = int(12 * adj["foundation"])
            prelims_weeks = int(16 * adj["prelims"])
            revision_weeks = int(8 * adj["revision"])
        elif weeks_available > 25:
            # Medium preparation
            foundation_weeks = int(8 * adj["foundation"])
            prelims_weeks = int(12 * adj["prelims"])
            revision_weeks = int(6 * adj["revision"])
        else:
            # Short preparation
            foundation_weeks = int(4 * adj["foundation"])
            prelims_weeks = int(weeks_available - 6)
            revision_weeks = 4
        
        # Ensure we don't exceed available time
        total_weeks = foundation_weeks + prelims_weeks + revision_weeks
        if total_weeks > weeks_available:
            ratio = weeks_available / total_weeks
            foundation_weeks = max(2, int(foundation_weeks * ratio))
            prelims_weeks = max(4, int(prelims_weeks * ratio))
            revision_weeks = max(2, weeks_available - foundation_weeks - prelims_weeks)
        
        # Create phases
        phases_config = [
            {
                "name": "Foundation Building",
                "description": "Build strong foundation with NCERTs and basic books. Focus on understanding concepts.",
                "duration_weeks": foundation_weeks,
                "focus_subjects": ["polity", "history", "geography", "economy"],
                "order": 1
            },
            {
                "name": "Prelims Preparation",
                "description": "Cover entire prelims syllabus with focus on MCQ practice and current affairs.",
                "duration_weeks": prelims_weeks,
                "focus_subjects": ["polity", "history", "geography", "economy", "science-tech", "environment"],
                "order": 2
            },
            {
                "name": "Revision & Mock Tests",
                "description": "Intensive revision, PYQ practice, and full-length mock tests.",
                "duration_weeks": revision_weeks,
                "focus_subjects": ["all"],
                "order": 3
            }
        ]
        
        current_date = today
        
        for config in phases_config:
            if config["duration_weeks"] <= 0:
                continue
            
            end_date = current_date + timedelta(weeks=config["duration_weeks"])
            
            # Calculate targets based on daily hours
            daily_hours = study_plan.daily_study_hours
            total_hours = daily_hours * config["duration_weeks"] * 7 * 0.8  # 80% efficiency
            target_topics = int(total_hours / 3)  # Avg 3 hours per topic
            
            phase = StudyPhase(
                study_plan_id=study_plan.id,
                name=config["name"],
                description=config["description"],
                order=config["order"],
                start_date=current_date,
                end_date=end_date,
                duration_weeks=config["duration_weeks"],
                focus_subjects=config["focus_subjects"],
                target_topics=target_topics,
                target_study_hours=total_hours,
                target_quizzes=config["duration_weeks"] * 3,
                is_active=(config["order"] == 1)
            )
            
            self.db.add(phase)
            
            # Set first phase as current
            if config["order"] == 1:
                await self.db.flush()
                study_plan.current_phase_id = phase.id
            
            current_date = end_date
    
    # ==================== Daily Task Generation ====================
    
    async def generate_daily_tasks(
        self,
        user_id: str,
        target_date: date = None
    ) -> List[DailyStudyTask]:
        """Generate study tasks for a specific day"""
        
        if target_date is None:
            target_date = date.today()
        
        # Get user's study plan
        result = await self.db.execute(
            select(UserStudyPlan)
            .options(selectinload(UserStudyPlan.current_phase))
            .where(UserStudyPlan.user_id == user_id)
            .where(UserStudyPlan.is_active == True)
        )
        study_plan = result.scalar_one_or_none()
        
        if not study_plan:
            return []
        
        # Check if tasks already exist for this date
        existing_result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.scheduled_date == target_date)
        )
        existing_tasks = list(existing_result.scalars().all())
        
        if existing_tasks:
            return existing_tasks
        
        # Get current phase for focus areas
        current_phase = study_plan.current_phase
        focus_subjects = current_phase.focus_subjects if current_phase else ["polity", "history", "geography"]
        
        # Calculate available study slots based on preferences
        daily_hours = study_plan.daily_study_hours
        tasks = []
        
        # Time allocation based on day and phase
        is_weekend = target_date.weekday() >= 5
        
        if is_weekend:
            # More time on weekends
            study_minutes = int(daily_hours * 60 * 1.2)
        else:
            study_minutes = int(daily_hours * 60)
        
        # Split time into activities
        # Primary study: 50%, Revision: 20%, Quiz: 15%, Current Affairs: 15%
        primary_study_minutes = int(study_minutes * 0.50)
        revision_minutes = int(study_minutes * 0.20)
        quiz_minutes = int(study_minutes * 0.15)
        ca_minutes = int(study_minutes * 0.15)
        
        # Get topics to study today
        suggested_topics = await self._get_suggested_topics(
            user_id, focus_subjects, 3
        )
        
        # Get topics due for revision
        revision_topics = await self._get_revision_topics(user_id, 2)
        
        # Create primary study tasks
        time_per_topic = primary_study_minutes // max(len(suggested_topics), 1)
        for i, topic_info in enumerate(suggested_topics):
            task = DailyStudyTask(
                study_plan_id=study_plan.id,
                user_id=user_id,
                title=f"Study: {topic_info['name']}",
                description=f"Study {topic_info['name']} from {topic_info.get('subject', 'General Studies')}",
                task_type=TaskType.STUDY.value,
                scheduled_date=target_date,
                scheduled_time_slot="morning" if i == 0 else "afternoon" if i == 1 else "evening",
                estimated_minutes=time_per_topic,
                priority=8 - i,
                topic_id=topic_info.get('id'),
                topic_name=topic_info['name'],
                subject_name=topic_info.get('subject'),
                resources=[{
                    "type": "book",
                    "name": topic_info.get('book', 'Standard Book')
                }]
            )
            tasks.append(task)
            self.db.add(task)
        
        # Create revision tasks
        for i, rev_topic in enumerate(revision_topics):
            task = DailyStudyTask(
                study_plan_id=study_plan.id,
                user_id=user_id,
                title=f"Revise: {rev_topic['name']}",
                description=f"Revision of {rev_topic['name']}",
                task_type=TaskType.REVISION.value,
                scheduled_date=target_date,
                scheduled_time_slot="evening",
                estimated_minutes=revision_minutes // max(len(revision_topics), 1),
                priority=7,
                topic_id=rev_topic.get('id'),
                topic_name=rev_topic['name'],
                is_revision=True,
                revision_number=rev_topic.get('revision_number', 1)
            )
            tasks.append(task)
            self.db.add(task)
        
        # Quiz task
        quiz_subject = random.choice(focus_subjects) if focus_subjects else "polity"
        quiz_task = DailyStudyTask(
            study_plan_id=study_plan.id,
            user_id=user_id,
            title=f"Daily Quiz: {quiz_subject.replace('-', ' ').title()}",
            description="Practice MCQs to reinforce learning",
            task_type=TaskType.QUIZ.value,
            scheduled_date=target_date,
            scheduled_time_slot="afternoon",
            estimated_minutes=quiz_minutes,
            priority=6,
            subject_name=quiz_subject
        )
        tasks.append(quiz_task)
        self.db.add(quiz_task)
        
        # Current Affairs task
        if study_plan.include_current_affairs:
            ca_task = DailyStudyTask(
                study_plan_id=study_plan.id,
                user_id=user_id,
                title="Daily Current Affairs",
                description="Read and make notes on today's important news",
                task_type=TaskType.CURRENT_AFFAIRS.value,
                scheduled_date=target_date,
                scheduled_time_slot="morning",
                estimated_minutes=ca_minutes,
                priority=7,
                is_mandatory=True
            )
            tasks.append(ca_task)
            self.db.add(ca_task)
        
        await self.db.commit()
        
        return tasks
    
    async def _get_suggested_topics(
        self,
        user_id: str,
        focus_subjects: List[str],
        count: int = 3
    ) -> List[Dict]:
        """Get topics to study based on progress and priority"""
        
        # Get topics user hasn't mastered yet
        result = await self.db.execute(
            select(TopicProficiency)
            .options(selectinload(TopicProficiency.topic))
            .where(TopicProficiency.user_id == user_id)
            .where(TopicProficiency.is_mastered == False)
            .order_by(TopicProficiency.proficiency_score.asc())
            .limit(10)
        )
        weak_topics = list(result.scalars().all())
        
        topics = []
        
        # Add weak topics first
        for prof in weak_topics[:count-1]:
            if prof.topic:
                topics.append({
                    "id": prof.topic_id,
                    "name": prof.topic.name,
                    "subject": prof.topic.subject.name if prof.topic.subject else "General Studies",
                    "proficiency": prof.proficiency_score
                })
        
        # Add new topic suggestions based on syllabus
        # Get from syllabus data structure
        syllabus_topics = self._get_syllabus_topics(focus_subjects)
        for topic in syllabus_topics:
            if len(topics) >= count:
                break
            if not any(t.get('name') == topic['name'] for t in topics):
                topics.append(topic)
        
        return topics[:count]
    
    def _get_syllabus_topics(self, focus_subjects: List[str]) -> List[Dict]:
        """Get topics from syllabus based on focus subjects"""
        topics = []
        
        for stage in UPSC_SYLLABUS["stages"]:
            for paper in stage["papers"]:
                for subject in paper["subjects"]:
                    if "all" in focus_subjects or subject["code"] in focus_subjects:
                        for topic in subject.get("topics", []):
                            topics.append({
                                "name": topic["name"],
                                "subject": subject["name"],
                                "importance": topic.get("importance", "medium"),
                                "estimated_hours": topic.get("estimated_hours", 5),
                                "book": RECOMMENDED_BOOKS.get(
                                    subject["code"], [{"name": "Standard Book"}]
                                )[0]["name"]
                            })
        
        # Sort by importance
        importance_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        topics.sort(key=lambda x: importance_order.get(x.get("importance", "medium"), 2))
        
        return topics
    
    async def _get_revision_topics(
        self,
        user_id: str,
        count: int = 2
    ) -> List[Dict]:
        """Get topics due for revision based on spaced repetition"""
        
        today = date.today()
        
        result = await self.db.execute(
            select(TopicProficiency)
            .options(selectinload(TopicProficiency.topic))
            .where(TopicProficiency.user_id == user_id)
            .where(TopicProficiency.needs_revision == True)
            .where(
                or_(
                    TopicProficiency.next_revision_date <= today,
                    TopicProficiency.next_revision_date.is_(None)
                )
            )
            .order_by(TopicProficiency.last_revised.asc().nullslast())
            .limit(count)
        )
        due_topics = list(result.scalars().all())
        
        topics = []
        for prof in due_topics:
            if prof.topic:
                topics.append({
                    "id": prof.topic_id,
                    "name": prof.topic.name,
                    "revision_number": prof.revision_count + 1,
                    "last_studied": prof.last_studied.isoformat() if prof.last_studied else None
                })
        
        return topics
    
    # ==================== Weekly Planning ====================
    
    async def generate_weekly_tasks(
        self,
        user_id: str,
        study_plan_id: str
    ):
        """Generate tasks for the entire week"""
        
        today = date.today()
        
        # Generate tasks for the next 7 days
        for i in range(7):
            target_date = today + timedelta(days=i)
            await self.generate_daily_tasks(user_id, target_date)
    
    async def get_weekly_plan(
        self,
        user_id: str,
        week_start: date = None
    ) -> Optional[WeeklyPlan]:
        """Get or create weekly plan"""
        
        if week_start is None:
            today = date.today()
            # Get Monday of current week
            week_start = today - timedelta(days=today.weekday())
        
        week_end = week_start + timedelta(days=6)
        year, week_number, _ = week_start.isocalendar()
        
        result = await self.db.execute(
            select(WeeklyPlan)
            .where(WeeklyPlan.user_id == user_id)
            .where(WeeklyPlan.year == year)
            .where(WeeklyPlan.week_number == week_number)
        )
        weekly_plan = result.scalar_one_or_none()
        
        if not weekly_plan:
            # Get study plan
            plan_result = await self.db.execute(
                select(UserStudyPlan)
                .where(UserStudyPlan.user_id == user_id)
                .where(UserStudyPlan.is_active == True)
            )
            study_plan = plan_result.scalar_one_or_none()
            
            if study_plan:
                weekly_plan = WeeklyPlan(
                    user_id=user_id,
                    study_plan_id=study_plan.id,
                    week_number=week_number,
                    year=year,
                    start_date=week_start,
                    end_date=week_end,
                    target_study_hours=study_plan.daily_study_hours * 7,
                    target_quizzes=7,
                    is_current=True
                )
                self.db.add(weekly_plan)
                await self.db.commit()
                await self.db.refresh(weekly_plan)
        
        return weekly_plan
    
    # ==================== Task Management ====================
    
    async def update_task_status(
        self,
        task_id: str,
        user_id: str,
        status: str,
        actual_minutes: Optional[int] = None,
        difficulty_rating: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[DailyStudyTask]:
        """Update task status and optionally record time/feedback"""
        
        result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.id == task_id)
            .where(DailyStudyTask.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS.value:
            task.started_at = datetime.now(timezone.utc)
        elif status == TaskStatus.COMPLETED.value:
            task.completed_at = datetime.now(timezone.utc)
            if actual_minutes:
                task.actual_minutes = actual_minutes
            elif not task.actual_minutes:
                task.actual_minutes = task.estimated_minutes
        
        if difficulty_rating:
            task.difficulty_rating = difficulty_rating
        
        if notes:
            task.notes = notes
        
        # Update topic proficiency if completed
        if status == TaskStatus.COMPLETED.value and task.topic_id:
            await self._update_topic_progress(
                user_id, 
                task.topic_id,
                task.actual_minutes or task.estimated_minutes,
                task.is_revision
            )
        
        await self.db.commit()
        await self.db.refresh(task)
        
        return task
    
    async def _update_topic_progress(
        self,
        user_id: str,
        topic_id: str,
        study_minutes: int,
        is_revision: bool = False
    ):
        """Update topic proficiency after completing a task"""
        
        result = await self.db.execute(
            select(TopicProficiency)
            .where(TopicProficiency.user_id == user_id)
            .where(TopicProficiency.topic_id == topic_id)
        )
        proficiency = result.scalar_one_or_none()
        
        if not proficiency:
            proficiency = TopicProficiency(
                user_id=user_id,
                topic_id=topic_id
            )
            self.db.add(proficiency)
        
        proficiency.total_study_minutes += study_minutes
        proficiency.last_studied = datetime.now(timezone.utc)
        
        if is_revision:
            proficiency.revision_count += 1
            proficiency.last_revised = datetime.now(timezone.utc)
            # Update next revision date using simple spaced repetition
            days_until_next = min(proficiency.revision_count * 7, 30)
            proficiency.next_revision_date = date.today() + timedelta(days=days_until_next)
            proficiency.needs_revision = False
        else:
            # First time studying - schedule revision
            proficiency.needs_revision = True
            proficiency.next_revision_date = date.today() + timedelta(days=1)
    
    # ==================== Roadmap Data ====================
    
    async def get_roadmap_data(self, user_id: str) -> Dict[str, Any]:
        """Get complete roadmap data for the user"""
        
        today = date.today()
        
        # Get study plan
        result = await self.db.execute(
            select(UserStudyPlan)
            .options(
                selectinload(UserStudyPlan.current_phase),
                selectinload(UserStudyPlan.phases)
            )
            .where(UserStudyPlan.user_id == user_id)
            .where(UserStudyPlan.is_active == True)
        )
        study_plan = result.scalar_one_or_none()
        
        if not study_plan:
            return {"has_plan": False}
        
        # Get today's tasks
        tasks_result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.scheduled_date == today)
            .order_by(DailyStudyTask.priority.desc())
        )
        today_tasks = list(tasks_result.scalars().all())
        
        # Generate if no tasks exist
        if not today_tasks:
            today_tasks = await self.generate_daily_tasks(user_id, today)
        
        # Get upcoming tasks (next 3 days)
        upcoming_result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.scheduled_date > today)
            .where(DailyStudyTask.scheduled_date <= today + timedelta(days=3))
            .order_by(DailyStudyTask.scheduled_date, DailyStudyTask.priority.desc())
            .limit(10)
        )
        upcoming_tasks = list(upcoming_result.scalars().all())
        
        # Get revision due
        revision_result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.is_revision == True)
            .where(DailyStudyTask.status == TaskStatus.PENDING.value)
            .where(DailyStudyTask.due_date <= today)
            .limit(5)
        )
        revision_due = list(revision_result.scalars().all())
        
        # Calculate stats
        week_ago = today - timedelta(days=7)
        completed_result = await self.db.execute(
            select(func.count(DailyStudyTask.id))
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.status == TaskStatus.COMPLETED.value)
            .where(DailyStudyTask.completed_at >= datetime.combine(week_ago, datetime.min.time()))
        )
        completed_this_week = completed_result.scalar() or 0
        
        # Get streak (simplified)
        streak = await self._calculate_streak(user_id)
        
        # Determine current phase info
        current_phase = study_plan.current_phase
        phases = sorted(study_plan.phases, key=lambda p: p.order)
        current_phase_index = next(
            (i for i, p in enumerate(phases) if p.id == current_phase.id),
            0
        ) if current_phase else 0
        
        return {
            "has_plan": True,
            "overall_progress": study_plan.overall_progress,
            "current_phase": current_phase_index + 1,
            "total_phases": len(phases),
            "phase_name": current_phase.name if current_phase else "Getting Started",
            "phase_progress": current_phase.progress_percentage if current_phase else 0,
            "today_tasks": [self._task_to_dict(t) for t in today_tasks],
            "upcoming_tasks": [self._task_to_dict(t) for t in upcoming_tasks],
            "revision_due": [self._task_to_dict(t) for t in revision_due],
            "completed_this_week": completed_this_week,
            "streak_days": streak,
            "target_exam_year": study_plan.target_exam_year,
            "days_to_prelims": (study_plan.target_prelims_date - today).days if study_plan.target_prelims_date else None,
            "daily_goal_hours": study_plan.daily_study_hours,
            "phases": [
                {
                    "name": p.name,
                    "start_date": p.start_date.isoformat(),
                    "end_date": p.end_date.isoformat(),
                    "progress": p.progress_percentage,
                    "is_active": p.is_active,
                    "is_completed": p.is_completed
                }
                for p in phases
            ]
        }
    
    def _task_to_dict(self, task: DailyStudyTask) -> Dict:
        """Convert task to dictionary"""
        return {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "estimated_minutes": task.estimated_minutes,
            "actual_minutes": task.actual_minutes,
            "topic_name": task.topic_name,
            "topic_id": task.topic_id,
            "subject_name": task.subject_name,
            "is_revision": task.is_revision,
            "scheduled_time_slot": task.scheduled_time_slot
        }
    
    async def _calculate_streak(self, user_id: str) -> int:
        """Calculate current study streak"""
        today = date.today()
        streak = 0
        check_date = today
        
        for _ in range(365):  # Max 1 year streak
            result = await self.db.execute(
                select(DailyStudyTask)
                .where(DailyStudyTask.user_id == user_id)
                .where(DailyStudyTask.scheduled_date == check_date)
                .where(DailyStudyTask.status == TaskStatus.COMPLETED.value)
                .limit(1)
            )
            completed = result.scalar_one_or_none()
            
            if completed:
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        return streak
    
    # ==================== Stats and Analytics ====================
    
    async def get_daily_stats(self, user_id: str, target_date: date = None) -> Dict:
        """Get daily study statistics"""
        
        if target_date is None:
            target_date = date.today()
        
        result = await self.db.execute(
            select(DailyStudyTask)
            .where(DailyStudyTask.user_id == user_id)
            .where(DailyStudyTask.scheduled_date == target_date)
        )
        tasks = list(result.scalars().all())
        
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED.value]
        total_minutes = sum(t.actual_minutes or t.estimated_minutes for t in completed)
        
        return {
            "date": target_date.isoformat(),
            "tasks_total": len(tasks),
            "tasks_completed": len(completed),
            "completion_rate": len(completed) / len(tasks) * 100 if tasks else 0,
            "study_minutes": total_minutes,
            "study_hours": round(total_minutes / 60, 1),
            "by_type": {
                task_type: len([t for t in completed if t.task_type == task_type])
                for task_type in [
                    TaskType.STUDY.value, TaskType.QUIZ.value, 
                    TaskType.REVISION.value, TaskType.CURRENT_AFFAIRS.value
                ]
            }
        }
