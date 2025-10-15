# app/repositories/base_mixins.py
"""Repository mixins following the pattern from example.
Provides common CRUD operations while keeping flexibility.
"""

import enum
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import asc, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

ModelT = TypeVar("ModelT")


class CRUDMixin(Generic[ModelT]):
    """Mixin for basic CRUD operations.
    Handles multi-tenancy automatically.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ):
        """Initialize repository with session and context.

        Args:
            session: Database session (no commit here)
            tenant_id: For multi-tenant filtering
            user_id: For audit fields

        """
        self.session = session
        self._tenant_id = tenant_id
        self._user_id = user_id

        # These should be set by subclasses
        self.model: type[ModelT] | None = None
        self.id_attr: InstrumentedAttribute | None = None
        self.tenant_attr: InstrumentedAttribute | None = None

    def _tenant_filter(self):
        """Apply tenant filter if configured."""
        if self.tenant_attr is not None and self._tenant_id is not None:
            return self.tenant_attr == self._tenant_id
        return None

    def _base_query(self):
        """Build base query with common filters."""
        tenant_filter = self._tenant_filter()
        if tenant_filter is not None:
            return select(self.model).where(tenant_filter)
        return select(self.model)

    async def get(self, id_: Any, include=None) -> ModelT | None:
        """Get single record by ID with optional eager loading.

        Args:
            id_: Record ID
            include: Relationships to eager load. Can be:
                - String: 'merchant'
                - List: ['merchant', 'store']
                - Dict: {'store': {'merchant': True}}
                - None: No eager loading

        """
        stmt = self._base_query().where(self.id_attr == id_)

        # Apply eager loading if mixin is available
        if hasattr(self, "apply_eager_loading"):
            stmt = self.apply_eager_loading(stmt, include)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self, *, filters=None, include=None, offset: int = None, limit: int = None, **kwargs
    ) -> Sequence[ModelT] | tuple[Sequence[ModelT], int, int]:
        """List records with flexible filtering, pagination and eager loading.

        Args:
            filters: Filter object with page, limit, search, sort_by, etc. OR None for simple listing
            include: Relationships to eager load
            offset: Override offset (used when filters is None)
            limit: Override limit (used when filters is None)
            **kwargs: Additional field filters as key=value pairs

        Returns:
            - If filters provided: Tuple of (items, total, total_pages)
            - If no filters: List of items only

        """
        stmt = self._base_query()

        # Handle filter object if provided (from API endpoints)
        if filters:
            # Apply search if mixin available
            if (
                hasattr(self, "build_search_conditions")
                and hasattr(filters, "search")
                and filters.search
            ):
                # If search requested but no SEARCHABLE_FIELDS configured, return empty result
                if not hasattr(self, "SEARCHABLE_FIELDS") or not self.SEARCHABLE_FIELDS:
                    # Force empty result by adding impossible condition
                    stmt = stmt.where(self.id_attr == None)
                else:
                    search_conditions = self.build_search_conditions(filters.search)
                    if search_conditions is not None:
                        stmt = stmt.where(search_conditions)

            # Apply filters if mixin available
            if hasattr(self, "apply_filter_conditions"):
                stmt = self.apply_filter_conditions(stmt, filters)

            # Apply sorting if mixin available
            if hasattr(self, "apply_sorting"):
                stmt = self.apply_sorting(stmt, filters)

            # Extract pagination from filters
            if hasattr(filters, "page") and hasattr(filters, "limit"):
                offset = (filters.page - 1) * filters.limit
                limit = filters.limit
            else:
                offset = offset or 0
                limit = limit or 50
        else:
            # Simple mode - use provided offset/limit or defaults
            offset = offset or 0
            limit = limit or 50

        # Apply additional field filters from kwargs
        for key, value in kwargs.items():
            if hasattr(self.model, key) and value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        # Apply eager loading if mixin is available
        if hasattr(self, "apply_eager_loading"):
            stmt = self.apply_eager_loading(stmt, include)

        # Apply pagination
        stmt = stmt.offset(offset).limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        # If filters provided, always return with total and total_pages (for API endpoints)
        if filters:
            count_stmt = select(func.count(self.id_attr))

            # Apply tenant filter
            tenant_filter = self._tenant_filter()
            if tenant_filter is not None:
                count_stmt = count_stmt.where(tenant_filter)

            # Apply same filters for count
            if (
                hasattr(self, "build_search_conditions")
                and hasattr(filters, "search")
                and filters.search
            ):
                # If search requested but no SEARCHABLE_FIELDS configured, return empty result
                if not hasattr(self, "SEARCHABLE_FIELDS") or not self.SEARCHABLE_FIELDS:
                    # Force empty result by adding impossible condition
                    count_stmt = count_stmt.where(self.id_attr == None)
                else:
                    search_conditions = self.build_search_conditions(filters.search)
                    if search_conditions is not None:
                        count_stmt = count_stmt.where(search_conditions)

            if hasattr(self, "apply_filter_conditions"):
                count_stmt = self.apply_filter_conditions(count_stmt, filters)

            # Apply kwargs filters for count
            for key, value in kwargs.items():
                if hasattr(self.model, key) and value is not None:
                    count_stmt = count_stmt.where(getattr(self.model, key) == value)

            count_result = await self.session.execute(count_stmt)
            total = count_result.scalar() or 0

            # Calculate total pages
            import math

            total_pages = math.ceil(total / limit) if total > 0 and limit > 0 else 0

            return items, total, total_pages

        # Simple mode - return items only
        return items

    async def count(self, **filters) -> int:
        """Count records with optional filters."""
        stmt = select(func.count(self.id_attr))

        # Apply tenant filter
        tenant_filter = self._tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        # Apply additional filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                stmt = stmt.where(getattr(self.model, key) == value)

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create(self, obj: ModelT) -> ModelT:
        """Create new record.
        Note: Does NOT commit - service layer handles transaction.
        """
        # Add audit fields if available
        if hasattr(obj, "created_by") and self._user_id:
            obj.created_by = self._user_id
        # Don't set created_at/updated_at - let database handle it via defaults

        self.session.add(obj)
        await self.session.flush()  # Get ID without committing
        await self.session.refresh(obj)  # Get database-generated fields
        return obj

    async def update(self, id_: Any, data: dict[str, Any]) -> ModelT | None:
        """Update record by ID.

        Args:
            id_: Record ID
            data: Fields to update as dict

        """
        obj = await self.get(id_)
        if not obj:
            return None

        # Update fields
        for key, value in data.items():
            if hasattr(obj, key) and value is not None:
                setattr(obj, key, value)

        # Add audit fields
        if hasattr(obj, "updated_by") and self._user_id:
            obj.updated_by = self._user_id
        # Don't set updated_at - SQLAlchemy's onupdate will handle it

        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id_: Any) -> bool:
        """Delete record by ID (permanent delete).

        Args:
            id_: Record ID

        """
        obj = await self.get(id_)
        if not obj:
            return False

        await self.session.delete(obj)
        await self.session.flush()
        return True

    async def exists(self, id_: Any) -> bool:
        """Check if record exists."""
        stmt = select(func.count(self.id_attr)).where(self.id_attr == id_)

        # Apply tenant filter
        tenant_filter = self._tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0


class BulkOperationsMixin:
    """Mixin for bulk operations."""

    # These will be set by the class that uses this mixin
    session: AsyncSession = None
    model: type = None
    id_attr: Any = None
    tenant_attr: Any = None
    _user_id: str | None = None
    _tenant_id: str | None = None

    def _tenant_filter(self):
        """Apply tenant filter if configured."""
        if self.tenant_attr is not None and self._tenant_id is not None:
            return self.tenant_attr == self._tenant_id
        return None

    async def bulk_create(self, objects: Sequence[ModelT]) -> Sequence[ModelT]:
        """Create multiple records in one operation."""
        for obj in objects:
            if hasattr(obj, "created_by") and self._user_id:
                obj.created_by = self._user_id
            if hasattr(obj, "created_at"):
                obj.created_at = datetime.utcnow()

        self.session.add_all(objects)
        await self.session.flush()
        return objects

    async def bulk_update(self, ids: Sequence[Any], data: dict[str, Any]) -> int:
        """Update multiple records by IDs."""
        stmt = update(self.model).where(self.id_attr.in_(ids)).values(**data)

        # Add audit fields
        if hasattr(self.model, "updated_by") and self._user_id:
            stmt = stmt.values(updated_by=self._user_id)
        if hasattr(self.model, "updated_at"):
            stmt = stmt.values(updated_at=datetime.utcnow())

        # Apply tenant filter
        tenant_filter = self._tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        result = await self.session.execute(stmt)
        return result.rowcount

    async def bulk_delete(self, ids: Sequence[Any]) -> int:
        """Delete multiple records by IDs (permanent delete)."""
        stmt = delete(self.model).where(self.id_attr.in_(ids))

        # Apply tenant filter
        tenant_filter = self._tenant_filter()
        if tenant_filter is not None:
            stmt = stmt.where(tenant_filter)

        result = await self.session.execute(stmt)
        return result.rowcount


class SearchMixin:
    """Mixin for text search operations.
    Configure searchable fields via SEARCHABLE_FIELDS.
    """

    # Default searchable fields - override in subclasses to enable search
    SEARCHABLE_FIELDS: list[str] = []

    # These will be set by the class that uses this mixin
    model: type = None

    def build_search_conditions(self, search_term: str):
        """Build OR conditions for search across configured fields.
        Only searches in fields defined in SEARCHABLE_FIELDS.
        """
        if not search_term or not self.SEARCHABLE_FIELDS:
            return None

        conditions = []
        for field_name in self.SEARCHABLE_FIELDS:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                conditions.append(field.ilike(f"%{search_term}%"))

        return or_(*conditions) if conditions else None


"""
Updated FilterMixin with declarative configuration
This will replace the old hardcoded FilterMixin
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class FilterMixin:
    """Mixin for filtering operations on repository queries.

    Provides declarative filter configuration that supports:
    - Direct field filtering
    - JOIN-based filtering across relationships
    - Custom filter handlers
    - Multiple operators (eq, in, like, ilike, gt, gte, lt, lte, ne)
    """

    # Declarative filter configuration - override in subclasses
    # Use FilterTypes and FilterOperators constants for type safety
    # Format: {
    #     'filter_field': {
    #         'type': FilterTypes.DIRECT|JOIN|CUSTOM,
    #         'field': 'model_field_name',        # for direct mapping
    #         'path': 'relationship.path',         # for joins
    #         'target': 'target_field',            # field on joined model
    #         'handler': 'method_name',            # for custom logic
    #         'operator': FilterOperators.AUTO|EQ|IN|LIKE|... # filter operator
    #     }
    # }
    # Example:
    # FILTER_CONFIG = {
    #     'status': {
    #         'type': FilterTypes.DIRECT,
    #         'field': 'status',
    #         'operator': FilterOperators.AUTO
    #     },
    #     'psp_id': {
    #         'type': FilterTypes.JOIN,
    #         'path': 'merchant',
    #         'target': 'psp_id',
    #         'operator': FilterOperators.AUTO
    #     }
    # }
    FILTER_CONFIG: dict[str, dict[str, Any]] = {}

    # These will be set by the class that uses this mixin
    model: type = None

    def apply_filter_conditions(self, stmt, filters):
        """Apply filter conditions based on FILTER_CONFIG."""
        if not filters:
            return stmt

        # Log what filters we received
        if hasattr(filters, "model_dump"):
            logger.info(f"Applying filters: {filters.model_dump()}")
        else:
            logger.info(f"Applying filters: {filters}")

        return self._apply_declarative_filters(stmt, filters)

    def _apply_declarative_filters(self, stmt, filters):
        """Apply filters using declarative configuration."""
        for filter_name, config in self.FILTER_CONFIG.items():
            # Get filter value from filters object
            filter_value = self._get_filter_value(filters, filter_name)
            if filter_value is None:
                continue

            logger.info(
                f"Processing filter {filter_name}: {filter_value} (type: {type(filter_value)})"
            )

            filter_type = config.get("type", "direct")

            if filter_type == "direct":
                # Direct field mapping
                stmt = self._apply_direct_filter(stmt, config, filter_value, filter_name)
            elif filter_type == "join":
                # Requires JOIN to filter
                stmt = self._apply_join_filter(stmt, config, filter_value, filter_name)
            elif filter_type == "custom":
                # Custom handler method
                stmt = self._apply_custom_filter(stmt, config, filter_value, filter_name)

        return stmt

    def _apply_direct_filter(self, stmt, config, filter_value, filter_name):
        """Apply filter on direct model field."""
        field_name = config.get(
            "field", filter_name
        )  # Default to filter_name if field not specified

        if not hasattr(self.model, field_name):
            logger.warning(f"Field {field_name} not found on model {self.model.__name__}")
            return stmt

        model_field = getattr(self.model, field_name)
        operator = config.get("operator", "auto")

        return self._apply_operator(stmt, model_field, filter_value, operator)

    def _apply_join_filter(self, stmt, config, filter_value, filter_name):
        """Apply filter that requires JOIN."""
        path = config.get("path")
        target = config.get("target")

        if not path or not target:
            logger.warning(f"Invalid join config for {filter_name}: {config}")
            return stmt

        # Parse relationship path (e.g., "store.merchant")
        relationships = path.split(".")
        current_model = self.model

        # Track joined models to avoid duplicate joins
        joined_models = set()

        # Build JOINs along the path
        for rel_name in relationships:
            if not hasattr(current_model, rel_name):
                logger.warning(f"Relationship {rel_name} not found on {current_model.__name__}")
                return stmt

            # Get the related model through the relationship
            relationship = getattr(current_model, rel_name)
            # Handle different SQLAlchemy relationship property types
            if hasattr(relationship.property, "mapper"):
                related_model = relationship.property.mapper.class_
            elif hasattr(relationship.property, "entity"):
                related_model = relationship.property.entity.class_
            else:
                logger.warning(f"Cannot determine related model for {rel_name}")
                return stmt

            # Add JOIN if not already joined
            if related_model not in joined_models:
                stmt = stmt.join(related_model)
                joined_models.add(related_model)

            current_model = related_model

        # Apply filter on target field of final model
        if hasattr(current_model, target):
            target_field = getattr(current_model, target)
            operator = config.get("operator", "auto")
            stmt = self._apply_operator(stmt, target_field, filter_value, operator)
        else:
            logger.warning(f"Target field {target} not found on {current_model.__name__}")

        return stmt

    def _apply_custom_filter(self, stmt, config, filter_value, filter_name):
        """Apply custom filter using handler method."""
        handler_name = config.get("handler")
        if not handler_name or not hasattr(self, handler_name):
            logger.warning(f"Custom handler {handler_name} not found for filter {filter_name}")
            return stmt

        handler = getattr(self, handler_name)
        return handler(stmt, filter_value)

    def _apply_operator(self, stmt, field, value, operator="auto"):
        """Apply the appropriate SQL operator based on value type and operator config."""
        if operator == "auto":
            # Auto-detect based on value type
            if isinstance(value, list):
                if value:  # Non-empty list
                    logger.info(f"Applying IN filter: {field.key} IN {value}")
                    stmt = stmt.where(field.in_(value))
            elif isinstance(value, (int, float)):
                logger.info(f"Applying EQ filter: {field.key} = {value}")
                stmt = stmt.where(field == value)
            elif isinstance(value, str):
                logger.info(f"Applying EQ filter: {field.key} = '{value}'")
                stmt = stmt.where(field == value)
            elif isinstance(value, enum.Enum):
                logger.info(f"Applying EQ filter (enum): {field.key} = {value.value}")
                stmt = stmt.where(field == value)
            elif value is not None:
                logger.info(f"Applying EQ filter (default): {field.key} = {value}")
                stmt = stmt.where(field == value)
        elif operator == "eq":
            stmt = stmt.where(field == value)
        elif operator == "in":
            if value:
                stmt = stmt.where(field.in_(value))
        elif operator == "ilike":
            stmt = stmt.where(field.ilike(f"%{value}%"))
        elif operator == "like":
            stmt = stmt.where(field.like(f"%{value}%"))
        elif operator == "gte":
            stmt = stmt.where(field >= value)
        elif operator == "lte":
            stmt = stmt.where(field <= value)
        elif operator == "gt":
            stmt = stmt.where(field > value)
        elif operator == "lt":
            stmt = stmt.where(field < value)
        elif operator == "ne":
            stmt = stmt.where(field != value)

        return stmt

    def _get_filter_value(self, filters, filter_name):
        """Extract filter value from filters object."""
        if hasattr(filters, filter_name):
            return getattr(filters, filter_name)
        elif isinstance(filters, dict) and filter_name in filters:
            return filters[filter_name]
        return None


