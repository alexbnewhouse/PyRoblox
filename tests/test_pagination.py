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


def test_cursor_is_passed_through() -> None:
    """Verify cursors from responses are actually forwarded to next request."""
    received_cursors: list[str | None] = []

    pages = [
        CursorPage(data=[1], next_page_cursor="cursor_A"),
        CursorPage(data=[2], next_page_cursor="cursor_B"),
        CursorPage(data=[3], next_page_cursor=None),
    ]
    idx = 0

    def fetch(cursor: str | None) -> CursorPage[int]:
        nonlocal idx
        received_cursors.append(cursor)
        page = pages[idx]
        idx += 1
        return page

    list(paginate(fetch))
    assert received_cursors == [None, "cursor_A", "cursor_B"]


def test_max_pages_one_stops_even_with_more() -> None:
    """max_pages=1 must stop after one page even if next_page_cursor exists."""
    call_count = 0

    def fetch(cursor: str | None) -> CursorPage[int]:
        nonlocal call_count
        call_count += 1
        return CursorPage(data=[1, 2], next_page_cursor="more")

    items = list(paginate(fetch, max_pages=1))
    assert items == [1, 2]
    assert call_count == 1


def test_lazy_evaluation_does_not_fetch_until_iterated() -> None:
    """paginate() returns an iterator; no requests until consumption."""
    call_count = 0

    def fetch(cursor: str | None) -> CursorPage[int]:
        nonlocal call_count
        call_count += 1
        return CursorPage(data=[1], next_page_cursor=None)

    iterator = paginate(fetch)
    assert call_count == 0  # Not called yet
    list(iterator)
    assert call_count == 1  # Called only when consumed


def test_empty_middle_page() -> None:
    """An empty page with next_page_cursor=None should stop iteration."""
    pages = [
        CursorPage(data=[1, 2], next_page_cursor="page2"),
        CursorPage(data=[], next_page_cursor=None),
    ]
    idx = 0

    def fetch(cursor: str | None) -> CursorPage[int]:
        nonlocal idx
        page = pages[idx]
        idx += 1
        return page

    items = list(paginate(fetch))
    assert items == [1, 2]
