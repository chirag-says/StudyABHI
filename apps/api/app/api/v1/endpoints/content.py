"""
Content API Endpoints
CRUD routes for articles, notes, and content management
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user
from app.models.user import User
from app.services.content_service import ContentService
from app.schemas.content import (
    ContentCreate, ContentUpdate, ContentResponse, ContentDetailResponse,
    ContentListResponse, ContentFilterParams,
    ContentTagCreate, ContentTagUpdate, ContentTagResponse,
    ContentTypeEnum, LanguageEnum, DifficultyLevelEnum, ContentStatusEnum
)

router = APIRouter()


# ==================== Content Endpoints ====================

@router.get("", response_model=ContentListResponse)
async def list_contents(
    content_type: Optional[ContentTypeEnum] = None,
    language: Optional[LanguageEnum] = None,
    difficulty: Optional[DifficultyLevelEnum] = None,
    status: Optional[ContentStatusEnum] = Query(None, alias="status"),
    topic_id: Optional[str] = None,
    tag_id: Optional[str] = None,
    is_featured: Optional[bool] = None,
    is_premium: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all content with filtering and pagination.
    
    Filters:
    - content_type: article, note, pdf, video
    - language: en, hi, hinglish
    - difficulty: beginner, intermediate, advanced, expert
    - status: draft, review, published, archived
    - topic_id: Filter by syllabus topic
    - tag_id: Filter by tag
    - is_featured: Featured content only
    - is_premium: Premium content only
    - search: Search in title and summary
    """
    filters = ContentFilterParams(
        content_type=content_type,
        language=language,
        difficulty=difficulty,
        status=status,
        topic_id=topic_id,
        tag_id=tag_id,
        is_featured=is_featured,
        is_premium=is_premium,
        search=search,
        page=page,
        limit=limit,
    )
    
    service = ContentService(db)
    items, total = await service.list_contents(filters)
    
    pages = (total + limit - 1) // limit
    
    return ContentListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post("", response_model=ContentDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_content(
    data: ContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create new content (article, note, etc.)
    
    Requires authentication.
    """
    service = ContentService(db)
    content = await service.create_content(data, author_id=current_user.id)
    
    # Reload with relationships
    content = await service.get_content_by_id(content.id)
    return content


@router.get("/{content_id}", response_model=ContentDetailResponse)
async def get_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Get content by ID with full details.
    
    Increments view count for published content.
    """
    service = ContentService(db)
    content = await service.get_content_by_id(content_id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check access for non-published content
    if content.status != "published":
        if not current_user or (current_user.id != content.author_id and not current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    # Increment view count
    await service.increment_view_count(content_id)
    
    return content


@router.get("/slug/{slug}", response_model=ContentDetailResponse)
async def get_content_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get content by URL slug"""
    service = ContentService(db)
    content = await service.get_content_by_slug(slug)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check access for non-published content
    if content.status != "published":
        if not current_user or (current_user.id != content.author_id and not current_user.is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    await service.increment_view_count(content.id)
    return content


@router.patch("/{content_id}", response_model=ContentDetailResponse)
async def update_content(
    content_id: str,
    data: ContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update content.
    
    Only the author or admin can update.
    """
    service = ContentService(db)
    content = await service.get_content_by_id(content_id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check ownership
    if content.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this content"
        )
    
    updated = await service.update_content(content_id, data)
    return await service.get_content_by_id(updated.id)


@router.post("/{content_id}/publish", response_model=ContentDetailResponse)
async def publish_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publish content (change status to published)"""
    service = ContentService(db)
    content = await service.get_content_by_id(content_id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    if content.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    published = await service.publish_content(content_id)
    return await service.get_content_by_id(published.id)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_content(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete content"""
    service = ContentService(db)
    content = await service.get_content_by_id(content_id)
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    if content.author_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    await service.delete_content(content_id)
    return None


# ==================== Tag Endpoints ====================

@router.get("/tags/all", response_model=list[ContentTagResponse])
async def list_tags(
    db: AsyncSession = Depends(get_db),
):
    """List all content tags"""
    service = ContentService(db)
    return await service.list_tags()


@router.post("/tags", response_model=ContentTagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    data: ContentTagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new content tag (requires auth)"""
    service = ContentService(db)
    return await service.create_tag(data)


@router.patch("/tags/{tag_id}", response_model=ContentTagResponse)
async def update_tag(
    tag_id: str,
    data: ContentTagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update content tag"""
    service = ContentService(db)
    tag = await service.update_tag(tag_id, data)
    
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return tag


@router.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete content tag"""
    service = ContentService(db)
    
    if not await service.delete_tag(tag_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    return None
