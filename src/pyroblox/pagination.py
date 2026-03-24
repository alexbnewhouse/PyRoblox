"""Generic cursor-based pagination for Roblox API responses."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from pyroblox.client import RobloxClient

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


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


def paginate_endpoint(
    client: RobloxClient,
    domain: str,
    path: str,
    model: type[M],
    *,
    limit: int = 100,
    max_pages: int | None = None,
    extra_params: dict[str, Any] | None = None,
    cursor_param: str = "cursor",
    next_cursor_key: str = "nextPageCursor",
    data_key: str = "data",
) -> Iterator[M]:
    """Shared pagination helper for standard Roblox cursor-paginated endpoints.

    Args:
        client: The RobloxClient instance.
        domain: API domain key (e.g. "groups", "badges").
        path: URL path.
        model: Pydantic model class to validate each item.
        limit: Items per page.
        max_pages: Safety limit on total pages fetched.
        extra_params: Additional query parameters merged into each request.
        cursor_param: Query parameter name for the cursor.
        next_cursor_key: JSON key for the next page cursor in responses.
        data_key: JSON key for the items array in responses.
    """
    def fetch_page(cursor: str | None) -> CursorPage[M]:
        params: dict[str, Any] = {"limit": limit}
        if extra_params:
            params.update(extra_params)
        if cursor:
            params[cursor_param] = cursor
        resp = client.get(domain, path, params=params)
        raw = resp.json()
        return CursorPage(
            data=[model.model_validate(item) for item in raw.get(data_key, [])],
            next_page_cursor=raw.get(next_cursor_key),
            previous_page_cursor=raw.get("previousPageCursor"),
        )

    return paginate(fetch_page, max_pages=max_pages)
