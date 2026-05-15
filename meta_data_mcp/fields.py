"""Shared Pydantic parameter types for provider tool models.

These aliases enforce project-wide validation policy so providers don't
need to re-declare common constraints inline.
"""

from typing import Annotated

from pydantic import Field

NonEmptyStr = Annotated[str, Field(min_length=1)]
"""A required string that must contain at least one character."""

Slug = Annotated[str, Field(pattern=r"^[a-z0-9-]+$", min_length=1)]
"""A URL-safe identifier slug: lowercase alphanumerics and hyphens."""

PageInt = Annotated[int, Field(default=1, ge=1)]
"""A 1-indexed page number (must be >= 1)."""

PageSize = Annotated[int, Field(default=20, ge=1, le=1000)]
"""A page-size parameter (1..1000 inclusive)."""
