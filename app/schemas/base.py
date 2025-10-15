"""Base schema with automatic relationship handling for SQLAlchemy models."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, model_validator


class BaseResponseSchema(BaseModel):
    """Base schema for all database entity responses.

    Includes common fields that all entities have:
    - id: Primary key
    - created_at/updated_at: Timestamps
    - created_by/updated_by: Audit fields

    Also handles SQLAlchemy lazy-loaded relationships automatically.
    """

    model_config = ConfigDict(from_attributes=True)

    # Common fields for all entities
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    updated_by: str | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, dt: datetime, _info: Any) -> str:
        """Serialize datetime to ISO format with Z suffix for UTC."""
        if dt:
            # If datetime is naive (no timezone), assume it's UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            # Convert to UTC if it has different timezone
            elif dt.tzinfo != UTC:
                dt = dt.astimezone(UTC)
            # Return ISO format with Z suffix
            return dt.isoformat().replace("+00:00", "Z")
        return None

    @model_validator(mode="before")
    @classmethod
    def validate_relationships(cls, data: Any) -> Any:
        """Automatically handle all SQLAlchemy relationships.

        This validator checks all fields and if they are SQLAlchemy relationships
        that haven't been loaded, it sets them to None instead of raising an error.
        """
        if not isinstance(data, dict):
            # If data is a SQLAlchemy model, we need to handle relationships
            from sqlalchemy.orm import class_mapper
            from sqlalchemy.orm.base import instance_state

            try:
                # Check if this is a SQLAlchemy instance
                state = instance_state(data)
                mapper = class_mapper(data.__class__)

                # Create dict with all attributes
                result = {}

                # Handle regular columns
                for column in mapper.columns:
                    result[column.key] = getattr(data, column.key)

                # Handle relationships
                for relationship in mapper.relationships:
                    rel_key = relationship.key

                    # Check if relationship is loaded
                    if rel_key in state.unloaded:
                        # Relationship not loaded - set to None
                        result[rel_key] = None
                    else:
                        try:
                            # Try to get the relationship value
                            rel_value = getattr(data, rel_key)
                            result[rel_key] = rel_value
                        except Exception:
                            # If any error (lazy loading in async), set to None
                            result[rel_key] = None

                # Add any additional attributes from the model
                for key in dir(data):
                    if not key.startswith("_") and key not in result:
                        try:
                            value = getattr(data, key)
                            # Skip methods and properties that might trigger queries
                            if not callable(value):
                                result[key] = value
                        except:
                            pass

                return result

            except Exception:
                # If not a SQLAlchemy model or any error, return as is
                pass

        return data


# Alias for backward compatibility
BaseORMSchema = BaseResponseSchema
