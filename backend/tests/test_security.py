"""
Tests for the upload-path controls in backend/security.py.

These are written as attempted attacks rather than as assertions that the code
exists: each test builds a payload that would have got through before the
hardening, and asserts it is now refused with the right status code. The
reference numbers (T1-T5) are the threats listed in security.py's docstring.

Run from the backend directory:
    python -m pytest tests/ -v
"""
import io
import zipfile

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from security import (
    MAX_COLUMNS,
    MAX_ROWS,
    SlidingWindowRateLimiter,
    assert_archive_within_limits,
    assert_frame_within_limits,
    looks_like_text,
    resolve_file_kind,
    safe_display_filename,
)

client = TestClient(main.app)


def _reset_rate_limiter():
    """The limiter is module state shared across requests, so tests that make
    real requests must clear it or they interfere with each other."""
    main.rate_limiter = SlidingWindowRateLimiter()


@pytest.fixture(autouse=True)
def fresh_limiter():
    _reset_rate_limiter()
    yield
    _reset_rate_limiter()


def _csv_bytes(rows=3):
    lines = ["name,amount"] + [f"shop{i},{100 * i}" for i in range(1, rows + 1)]
    return ("\n".join(lines) + "\n").encode()


# ---------------------------------------------------------------------------
# T4: format is established from content, not from the filename
# ---------------------------------------------------------------------------
def test_excel_renamed_to_csv_is_rejected():
    """Previously `filename.endswith('.csv')` sent this to the CSV parser."""
    buf = io.BytesIO()
    pd.DataFrame({"a": [1, 2]}).to_excel(buf, index=False)
    with pytest.raises(HTTPException) as exc:
        resolve_file_kind(buf.getvalue(), "actually_excel.csv")
    assert exc.value.status_code == 400
    assert "Excel" in exc.value.detail