class SortMixin:
    """Mixin for sorting operations."""

    # Default sort field - override in subclasses
    DEFAULT_SORT_FIELD: str = "updated_at"
    DEFAULT_SORT_ORDER: str = "desc"

    # These will be set by the class that uses this mixin
    model: type = None

    def apply_sorting(self, stmt, filters):
        """Apply sorting to the query based on sort_by and sort_order from filters."""
        # Determine sort field and order
        sort_field_name = self.DEFAULT_SORT_FIELD
        sort_order = self.DEFAULT_SORT_ORDER

        if filters:
            if hasattr(filters, "sort_by") and filters.sort_by:
                sort_field_name = filters.sort_by
            if hasattr(filters, "sort_order") and filters.sort_order:
                sort_order = filters.sort_order

        # Apply sorting if field exists
        if hasattr(self.model, sort_field_name):
            sort_field = getattr(self.model, sort_field_name)
            if sort_order == "desc":
                stmt = stmt.order_by(desc(sort_field))
            else:
                stmt = stmt.order_by(asc(sort_field))

        return stmt


class EagerLoadMixin:
    """Mixin for flexible eager loading of related models.
    Supports multiple ways to specify relationships to load.
    """

    # These will be set by the class that uses this mixin
    model: type = None

    def apply_eager_loading(self, stmt, include=None):
        """Apply eager loading based on include specification.

        Args:
            stmt: SQLAlchemy statement
            include: Can be:
                - List of strings: ['merchant', 'store.merchant']
                - Dict with depth: {'merchant': True, 'store': {'merchant': True}}
                - String: 'merchant' or 'store.merchant'
                - None: No eager loading

        Returns:
            Modified statement with eager loading options

        """
        if not include:
            return stmt

        # Normalize include to list of paths
        paths_to_load = self._normalize_include(include)

        # Apply eager loading for each path
        for path in sorted(paths_to_load):  # Sort for consistent loading order
            stmt = self._apply_path_loading(stmt, path)

        return stmt

    def _normalize_include(self, include):
        """Normalize different include formats to list of paths.

        Args:
            include: Various formats of include specification

        Returns:
            Set of relationship paths to load

        """
        paths = set()

        if isinstance(include, str):
            # Single string: 'merchant' or 'store.merchant'
            paths.add(include)
        elif isinstance(include, list):
            # List of strings: ['merchant', 'store.merchant']
            paths.update(include)
        elif isinstance(include, dict):
            # Dict format: {'merchant': True, 'store': {'merchant': True}}
            def extract_paths(d, prefix=""):
                for key, value in d.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    if value is True:
                        paths.add(current_path)
                    elif isinstance(value, dict):
                        extract_paths(value, current_path)
                    elif isinstance(value, list):
                        # Support list within dict: {'store': ['merchant', 'terminals']}
                        for item in value:
                            paths.add(f"{current_path}.{item}")

            extract_paths(include)

        return paths

    def _apply_path_loading(self, stmt, path):
        """Apply eager loading for a specific relationship path.
        Supports unlimited depth of nested relationships.

        Args:
            stmt: SQLAlchemy statement
            path: Relationship path like 'store.merchant.psps.terminals'

        Returns:
            Modified statement with eager loading

        """
        from sqlalchemy.orm import selectinload

        segments = path.split(".")
        if not segments:
            return stmt

        try:
            # Build the chain of selectinload calls dynamically
            # For path 'store.merchant.psps', we need:
            # selectinload(Model.store).selectinload('merchant').selectinload('psps')

            # First segment uses the actual attribute from model
            if not hasattr(self.model, segments[0]):
                return stmt

            # Start with the first relationship
            option = selectinload(getattr(self.model, segments[0]))

            # Chain the rest using string names
            for segment in segments[1:]:
                option = option.selectinload(segment)

            # Apply the constructed option chain
            stmt = stmt.options(option)

        except Exception as e:
            # Log error but don't fail - just return original statement
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Failed to apply eager loading for path '{path}': {e}")

        return stmt


class PaginationMixin(SearchMixin, FilterMixin, SortMixin):
    """Combined mixin for pagination with search, filter, and sort.
    Inherits from SearchMixin, FilterMixin, and SortMixin.

    This mixin provides the search, filter, and sort capabilities
    that are used by the list method in CRUDMixin when a filters
    object is provided.
    """

    pass
