"""Constants for FilterMixin configuration
Provides type-safe constants for filter types and operators.
"""


class FilterTypes:
    """Constants for filter types in FILTER_CONFIG."""

    DIRECT = "direct"  # Direct field filtering
    JOIN = "join"  # Filter requiring JOIN operations
    CUSTOM = "custom"  # Custom filter handler

    ALL = [DIRECT, JOIN, CUSTOM]

    @classmethod
    def is_valid(cls, filter_type: str) -> bool:
        """Check if filter type is valid."""
        return filter_type in cls.ALL


class FilterOperators:
    """Constants for filter operators in FILTER_CONFIG."""

    # Auto-detection based on value type
    AUTO = "auto"

    # Equality operators
    EQ = "eq"  # Equal (=)
    NE = "ne"  # Not equal (!=)

    # List operators
    IN = "in"  # IN operator for lists

    # String pattern operators
    LIKE = "like"  # SQL LIKE with wildcards
    ILIKE = "ilike"  # Case-insensitive LIKE

    # Comparison operators
    GT = "gt"  # Greater than (>)
    GTE = "gte"  # Greater than or equal (>=)
    LT = "lt"  # Less than (<)
    LTE = "lte"  # Less than or equal (<=)

    ALL = [AUTO, EQ, NE, IN, LIKE, ILIKE, GT, GTE, LT, LTE]

    @classmethod
    def is_valid(cls, operator: str) -> bool:
        """Check if operator is valid."""
        return operator in cls.ALL
