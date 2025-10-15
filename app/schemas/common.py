from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int = Field(ge=1, description="Current page number")
    limit: int = Field(ge=1, description="Items per page")
    total: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Generic paginated response"""

    data: list[DataT]
    pagination: PaginationMeta


class ApiResponse(BaseModel, Generic[DataT]):
    """Generic API response"""

    data: DataT
    success: bool = True
    message: str | None = None


class BaseFilter(BaseModel):
    """Base filter for pagination and sorting"""

    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=10, ge=1, description="Items per page")
    search: str | None = Field(default=None, description="Search term")
    sort_by: str | None = Field(default="updated_at", description="Field to sort by")
    sort_order: str | None = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")


class ErrorResponse(BaseModel):
    """Error response schema"""

    success: bool = False
    error: str
    message: str
    details: Any | None = None
