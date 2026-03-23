"""Generic cursor-based pagination for Roblox API responses."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CursorPage(Generic[T]):
    """One page of a cursor-paginated Roblox API response."""

    data: list[T] = field(default_factory=list)
    next_page_cursor: str | None = None
    previous_page_cursor: str | None = None


def paginate(
    fetch_page: Callable[[str | None], CursorPage[T]],
    *,
    max_pages: int | None = None,
) -> Iterator[T]:
    """Lazily iterate through all items across all pages.

    Args:
        fetch_page: Callable that takes a cursor (None for first page)
                    and returns a CursorPage.
        max_pages: Safety limit on total pages fetched.

    Yields:
        Individual items from each page.
    """
    cursor: str | None = None
    pages_fetched = 0

    while True:
        page = fetch_page(cursor)
        yield from page.data
        pages_fetched += 1

        if page.next_page_cursor is None:
            break
        if max_pages is not None and pages_fetched >= max_pages:
            break
        cursor = page.next_page_cursor
