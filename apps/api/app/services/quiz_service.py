"""
Quiz Evaluation Service
Track and analyze quiz performance with detailed analytics.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging
import uuid

from app.models.quiz import (
    Quiz, QuizQuestion, QuizAttempt, QuestionAnswer,
    QuizStatus, AttemptStatus
)

logger = logging.getLogger(__name__)


@dataclass
class TopicPerformance:
    """Performance metrics for a single topic"""
    topic_id: str
    topic_name: str
    total_questions: int
    correct_answers: int
    wrong_answers: int
    accuracy: float
    avg_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "topic_name": self.topic_name,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "wrong_answers": self.wrong_answers,
            "accuracy": round(self.accuracy, 2),
            "avg_time_seconds": round(self.avg_time_seconds, 2),
        }


@dataclass
class QuizResult:
    """Complete result of a quiz attempt"""
    attempt_id: str
    quiz_id: str
    quiz_title: str
    score_percentage: float
    passed: bool
    total_questions: int
    correct_answers: int
    wrong_answers: int
    skipped: int
    time_spent_seconds: int
    topic_performance: List[TopicPerformance]
    question_results: List[Dict[str, Any]]
    improvement_areas: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "quiz_id": self.quiz_id,
            "quiz_title": self.quiz_title,
            "score_percentage": round(self.score_percentage, 2),
            "passed": self.passed,
            "total_questions": self.total_questions,
            "correct_answers": self.correct_answers,
            "wrong_answers": self.wrong_answers,
            "skipped": self.skipped,
            "time_spent_seconds": self.time_spent_seconds,
            "topic_performance": [tp.to_dict() for tp in self.topic_performance],
            "question_results": self.question_results,
            "improvement_areas": self.improvement_areas,
        }


@dataclass
class UserAnalytics:
    """Overall user performance analytics"""
    user_id: str
    total_quizzes_attempted: int
    total_questions_answered: int
    overall_accuracy: float
    average_time_per_question: float
    quizzes_passed: int
    quizzes_failed: int
    pass_rate: float
    topic_performance: List[TopicPerformance]
    difficulty_performance: Dict[str, float]
    recent_trend: str  # improving, stable, declining
    streak_days: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "total_quizzes_attempted": self.total_quizzes_attempted,
            "total_questions_answered": self.total_questions_answered,
            "overall_accuracy": round(self.overall_accuracy, 2),
            "average_time_per_question": round(self.average_time_per_question, 2),
            "quizzes_passed": self.quizzes_passed,
            "quizzes_failed": self.quizzes_failed,
            "pass_rate": round(self.pass_rate, 2),
            "topic_performance": [tp.to_dict() for tp in self.topic_performance],
            "difficulty_performance": self.difficulty_performance,
            "recent_trend": self.recent_trend,
            "streak_days": self.streak_days,
        }


class QuizService:
    """
    Quiz CRUD operations service.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Quiz CRUD ====================
    
    async def create_quiz(
        self,
        title: str,
        created_by: str,
        questions: List[Dict[str, Any]],
        description: Optional[str] = None,
        difficulty: str = "medium",
        time_limit_minutes: Optional[int] = None,
        passing_score: int = 60,
        topic_ids: Optional[List[str]] = None,
        is_ai_generated: bool = False,
        source_content: Optional[str] = None,
    ) -> Quiz:
        """Create a new quiz with questions"""
        quiz = Quiz(
            title=title,
            description=description,
            difficulty=difficulty,
            time_limit_minutes=time_limit_minutes,
            passing_score=passing_score,
            status=QuizStatus.DRAFT.value,
            is_ai_generated=is_ai_generated,
            source_content=source_content,
            question_count=len(questions),
            created_by=created_by,
        )
        
        self.db.add(quiz)
        await self.db.flush()
        
        # Add questions
        for i, q_data in enumerate(questions):
            question = QuizQuestion(
                quiz_id=quiz.id,
                question_text=q_data["question_text"],
                question_number=i + 1,
                options=q_data["options"],
                correct_option=q_data["correct_option"],
                explanation=q_data.get("explanation", ""),
                difficulty=q_data.get("difficulty", difficulty),
                topic_id=q_data.get("topic_id"),
                topic_name=q_data.get("topic_name"),
                source_chunk_id=q_data.get("source_chunk_id"),
                confidence_score=q_data.get("confidence_score"),
            )
            self.db.add(question)
        
        await self.db.flush()
        await self.db.flush()
        
        # Reload quiz with questions
        result = await self.db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .where(Quiz.id == quiz.id)
        )
        quiz = result.scalar_one()
        
        return quiz
    
    async def get_quiz(self, quiz_id: str) -> Optional[Quiz]:
        """Get quiz by ID with questions"""
        result = await self.db.execute(
            select(Quiz)
            .options(selectinload(Quiz.questions))
            .where(Quiz.id == quiz_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_quizzes(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Quiz], int]:
        """Get quizzes created by or accessible to user"""
        count_result = await self.db.execute(
            select(func.count(Quiz.id))
            .where(or_(
                Quiz.created_by == user_id,
                Quiz.status == QuizStatus.PUBLISHED.value
            ))
        )
        total = count_result.scalar() or 0
        
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(Quiz)
            .where(or_(
                Quiz.created_by == user_id,
                Quiz.status == QuizStatus.PUBLISHED.value
            ))
            .order_by(Quiz.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        
        return items, total
    
    async def publish_quiz(self, quiz_id: str) -> Optional[Quiz]:
        """Publish a quiz"""
        quiz = await self.get_quiz(quiz_id)
        if quiz:
            quiz.status = QuizStatus.PUBLISHED.value
            await self.db.flush()
        return quiz
    
    async def delete_quiz(self, quiz_id: str) -> bool:
        """Delete a quiz"""
        quiz = await self.get_quiz(quiz_id)
        if quiz:
            await self.db.delete(quiz)
            await self.db.flush()
            return True
        return False


class QuizEvaluator:
    """
    Quiz Evaluation Service.
    
    Tracks:
    - Accuracy per question and overall
    - Time spent per question
    - Topic-wise performance
    - Historical attempt data
    - Performance trends
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Attempt Management ====================
    
    async def start_attempt(
        self,
        quiz_id: str,
        user_id: str,
    ) -> QuizAttempt:
        """Start a new quiz attempt"""
        # Get quiz
        quiz_result = await self.db.execute(
            select(Quiz).where(Quiz.id == quiz_id)
        )
        quiz = quiz_result.scalar_one_or_none()
        
        if not quiz:
            raise ValueError("Quiz not found")
        
        # Count previous attempts
        count_result = await self.db.execute(
            select(func.count(QuizAttempt.id))
            .where(and_(
                QuizAttempt.quiz_id == quiz_id,
                QuizAttempt.user_id == user_id
            ))
        )
        attempt_number = (count_result.scalar() or 0) + 1
        
        # Create attempt
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            attempt_number=attempt_number,
            status=AttemptStatus.IN_PROGRESS.value,
            total_questions=quiz.question_count,
        )
        
        self.db.add(attempt)
        await self.db.flush()
        await self.db.refresh(attempt)
        
        return attempt
    
    async def submit_answer(
        self,
        attempt_id: str,
        question_id: str,
        selected_option: Optional[int],  # None if skipped
        time_spent_seconds: int,
    ) -> QuestionAnswer:
        """Submit an answer for a question"""
        # Get question
        q_result = await self.db.execute(
            select(QuizQuestion).where(QuizQuestion.id == question_id)
        )
        question = q_result.scalar_one_or_none()
        
        if not question:
            raise ValueError("Question not found")
        
        # Check if answer already exists
        existing_result = await self.db.execute(
            select(QuestionAnswer)
            .where(and_(
                QuestionAnswer.attempt_id == attempt_id,
                QuestionAnswer.question_id == question_id
            ))
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            # Update existing answer
            existing.selected_option = selected_option
            existing.is_correct = selected_option == question.correct_option if selected_option is not None else None
            existing.time_spent_seconds = time_spent_seconds
            existing.answered_at = datetime.now(timezone.utc)
            answer = existing
        else:
            # Create new answer
            answer = QuestionAnswer(
                attempt_id=attempt_id,
                question_id=question_id,
                selected_option=selected_option,
                is_correct=selected_option == question.correct_option if selected_option is not None else None,
                time_spent_seconds=time_spent_seconds,
                answered_at=datetime.now(timezone.utc),
            )
            self.db.add(answer)
        
        # Update question statistics
        question.times_answered += 1
        if answer.is_correct:
            question.times_correct += 1
        
        await self.db.flush()
        return answer
    
    async def complete_attempt(
        self,
        attempt_id: str,
    ) -> QuizResult:
        """Complete a quiz attempt and calculate results"""
        # Get attempt with answers
        attempt_result = await self.db.execute(
            select(QuizAttempt)
            .options(
                selectinload(QuizAttempt.answers).selectinload(QuestionAnswer.question),
                selectinload(QuizAttempt.quiz).selectinload(Quiz.questions)
            )
            .where(QuizAttempt.id == attempt_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Attempt not found")
        
        # Calculate results
        correct = 0
        wrong = 0
        skipped = 0
        total_time = 0
        topic_stats: Dict[str, Dict[str, Any]] = {}
        question_results = []
        
        for answer in attempt.answers:
            q = answer.question
            
            # Count correct/wrong/skipped
            if answer.selected_option is None:
                skipped += 1
            elif answer.is_correct:
                correct += 1
            else:
                wrong += 1
            
            total_time += answer.time_spent_seconds or 0
            
            # Track topic performance
            topic_key = q.topic_id or "general"
            topic_name = q.topic_name or "General"
            
            if topic_key not in topic_stats:
                topic_stats[topic_key] = {
                    "name": topic_name,
                    "correct": 0,
                    "wrong": 0,
                    "total": 0,
                    "time": 0,
                }
            
            topic_stats[topic_key]["total"] += 1
            topic_stats[topic_key]["time"] += answer.time_spent_seconds or 0
            
            if answer.is_correct:
                topic_stats[topic_key]["correct"] += 1
            elif answer.selected_option is not None:
                topic_stats[topic_key]["wrong"] += 1
            
            # Question result
            question_results.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "selected_option": answer.selected_option,
                "correct_option": q.correct_option,
                "is_correct": answer.is_correct,
                "time_spent": answer.time_spent_seconds,
                "explanation": q.explanation,
                "topic_name": q.topic_name,
            })
        
        # Update attempt
        attempt.status = AttemptStatus.COMPLETED.value
        attempt.completed_at = datetime.now(timezone.utc)
        attempt.time_spent_seconds = total_time
        attempt.answered_questions = len(attempt.answers)
        attempt.correct_answers = correct
        attempt.wrong_answers = wrong
        attempt.skipped_questions = skipped
        attempt.score_percentage = (correct / attempt.total_questions * 100) if attempt.total_questions > 0 else 0
        attempt.passed = attempt.score_percentage >= attempt.quiz.passing_score
        
        # Store topic performance
        attempt.topic_performance = {
            tid: {"correct": stats["correct"], "total": stats["total"]}
            for tid, stats in topic_stats.items()
        }
        
        # Update quiz stats
        attempt.quiz.total_attempts += 1
        
        await self.db.flush()
        
        # Build topic performance objects
        topic_perf = [
            TopicPerformance(
                topic_id=tid,
                topic_name=stats["name"],
                total_questions=stats["total"],
                correct_answers=stats["correct"],
                wrong_answers=stats["wrong"],
                accuracy=(stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                avg_time_seconds=stats["time"] / stats["total"] if stats["total"] > 0 else 0,
            )
            for tid, stats in topic_stats.items()
        ]
        
        # Identify improvement areas
        improvement_areas = [
            tp.topic_name for tp in topic_perf 
            if tp.accuracy < 50 and tp.total_questions >= 2
        ]
        
        return QuizResult(
            attempt_id=attempt_id,
            quiz_id=attempt.quiz_id,
            quiz_title=attempt.quiz.title,
            score_percentage=attempt.score_percentage,
            passed=attempt.passed,
            total_questions=attempt.total_questions,
            correct_answers=correct,
            wrong_answers=wrong,
            skipped=skipped,
            time_spent_seconds=total_time,
            topic_performance=topic_perf,
            question_results=question_results,
            improvement_areas=improvement_areas,
        )

    async def get_attempt_result(self, attempt_id: str) -> QuizResult:
        """Get result of a completed attempt"""
        # Get attempt with answers
        attempt_result = await self.db.execute(
            select(QuizAttempt)
            .options(
                selectinload(QuizAttempt.answers).selectinload(QuestionAnswer.question),
                selectinload(QuizAttempt.quiz).selectinload(Quiz.questions)
            )
            .where(QuizAttempt.id == attempt_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Attempt not found")
        
        # Re-construct results similar to complete_attempt
        # (Logic duplicated for safety, ideal refactor would share this)
        topic_stats: Dict[str, Dict[str, Any]] = {}
        question_results = []
        
        for answer in attempt.answers:
            q = answer.question
            
            # Track topic performance
            topic_key = q.topic_id or "general"
            topic_name = q.topic_name or "General"
            
            if topic_key not in topic_stats:
                topic_stats[topic_key] = {
                    "name": topic_name,
                    "correct": 0,
                    "total": 0,
                    "time": 0,
                }
            
            topic_stats[topic_key]["total"] += 1
            topic_stats[topic_key]["time"] += answer.time_spent_seconds or 0
            
            if answer.is_correct:
                topic_stats[topic_key]["correct"] += 1
            
            # Question result
            question_results.append({
                "question_id": q.id,
                "question_text": q.question_text,
                "options": q.options,
                "selected_option": answer.selected_option,
                "correct_option": q.correct_option,
                "is_correct": answer.is_correct if answer.is_correct is not None else False,
                "time_spent": answer.time_spent_seconds,
                "explanation": q.explanation,
                "topic_name": q.topic_name,
            })
        
        # Build topic performance objects
        topic_perf = [
            TopicPerformance(
                topic_id=tid,
                topic_name=stats["name"],
                total_questions=stats["total"],
                correct_answers=stats["correct"],
                wrong_answers=stats["total"] - stats["correct"],
                accuracy=(stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                avg_time_seconds=stats["time"] / stats["total"] if stats["total"] > 0 else 0,
            )
            for tid, stats in topic_stats.items()
        ]
        
        # Identify improvement areas
        improvement_areas = [
            tp.topic_name for tp in topic_perf 
            if tp.accuracy < 50 and tp.total_questions >= 2
        ]
        
        return QuizResult(
            attempt_id=attempt_id,
            quiz_id=attempt.quiz_id,
            quiz_title=attempt.quiz.title,
            score_percentage=attempt.score_percentage or 0.0,
            passed=attempt.passed or False,
            total_questions=attempt.total_questions,
            correct_answers=attempt.correct_answers or 0,
            wrong_answers=attempt.wrong_answers or 0,
            skipped=attempt.skipped_questions or 0,
            time_spent_seconds=attempt.time_spent_seconds or 0,
            topic_performance=topic_perf,
            question_results=question_results,
            improvement_areas=improvement_areas,
        )
    
    # ==================== Analytics ====================
    
    async def get_user_analytics(
        self,
        user_id: str,
        days: int = 30,
    ) -> UserAnalytics:
        """Get comprehensive user analytics"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get completed attempts
        attempts_result = await self.db.execute(
            select(QuizAttempt)
            .options(selectinload(QuizAttempt.answers).selectinload(QuestionAnswer.question))
            .where(and_(
                QuizAttempt.user_id == user_id,
                QuizAttempt.status == AttemptStatus.COMPLETED.value,
                QuizAttempt.completed_at >= since
            ))
            .order_by(QuizAttempt.completed_at.desc())
        )
        attempts = list(attempts_result.scalars().all())
        
        if not attempts:
            return UserAnalytics(
                user_id=user_id,
                total_quizzes_attempted=0,
                total_questions_answered=0,
                overall_accuracy=0.0,
                average_time_per_question=0.0,
                quizzes_passed=0,
                quizzes_failed=0,
                pass_rate=0.0,
                topic_performance=[],
                difficulty_performance={},
                recent_trend="stable",
                streak_days=0,
            )
        
        # Calculate metrics
        total_correct = sum(a.correct_answers for a in attempts)
        total_questions = sum(a.total_questions for a in attempts)
        total_time = sum(a.time_spent_seconds or 0 for a in attempts)
        passed = sum(1 for a in attempts if a.passed)
        failed = len(attempts) - passed
        
        # Topic performance aggregation
        topic_stats: Dict[str, Dict[str, Any]] = {}
        difficulty_stats: Dict[str, Dict[str, int]] = {}
        
        for attempt in attempts:
            for answer in attempt.answers:
                q = answer.question
                
                # Topic stats
                topic_key = q.topic_id or "general"
                if topic_key not in topic_stats:
                    topic_stats[topic_key] = {
                        "name": q.topic_name or "General",
                        "correct": 0,
                        "wrong": 0,
                        "total": 0,
                        "time": 0,
                    }
                
                topic_stats[topic_key]["total"] += 1
                topic_stats[topic_key]["time"] += answer.time_spent_seconds or 0
                if answer.is_correct:
                    topic_stats[topic_key]["correct"] += 1
                elif answer.selected_option is not None:
                    topic_stats[topic_key]["wrong"] += 1
                
                # Difficulty stats
                diff = q.difficulty or "medium"
                if diff not in difficulty_stats:
                    difficulty_stats[diff] = {"correct": 0, "total": 0}
                difficulty_stats[diff]["total"] += 1
                if answer.is_correct:
                    difficulty_stats[diff]["correct"] += 1
        
        # Build topic performance
        topic_perf = [
            TopicPerformance(
                topic_id=tid,
                topic_name=stats["name"],
                total_questions=stats["total"],
                correct_answers=stats["correct"],
                wrong_answers=stats["wrong"],
                accuracy=(stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                avg_time_seconds=stats["time"] / stats["total"] if stats["total"] > 0 else 0,
            )
            for tid, stats in topic_stats.items()
        ]
        
        # Difficulty performance
        diff_perf = {
            k: (v["correct"] / v["total"] * 100) if v["total"] > 0 else 0
            for k, v in difficulty_stats.items()
        }
        
        # Calculate trend
        trend = self._calculate_trend(attempts)
        
        # Calculate streak
        streak = self._calculate_streak(attempts)
        
        return UserAnalytics(
            user_id=user_id,
            total_quizzes_attempted=len(attempts),
            total_questions_answered=total_questions,
            overall_accuracy=(total_correct / total_questions * 100) if total_questions > 0 else 0,
            average_time_per_question=total_time / total_questions if total_questions > 0 else 0,
            quizzes_passed=passed,
            quizzes_failed=failed,
            pass_rate=(passed / len(attempts) * 100) if attempts else 0,
            topic_performance=topic_perf,
            difficulty_performance=diff_perf,
            recent_trend=trend,
            streak_days=streak,
        )
    
    async def get_attempt_history(
        self,
        user_id: str,
        quiz_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[QuizAttempt], int]:
        """Get user's attempt history"""
        query = select(QuizAttempt).where(QuizAttempt.user_id == user_id)
        
        if quiz_id:
            query = query.where(QuizAttempt.quiz_id == quiz_id)
        
        # Count
        count_query = select(func.count(QuizAttempt.id)).where(QuizAttempt.user_id == user_id)
        if quiz_id:
            count_query = count_query.where(QuizAttempt.quiz_id == quiz_id)
        
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        # Get data
        offset = (page - 1) * limit
        result = await self.db.execute(
            query
            .options(selectinload(QuizAttempt.quiz))
            .order_by(QuizAttempt.completed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        
        return items, total
    
    def _calculate_trend(self, attempts: List[QuizAttempt]) -> str:
        """Calculate performance trend based on recent attempts"""
        if len(attempts) < 3:
            return "stable"
        
        recent_3 = attempts[:3]
        older_3 = attempts[3:6] if len(attempts) >= 6 else attempts[3:]
        
        if not older_3:
            return "stable"
        
        recent_avg = sum(a.score_percentage or 0 for a in recent_3) / len(recent_3)
        older_avg = sum(a.score_percentage or 0 for a in older_3) / len(older_3)
        
        diff = recent_avg - older_avg
        
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_streak(self, attempts: List[QuizAttempt]) -> int:
        """Calculate current streak of days with quiz activity"""
        if not attempts:
            return 0
        
        dates = set()
        for a in attempts:
            if a.completed_at:
                dates.add(a.completed_at.date())
        
        if not dates:
            return 0
        
        sorted_dates = sorted(dates, reverse=True)
        today = datetime.now(timezone.utc).date()
        
        if sorted_dates[0] < today - timedelta(days=1):
            return 0
        
        streak = 1
        for i in range(1, len(sorted_dates)):
            if sorted_dates[i] == sorted_dates[i-1] - timedelta(days=1):
                streak += 1
            else:
                break
        
        return streak