def test_binary_renamed_to_xlsx_is_rejected():
    with pytest.raises(HTTPException) as exc:
        resolve_file_kind(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image.xlsx")
    assert exc.value.status_code == 400


def test_binary_renamed_to_csv_is_rejected():
    with pytest.raises(HTTPException) as exc:
        resolve_file_kind(b"\x00\x01\x02\x03" * 32, "payload.csv")
    assert exc.value.status_code == 400


def test_genuine_csv_and_xlsx_are_accepted():
    assert resolve_file_kind(_csv_bytes(), "sales.csv") == "csv"
    buf = io.BytesIO()
    pd.DataFrame({"a": [1]}).to_excel(buf, index=False)
    assert resolve_file_kind(buf.getvalue(), "sales.xlsx") == "excel"


def test_unknown_extension_is_rejected():
    with pytest.raises(HTTPException) as exc:
        resolve_file_kind(_csv_bytes(), "notes.txt")
    assert exc.value.status_code == 400


def test_looks_like_text_rejects_nul_bytes():
    assert looks_like_text(b"name,amount\nshop,100\n")
    assert not looks_like_text(b"name\x00amount")


# ---------------------------------------------------------------------------
# T2: decompression bombs and oversized parsed shapes
# ---------------------------------------------------------------------------
def test_decompression_bomb_is_rejected_before_parsing():
    """A small archive declaring a huge uncompressed payload. openpyxl would
    have expanded this; the central directory is measured instead."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bomb.xml", b"\x00" * (200 * 1024 * 1024))
    payload = buf.getvalue()
    assert len(payload) < 1 * 1024 * 1024, "the bomb must be small on the wire"
    with pytest.raises(HTTPException) as exc:
        assert_archive_within_limits(payload)
    assert exc.value.status_code in (400, 413)


def test_ordinary_workbook_passes_the_archive_check():
    buf = io.BytesIO()
    pd.DataFrame({"a": range(50), "b": range(50)}).to_excel(buf, index=False)
    assert_archive_within_limits(buf.getvalue()) is None


def test_corrupt_archive_is_a_client_error_not_a_crash():
    with pytest.raises(HTTPException) as exc:
        assert_archive_within_limits(b"PK\x03\x04" + b"garbage" * 20)
    assert exc.value.status_code == 400


def test_too_many_rows_is_rejected():
    df = pd.DataFrame({"a": range(MAX_ROWS + 1)})
    with pytest.raises(HTTPException) as exc:
        assert_frame_within_limits(df)
    assert exc.value.status_code == 400
    assert "rows" in exc.value.detail


def test_too_many_columns_is_rejected():
    df = pd.DataFrame({f"c{i}": [1] for i in range(MAX_COLUMNS + 1)})
    with pytest.raises(HTTPException) as exc:
        assert_frame_within_limits(df)
    assert exc.value.status_code == 400
    assert "columns" in exc.value.detail


def test_normal_shape_passes():
    assert assert_frame_within_limits(pd.DataFrame({"a": range(100)})) is None


# ---------------------------------------------------------------------------
# T3: rate limiting
# ---------------------------------------------------------------------------
def test_rate_limiter_allows_then_blocks():
    limiter = SlidingWindowRateLimiter(max_requests=3, window_seconds=60)

    class FakeRequest:
        headers = {}

        class client:
            host = "203.0.113.7"

    for _ in range(3):
        limiter.check(FakeRequest())
    with pytest.raises(HTTPException) as exc:
        limiter.check(FakeRequest())
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_rate_limiter_is_per_client():
    limiter = SlidingWindowRateLimiter(max_requests=1, window_seconds=60)

    def req(ip):
        class R:
            headers = {"x-forwarded-for": ip}
            client = None
        return R()

    limiter.check(req("198.51.100.1"))
    limiter.check(req("198.51.100.2"))  # different client, must be allowed
    with pytest.raises(HTTPException):
        limiter.check(req("198.51.100.1"))


def test_rate_limit_enforced_through_the_endpoint():
    main.rate_limiter = SlidingWindowRateLimiter(max_requests=2, window_seconds=60)
    payload = _csv_bytes()
    codes = [
        client.post("/upload", files={"file": ("s.csv", payload, "text/csv")}).status_code
        for _ in range(3)
    ]
    assert codes[-1] == 429, f"third request should be limited, got {codes}"


# ---------------------------------------------------------------------------
# T5: the reflected filename
# ---------------------------------------------------------------------------
def test_filename_is_sanitised():
    assert safe_display_filename("../../etc/passwd") == "passwd"
    assert "<" not in safe_display_filename("<script>alert(1)</script>.csv")
    assert safe_display_filename("") == "uploaded file"
    assert len(safe_display_filename("a" * 500)) <= 120


def test_sanitised_filename_appears_in_the_response():
    r = client.post(
        "/upload",
        files={"file": ("<script>x</script>.csv", _csv_bytes(), "text/csv")},
    )
    assert r.status_code == 200
    assert "<script>" not in r.text


# ---------------------------------------------------------------------------
# End-to-end: the happy path and the headers still work
# ---------------------------------------------------------------------------
def test_valid_upload_succeeds():
    r = client.post("/upload", files={"file": ("sales.csv", _csv_bytes(8), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert "quality_before" in body and "cleaning_report" in body


def test_empty_file_is_rejected():
    r = client.post("/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_security_headers_present():
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"


# ---------------------------------------------------------------------------
# T1: the streaming size limit
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_oversized_upload_is_refused_mid_stream():
    """The limit must fire while reading, not after the whole body is
    materialised. The fake file counts how much was requested, proving the read
    stopped early rather than consuming everything."""
    from security import MAX_UPLOAD_BYTES, read_upload_limited

    class EndlessFile:
        def __init__(self):
            self.bytes_served = 0

        async def read(self, size=-1):
            self.bytes_served += size
            return b"x" * size

    f = EndlessFile()
    with pytest.raises(HTTPException) as exc:
        await read_upload_limited(f)
    assert exc.value.status_code == 413
    # Must have stopped just past the cap, not read an unbounded amount.
    assert f.bytes_served <= MAX_UPLOAD_BYTES + (128 * 1024)


@pytest.mark.asyncio
async def test_small_upload_is_returned_intact():
    from security import read_upload_limited

    class SmallFile:
        def __init__(self, data):
            self._buf = io.BytesIO(data)

        async def read(self, size=-1):
            return self._buf.read(size)

    payload = _csv_bytes(5)
    assert await read_upload_limited(SmallFile(payload)) == payload
