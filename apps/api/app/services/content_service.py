"""
Content Service
Business logic for content management
"""
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
import re

from app.models.content import Content, ContentTag, ContentStatus, content_tag_associations
from app.models.syllabus import Topic, content_topics
from app.schemas.content import (
    ContentCreate, ContentUpdate, ContentFilterParams,
    ContentTagCreate, ContentTagUpdate
)


class ContentService:
    """Service class for content-related operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== Content CRUD ====================
    
    async def get_content_by_id(self, content_id: str) -> Optional[Content]:
        """Get content by ID with relationships"""
        result = await self.db.execute(
            select(Content)
            .options(
                selectinload(Content.topics),
                selectinload(Content.tags),
                selectinload(Content.author)
            )
            .where(Content.id == content_id)
        )
        return result.scalar_one_or_none()
    
    async def get_content_by_slug(self, slug: str) -> Optional[Content]:
        """Get content by slug"""
        result = await self.db.execute(
            select(Content)
            .options(
                selectinload(Content.topics),
                selectinload(Content.tags),
                selectinload(Content.author)
            )
            .where(Content.slug == slug)
        )
        return result.scalar_one_or_none()
    
    async def list_contents(
        self, 
        filters: ContentFilterParams
    ) -> Tuple[List[Content], int]:
        """List contents with filtering and pagination"""
        query = select(Content)
        count_query = select(func.count(Content.id))
        
        # Apply filters
        if filters.content_type:
            query = query.where(Content.content_type == filters.content_type.value)
            count_query = count_query.where(Content.content_type == filters.content_type.value)
        
        if filters.language:
            query = query.where(Content.language == filters.language.value)
            count_query = count_query.where(Content.language == filters.language.value)
        
        if filters.difficulty:
            query = query.where(Content.difficulty == filters.difficulty.value)
            count_query = count_query.where(Content.difficulty == filters.difficulty.value)
        
        if filters.status:
            query = query.where(Content.status == filters.status.value)
            count_query = count_query.where(Content.status == filters.status.value)
        
        if filters.author_id:
            query = query.where(Content.author_id == filters.author_id)
            count_query = count_query.where(Content.author_id == filters.author_id)
        
        if filters.is_featured is not None:
            query = query.where(Content.is_featured == filters.is_featured)
            count_query = count_query.where(Content.is_featured == filters.is_featured)
        
        if filters.is_premium is not None:
            query = query.where(Content.is_premium == filters.is_premium)
            count_query = count_query.where(Content.is_premium == filters.is_premium)
        
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.summary.ilike(search_term)
                )
            )
            count_query = count_query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.summary.ilike(search_term)
                )
            )
        
        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        offset = (filters.page - 1) * filters.limit
        query = query.offset(offset).limit(filters.limit)
        query = query.order_by(Content.created_at.desc())
        
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        
        return items, total
    
    async def create_content(
        self, 
        data: ContentCreate, 
        author_id: Optional[str] = None
    ) -> Content:
        """Create new content"""
        # Generate slug
        slug = self._generate_unique_slug(data.title)
        
        # Calculate word count if body provided
        word_count = None
        if data.body:
            word_count = len(data.body.split())
        
        content = Content(
            title=data.title,
            slug=slug,
            subtitle=data.subtitle,
            content_type=data.content_type.value,
            body=data.body,
            summary=data.summary,
            language=data.language.value,
            difficulty=data.difficulty.value,
            status=ContentStatus.DRAFT.value,
            file_url=data.file_url,
            duration_minutes=data.duration_minutes,
            estimated_read_time=data.estimated_read_time,
            word_count=word_count,
            is_premium=data.is_premium,
            author_id=author_id,
        )
        
        self.db.add(content)
        await self.db.flush()
        
        # Add topic associations
        if data.topic_ids:
            await self._update_content_topics(content.id, data.topic_ids)
        
        # Add tag associations
        if data.tag_ids:
            await self._update_content_tags(content.id, data.tag_ids)
        
        await self.db.refresh(content)
        return content
    
    async def update_content(
        self, 
        content_id: str, 
        data: ContentUpdate
    ) -> Optional[Content]:
        """Update existing content"""
        content = await self.get_content_by_id(content_id)
        if not content:
            return None
        
        # Update fields
        update_data = data.model_dump(exclude_unset=True, exclude={"topic_ids", "tag_ids"})
        
        for field, value in update_data.items():
            if hasattr(value, 'value'):  # Handle enums
                value = value.value
            setattr(content, field, value)
        
        # Update word count if body changed
        if data.body is not None:
            content.word_count = len(data.body.split())
        
        # Increment version
        content.version += 1
        
        # Update associations
        if data.topic_ids is not None:
            await self._update_content_topics(content_id, data.topic_ids)
        
        if data.tag_ids is not None:
            await self._update_content_tags(content_id, data.tag_ids)
        
        await self.db.flush()
        await self.db.refresh(content)
        return content
    
    async def delete_content(self, content_id: str) -> bool:
        """Delete content"""
        content = await self.get_content_by_id(content_id)
        if not content:
            return False
        
        await self.db.delete(content)
        await self.db.flush()
        return True
    
    async def publish_content(self, content_id: str) -> Optional[Content]:
        """Publish content"""
        from datetime import datetime, timezone
        
        content = await self.get_content_by_id(content_id)
        if not content:
            return None
        
        content.status = ContentStatus.PUBLISHED.value
        content.published_at = datetime.now(timezone.utc)
        
        await self.db.flush()
        await self.db.refresh(content)
        return content
    
    async def increment_view_count(self, content_id: str) -> None:
        """Increment view count for content"""
        content = await self.get_content_by_id(content_id)
        if content:
            content.view_count += 1
            await self.db.flush()
    
    # ==================== Tag CRUD ====================
    
    async def get_tag_by_id(self, tag_id: str) -> Optional[ContentTag]:
        """Get tag by ID"""
        result = await self.db.execute(
            select(ContentTag).where(ContentTag.id == tag_id)
        )
        return result.scalar_one_or_none()
    
    async def list_tags(self) -> List[ContentTag]:
        """List all tags"""
        result = await self.db.execute(
            select(ContentTag).order_by(ContentTag.name)
        )
        return list(result.scalars().all())
    
    async def create_tag(self, data: ContentTagCreate) -> ContentTag:
        """Create new tag"""
        slug = self._slugify(data.name)
        
        tag = ContentTag(
            name=data.name,
            slug=slug,
            description=data.description,
            color=data.color,
        )
        
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag
    
    async def update_tag(
        self, 
        tag_id: str, 
        data: ContentTagUpdate
    ) -> Optional[ContentTag]:
        """Update tag"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tag, field, value)
        
        # Update slug if name changed
        if data.name:
            tag.slug = self._slugify(data.name)
        
        await self.db.flush()
        await self.db.refresh(tag)
        return tag
    
    async def delete_tag(self, tag_id: str) -> bool:
        """Delete tag"""
        tag = await self.get_tag_by_id(tag_id)
        if not tag:
            return False
        
        await self.db.delete(tag)
        await self.db.flush()
        return True
    
    # ==================== Helper Methods ====================
    
    async def _update_content_topics(
        self, 
        content_id: str, 
        topic_ids: List[str]
    ) -> None:
        """Update content-topic associations"""
        # Clear existing
        await self.db.execute(
            content_topics.delete().where(content_topics.c.content_id == content_id)
        )
        
        # Add new
        for topic_id in topic_ids:
            await self.db.execute(
                content_topics.insert().values(
                    content_id=content_id, 
                    topic_id=topic_id
                )
            )
    
    async def _update_content_tags(
        self, 
        content_id: str, 
        tag_ids: List[str]
    ) -> None:
        """Update content-tag associations"""
        # Clear existing
        await self.db.execute(
            content_tag_associations.delete().where(
                content_tag_associations.c.content_id == content_id
            )
        )
        
        # Add new
        for tag_id in tag_ids:
            await self.db.execute(
                content_tag_associations.insert().values(
                    content_id=content_id, 
                    tag_id=tag_id
                )
            )
    
    def _generate_unique_slug(self, title: str) -> str:
        """Generate unique slug from title"""
        import uuid
        base_slug = self._slugify(title)
        # Add short UUID suffix for uniqueness
        return f"{base_slug}-{str(uuid.uuid4())[:8]}"
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_-]+', '-', slug)
        slug = slug.strip('-')
        return slug[:120]
