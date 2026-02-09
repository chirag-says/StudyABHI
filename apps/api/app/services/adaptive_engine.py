"""
Adaptive Learning Roadmap Engine
Rule-based system for personalized learning recommendations.

This engine analyzes user behavior and adjusts the learning path based on:
- Consistency patterns (reduce load if inconsistent)
- Topic accuracy (force revision if declining)
- Performance level (unlock content for high performers)
- Burnout prevention (detect overwork patterns)
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging

logger = logging.getLogger(__name__)


# ==================== Configuration Constants ====================

class AdaptiveConfig:
    """Configuration for adaptive learning rules"""
    
    # Consistency thresholds
    CONSISTENCY_HIGH = 80      # 80%+ days active = high consistency
    CONSISTENCY_MEDIUM = 50    # 50-80% = medium
    CONSISTENCY_LOW = 30       # Below 30% = low consistency
    
    # Burnout prevention
    MAX_DAILY_MINUTES = 240    # 4 hours max recommended
    BURNOUT_RISK_HIGH = 70     # Above 70 = high burnout risk
    CONSECUTIVE_HEAVY_DAYS = 5 # Reduce load after 5 heavy days
    
    # Topic revision triggers
    ACCURACY_DROP_THRESHOLD = 15   # 15% drop triggers revision
    WEAK_TOPIC_ACCURACY = 50       # Below 50% = weak topic
    REVISION_DUE_DAYS = 7          # Default revision interval
    
    # High performer thresholds
    HIGH_PERFORMER_ACCURACY = 80   # 80%+ overall
    HIGH_PERFORMER_CONSISTENCY = 70
    HIGH_PERFORMER_STREAK = 7      # 7+ day streak
    
    # Load levels (daily study minutes)
    LOAD_LIGHT = 30            # 30 minutes
    LOAD_NORMAL = 60           # 1 hour
    LOAD_MODERATE = 90         # 1.5 hours
    LOAD_INTENSIVE = 120       # 2 hours


@dataclass
class LearningRecommendation:
    """A single learning recommendation"""
    type: str                  # study, revision, break, quiz, milestone
    priority: int              # 1-10 (10 = highest)
    topic_id: Optional[str]
    topic_name: Optional[str]
    title: str
    reason: str
    estimated_minutes: int
    action_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DailyPlan:
    """Generated daily learning plan"""
    date: date
    user_id: str
    total_recommended_minutes: int
    load_level: str  # light, normal, moderate, intensive
    recommendations: List[LearningRecommendation]
    revision_topics: List[str]
    new_topics: List[str]
    warnings: List[str]
    motivational_message: str


@dataclass 
class AdaptiveAnalysis:
    """Result of adaptive analysis"""
    consistency_score: float
    burnout_risk: float
    engagement_score: float
    accuracy_trend: str
    weak_topics: List[str]
    topics_due_revision: List[str]
    recommended_load: str
    is_high_performer: bool
    needs_break: bool
    force_revision: bool


class AdaptiveLearningEngine:
    """
    Rule-based Adaptive Learning Roadmap Engine.
    
    Analyzes learning patterns and produces personalized recommendations.
    
    RULES:
    1. CONSISTENCY RULE: Reduce load if user shows inconsistency
       - If missed >3 days in last week → reduce to light load
       - If streak broken → lower expectations temporarily
    
    2. REVISION RULE: Force revision if topic accuracy drops
       - If accuracy drops >15% → add topic to revision queue
       - If accuracy <50% after 5+ attempts → mark as weak area
    
    3. PERFORMANCE RULE: Unlock content for high performers
       - If accuracy >80% AND consistency >70% → unlock bonus content
       - If streak >7 days → unlock achievement content
    
    4. BURNOUT PREVENTION: Detect and prevent overwork
       - If studying >4 hours/day for 5+ consecutive days → suggest break
       - If engagement dropping while time increasing → burnout risk
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.config = AdaptiveConfig()
    
    # ========== Main Analysis Methods ==========
    
    async def analyze_user(self, user_id: str, days: int = 14) -> AdaptiveAnalysis:
        """
        Perform comprehensive analysis of user's learning behavior.
        
        Args:
            user_id: User to analyze
            days: Number of past days to consider
            
        Returns:
            AdaptiveAnalysis with all metrics and flags
        """
        # Import models here to avoid circular imports
        from app.models.learning import (
            DailyProgress, TopicProficiency, AdaptiveLearningState
        )
        
        since = date.today() - timedelta(days=days)
        
        # === RULE 1: Analyze Consistency ===
        consistency_data = await self._analyze_consistency(user_id, since)
        
        # === RULE 2: Analyze Topic Performance ===
        topic_data = await self._analyze_topics(user_id)
        
        # === RULE 3: Check High Performer Status ===
        is_high_performer = (
            consistency_data["consistency_score"] >= self.config.HIGH_PERFORMER_CONSISTENCY
            and topic_data["overall_accuracy"] >= self.config.HIGH_PERFORMER_ACCURACY
            and consistency_data["current_streak"] >= self.config.HIGH_PERFORMER_STREAK
        )
        
        # === RULE 4: Detect Burnout Risk ===
        burnout_data = await self._analyze_burnout_risk(user_id, since)
        
        # Determine recommended load level
        recommended_load = self._determine_load_level(
            consistency_data, topic_data, burnout_data
        )
        
        # Compile analysis
        analysis = AdaptiveAnalysis(
            consistency_score=consistency_data["consistency_score"],
            burnout_risk=burnout_data["burnout_risk"],
            engagement_score=burnout_data["engagement_score"],
            accuracy_trend=topic_data["accuracy_trend"],
            weak_topics=topic_data["weak_topics"],
            topics_due_revision=topic_data["revision_due"],
            recommended_load=recommended_load,
            is_high_performer=is_high_performer,
            needs_break=burnout_data["needs_break"],
            force_revision=len(topic_data["revision_due"]) > 0,
        )
        
        # Save state to database
        await self._save_adaptive_state(user_id, analysis)
        
        return analysis
    
    async def generate_daily_plan(
        self,
        user_id: str,
        analysis: Optional[AdaptiveAnalysis] = None,
    ) -> DailyPlan:
        """
        Generate a personalized daily learning plan.
        
        Args:
            user_id: User to generate plan for
            analysis: Pre-computed analysis (or will compute)
            
        Returns:
            DailyPlan with recommendations
        """
        # Get or compute analysis
        if not analysis:
            analysis = await self.analyze_user(user_id)
        
        recommendations = []
        warnings = []
        
        # === Apply Load Level ===
        load_config = self._get_load_config(analysis.recommended_load)
        total_minutes = load_config["target_minutes"]
        
        # === RULE 4: Check if break needed ===
        if analysis.needs_break:
            recommendations.append(LearningRecommendation(
                type="break",
                priority=10,
                topic_id=None,
                topic_name=None,
                title="Take a Well-Deserved Break",
                reason="You've been working hard! A short break will help consolidate learning.",
                estimated_minutes=0,
            ))
            warnings.append("Burnout risk detected. Consider a rest day.")
            total_minutes = self.config.LOAD_LIGHT
        
        # === RULE 2: Force Revision if needed ===
        if analysis.force_revision and analysis.topics_due_revision:
            for topic_id in analysis.topics_due_revision[:3]:  # Max 3 revision topics
                topic_info = await self._get_topic_info(topic_id)
                recommendations.append(LearningRecommendation(
                    type="revision",
                    priority=9,
                    topic_id=topic_id,
                    topic_name=topic_info["name"],
                    title=f"Revise: {topic_info['name']}",
                    reason="Performance dropped. Revision recommended.",
                    estimated_minutes=20,
                    metadata={"accuracy_drop": True}
                ))
        
        # === Add Weak Area Practice ===
        if analysis.weak_topics:
            for topic_id in analysis.weak_topics[:2]:  # Max 2 weak topics
                topic_info = await self._get_topic_info(topic_id)
                recommendations.append(LearningRecommendation(
                    type="quiz",
                    priority=8,
                    topic_id=topic_id,
                    topic_name=topic_info["name"],
                    title=f"Practice Quiz: {topic_info['name']}",
                    reason="Weak area detected. Practice will help.",
                    estimated_minutes=15,
                    metadata={"is_weak_area": True}
                ))
        
        # === Add New Topic Study ===
        new_topics = await self._get_recommended_topics(user_id, analysis)
        for topic_id, topic_name in new_topics[:2]:  # Max 2 new topics
            recommendations.append(LearningRecommendation(
                type="study",
                priority=7,
                topic_id=topic_id,
                topic_name=topic_name,
                title=f"Study: {topic_name}",
                reason="Next topic in your syllabus roadmap.",
                estimated_minutes=30,
            ))
        
        # === RULE 3: Bonus Content for High Performers ===
        if analysis.is_high_performer:
            recommendations.append(LearningRecommendation(
                type="bonus",
                priority=6,
                topic_id=None,
                topic_name=None,
                title="Advanced Content Unlocked!",
                reason="You're a high performer! Enjoy bonus study material.",
                estimated_minutes=20,
                metadata={"bonus_type": "advanced_content"}
            ))
        
        # === RULE 1: Adjust for Consistency ===
        if analysis.consistency_score < self.config.CONSISTENCY_LOW:
            # Give easier targets for inconsistent users
            recommendations = [r for r in recommendations if r.priority >= 7]
            warnings.append("Start slow to build consistency. Small steps matter!")
            
            # Add consistency tip
            recommendations.append(LearningRecommendation(
                type="tip",
                priority=10,
                topic_id=None,
                topic_name=None,
                title="Build Your Streak",
                reason="Even 10 minutes of study counts. Start small, stay consistent.",
                estimated_minutes=10,
            ))
        
        # Sort by priority
        recommendations.sort(key=lambda r: -r.priority)
        
        # Generate motivational message
        message = self._generate_motivational_message(analysis)
        
        return DailyPlan(
            date=date.today(),
            user_id=user_id,
            total_recommended_minutes=total_minutes,
            load_level=analysis.recommended_load,
            recommendations=recommendations,
            revision_topics=analysis.topics_due_revision,
            new_topics=[t[0] for t in new_topics],
            warnings=warnings,
            motivational_message=message,
        )
    
    # ========== Analysis Helper Methods ==========
    
    async def _analyze_consistency(
        self, 
        user_id: str, 
        since: date
    ) -> Dict[str, Any]:
        """
        Analyze user's study consistency.
        
        RULE: Users with low consistency get reduced load to
        help them build habit gradually.
        """
        from app.models.learning import DailyProgress
        
        # Get daily progress records
        result = await self.db.execute(
            select(DailyProgress)
            .where(and_(
                DailyProgress.user_id == user_id,
                DailyProgress.date >= since
            ))
            .order_by(DailyProgress.date.desc())
        )
        progress_records = list(result.scalars().all())
        
        total_days = (date.today() - since).days
        active_days = len([p for p in progress_records if p.total_study_minutes > 0])
        
        # Calculate consistency score (0-100)
        consistency_score = (active_days / max(total_days, 1)) * 100
        
        # Calculate current streak
        current_streak = 0
        for i, p in enumerate(progress_records):
            expected_date = date.today() - timedelta(days=i)
            if p.date == expected_date and p.total_study_minutes > 0:
                current_streak += 1
            else:
                break
        
        # Count missed days in last 7
        last_week = date.today() - timedelta(days=7)
        recent = [p for p in progress_records if p.date >= last_week]
        missed_days = 7 - len([p for p in recent if p.total_study_minutes > 0])
        
        return {
            "consistency_score": consistency_score,
            "current_streak": current_streak,
            "active_days": active_days,
            "missed_days_last_week": missed_days,
        }
    
    async def _analyze_topics(self, user_id: str) -> Dict[str, Any]:
        """
        Analyze topic-wise performance.
        
        RULE: Topics with declining accuracy get flagged for revision.
        Topics with <50% accuracy are marked as weak areas.
        """
        from app.models.learning import TopicProficiency
        
        result = await self.db.execute(
            select(TopicProficiency)
            .where(TopicProficiency.user_id == user_id)
        )
        proficiencies = list(result.scalars().all())
        
        weak_topics = []
        revision_due = []
        total_accuracy = 0
        topics_with_data = 0
        
        for prof in proficiencies:
            # Check weak areas
            if prof.is_weak_area or (
                prof.accuracy_percentage is not None 
                and prof.accuracy_percentage < self.config.WEAK_TOPIC_ACCURACY
                and prof.total_questions >= 5
            ):
                weak_topics.append(prof.topic_id)
            
            # Check revision due
            if prof.next_revision_date and prof.next_revision_date <= date.today():
                revision_due.append(prof.topic_id)
            elif prof.needs_revision:
                revision_due.append(prof.topic_id)
            
            # Calculate overall accuracy
            if prof.accuracy_percentage is not None:
                total_accuracy += prof.accuracy_percentage
                topics_with_data += 1
        
        overall_accuracy = total_accuracy / topics_with_data if topics_with_data > 0 else 0
        
        # Determine trend (would need historical data in production)
        accuracy_trend = "stable"
        declining_count = len([p for p in proficiencies if p.accuracy_trend == "declining"])
        improving_count = len([p for p in proficiencies if p.accuracy_trend == "improving"])
        
        if declining_count > improving_count + 2:
            accuracy_trend = "declining"
        elif improving_count > declining_count + 2:
            accuracy_trend = "improving"
        
        return {
            "weak_topics": weak_topics,
            "revision_due": revision_due,
            "overall_accuracy": overall_accuracy,
            "accuracy_trend": accuracy_trend,
        }
    
    async def _analyze_burnout_risk(
        self, 
        user_id: str, 
        since: date
    ) -> Dict[str, Any]:
        """
        Analyze burnout risk based on study patterns.
        
        RULE: Detect signs of overwork:
        - Consistent high daily hours without breaks
        - Declining engagement despite increased time
        - Long sessions without adequate rest
        """
        from app.models.learning import DailyProgress, StudySession
        
        # Get recent daily progress
        result = await self.db.execute(
            select(DailyProgress)
            .where(and_(
                DailyProgress.user_id == user_id,
                DailyProgress.date >= since
            ))
            .order_by(DailyProgress.date.desc())
        )
        progress_records = list(result.scalars().all())
        
        # Calculate metrics
        burnout_risk = 0.0
        engagement_score = 50.0
        needs_break = False
        
        # Check for consecutive heavy study days
        consecutive_heavy = 0
        for p in progress_records[:7]:  # Last 7 days
            if p.total_study_minutes > self.config.MAX_DAILY_MINUTES:
                consecutive_heavy += 1
        
        if consecutive_heavy >= self.config.CONSECUTIVE_HEAVY_DAYS:
            burnout_risk += 40
            needs_break = True
        
        # Check for declining accuracy despite high effort
        recent_accuracy = None
        if progress_records:
            accuracies = [p.daily_accuracy for p in progress_records[:5] if p.daily_accuracy is not None]
            if len(accuracies) >= 3:
                recent_accuracy = sum(accuracies) / len(accuracies)
                
                # If accuracy dropping while still putting in time
                older_accuracy = [p.daily_accuracy for p in progress_records[5:10] if p.daily_accuracy is not None]
                if older_accuracy:
                    old_avg = sum(older_accuracy) / len(older_accuracy)
                    if recent_accuracy < old_avg - 10:  # Dropped 10%+
                        burnout_risk += 20
        
        # Check average daily study time
        if progress_records:
            avg_daily = sum(p.total_study_minutes for p in progress_records) / len(progress_records)
            if avg_daily > 180:  # More than 3 hours average
                burnout_risk += 20
            
            # Calculate engagement (goal achievement rate)
            goals_met = sum(1 for p in progress_records if p.goal_achieved)
            engagement_score = (goals_met / len(progress_records)) * 100 if progress_records else 50
        
        # Cap burnout risk
        burnout_risk = min(burnout_risk, 100)
        
        # Needs break if high burnout risk
        if burnout_risk >= self.config.BURNOUT_RISK_HIGH:
            needs_break = True
        
        return {
            "burnout_risk": burnout_risk,
            "engagement_score": engagement_score,
            "needs_break": needs_break,
            "consecutive_heavy_days": consecutive_heavy,
        }
    
    def _determine_load_level(
        self,
        consistency_data: Dict,
        topic_data: Dict,
        burnout_data: Dict,
    ) -> str:
        """
        Determine recommended daily load level.
        
        RULES:
        - High burnout risk → light
        - Low consistency → light  
        - Declining accuracy → normal (focus on quality)
        - High performer with good consistency → intensive
        """
        # Start with normal
        load = "normal"
        
        # === Rule: Reduce for burnout risk ===
        if burnout_data["burnout_risk"] >= self.config.BURNOUT_RISK_HIGH:
            return "light"
        
        if burnout_data["needs_break"]:
            return "light"
        
        # === Rule: Reduce for inconsistency ===
        if consistency_data["consistency_score"] < self.config.CONSISTENCY_LOW:
            return "light"
        
        if consistency_data["missed_days_last_week"] >= 4:
            return "light"
        
        # === Rule: Moderate for declining accuracy ===
        if topic_data["accuracy_trend"] == "declining":
            return "normal"  # Focus on quality over quantity
        
        # === Rule: Allow intensive for high performers ===
        if (
            consistency_data["consistency_score"] >= self.config.HIGH_PERFORMER_CONSISTENCY
            and topic_data["overall_accuracy"] >= self.config.HIGH_PERFORMER_ACCURACY
            and burnout_data["burnout_risk"] < 30
        ):
            return "intensive"
        
        # === Good consistency but not exceptional ===
        if consistency_data["consistency_score"] >= self.config.CONSISTENCY_MEDIUM:
            return "moderate"
        
        return load
    
    def _get_load_config(self, load_level: str) -> Dict[str, int]:
        """Get configuration for a load level"""
        configs = {
            "light": {"target_minutes": self.config.LOAD_LIGHT, "max_topics": 1},
            "normal": {"target_minutes": self.config.LOAD_NORMAL, "max_topics": 2},
            "moderate": {"target_minutes": self.config.LOAD_MODERATE, "max_topics": 3},
            "intensive": {"target_minutes": self.config.LOAD_INTENSIVE, "max_topics": 4},
        }
        return configs.get(load_level, configs["normal"])
    
    async def _get_topic_info(self, topic_id: str) -> Dict[str, str]:
        """Get topic name and info"""
        from app.models.syllabus import Topic
        
        result = await self.db.execute(
            select(Topic).where(Topic.id == topic_id)
        )
        topic = result.scalar_one_or_none()
        
        return {
            "id": topic_id,
            "name": topic.name if topic else "Unknown Topic",
        }
    
    async def _get_recommended_topics(
        self, 
        user_id: str,
        analysis: AdaptiveAnalysis,
    ) -> List[Tuple[str, str]]:
        """
        Get recommended next topics to study.
        
        RULE: Recommend topics based on:
        - Syllabus order (what's next)
        - Not already mastered
        - Prerequisites completed
        """
        from app.models.syllabus import Topic
        from app.models.learning import TopicProficiency
        
        # Get topics user has proficiency in
        result = await self.db.execute(
            select(TopicProficiency.topic_id)
            .where(and_(
                TopicProficiency.user_id == user_id,
                TopicProficiency.is_mastered == True
            ))
        )
        mastered_ids = set(r[0] for r in result.fetchall())
        
        # Get next topics from syllabus (simplified - in production, follow curriculum order)
        result = await self.db.execute(
            select(Topic)
            .where(Topic.id.notin_(mastered_ids) if mastered_ids else True)
            .order_by(Topic.order)
            .limit(5)
        )
        topics = list(result.scalars().all())
        
        return [(t.id, t.name) for t in topics]
    
    async def _save_adaptive_state(
        self,
        user_id: str,
        analysis: AdaptiveAnalysis,
    ):
        """Save analysis results to database"""
        from app.models.learning import AdaptiveLearningState
        
        result = await self.db.execute(
            select(AdaptiveLearningState)
            .where(AdaptiveLearningState.user_id == user_id)
        )
        state = result.scalar_one_or_none()
        
        if not state:
            state = AdaptiveLearningState(user_id=user_id)
            self.db.add(state)
        
        # Update state
        state.consistency_score = analysis.consistency_score
        state.burnout_risk = analysis.burnout_risk
        state.engagement_score = analysis.engagement_score
        state.accuracy_trend = analysis.accuracy_trend
        state.weak_topics_count = len(analysis.weak_topics)
        state.recommended_daily_minutes = self._get_load_config(analysis.recommended_load)["target_minutes"]
        state.topics_needing_revision = analysis.topics_due_revision
        state.current_load_level = analysis.recommended_load
        state.is_high_performer = analysis.is_high_performer
        state.needs_break = analysis.needs_break
        state.force_revision_mode = analysis.force_revision
        state.last_evaluated_at = datetime.now(timezone.utc)
        
        await self.db.flush()
    
    def _generate_motivational_message(self, analysis: AdaptiveAnalysis) -> str:
        """Generate personalized motivational message"""
        if analysis.needs_break:
            return "You've been working incredibly hard! Take a well-deserved break today. Rest is part of learning. 🌟"
        
        if analysis.is_high_performer:
            return "Outstanding performance! You're among the top learners. Keep up the excellent work! 🏆"
        
        if analysis.consistency_score >= 80:
            return "Your consistency is impressive! This habit will take you far. 💪"
        
        if analysis.accuracy_trend == "improving":
            return "Your accuracy is improving! The hard work is paying off. Keep going! 📈"
        
        if analysis.consistency_score < 30:
            return "Every journey begins with a single step. Even 10 minutes today makes a difference. Let's start small! 🌱"
        
        if len(analysis.weak_topics) > 0:
            return "Everyone has areas to improve. Focus on your weak topics today, and you'll see progress! 💡"
        
        return "Another day, another opportunity to learn. You've got this! 🚀"
