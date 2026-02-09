"""
Base Model Mixins
Common functionality shared across models
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declared_attr


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns.
    Automatically sets timestamps on create and update.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
            nullable=False
        )
