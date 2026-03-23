"""Tests for the cursor-based pagination utility."""

from pyroblox.pagination import CursorPage, paginate


def test_single_page() -> None:
    def fetch(cursor: str | None) -> CursorPage[int]:
        return CursorPage(data=[1, 2, 3], next_page_cursor=None)

    items = list(paginate(fetch))
    assert items == [1, 2, 3]


def test_multiple_pages() -> None:
    pages = [
        CursorPage(data=[1, 2], next_page_cursor="abc"),
        CursorPage(data=[3, 4], next_page_cursor="def"),
        CursorPage(data=[5], next_page_cursor=None),
    ]
    call_count = 0

    def fetch(cursor: str | None) -> CursorPage[int]:
        nonlocal call_count
        page = pages[call_count]
        call_count += 1
        return page

    items = list(paginate(fetch))
    assert items == [1, 2, 3, 4, 5]
    assert call_count == 3


def test_max_pages_limit() -> None:
    def fetch(cursor: str | None) -> CursorPage[int]:
        return CursorPage(data=[1], next_page_cursor="always_more")

    items = list(paginate(fetch, max_pages=3))
    assert items == [1, 1, 1]


def test_empty_page() -> None:
    def fetch(cursor: str | None) -> CursorPage[int]:
        return CursorPage(data=[], next_page_cursor=None)

    items = list(paginate(fetch))
    assert items == []
