"""
Upload-path hardening for the SME Analytics Platform.

Kept in one module so the controls are auditable in a single place rather than
scattered through the request handler, and so each one can be unit-tested
independently of FastAPI.

Threat model. The service is a public, unauthenticated endpoint that accepts an
arbitrary spreadsheet and runs a CPU-heavy AutoML pipeline over it. There is no
user account, no persistence, and no secret to steal, so the realistic threats
are availability and resource abuse rather than data exfiltration:

  T1  Memory/disk exhaustion by a very large upload.
  T2  CPU exhaustion by an upload that is small on disk but enormous once
      parsed -- a decompression bomb, or a CSV with millions of rows.
  T3  CPU exhaustion by repeated requests to an expensive endpoint.
  T4  Parser abuse: feeding a file whose real format is not what its extension
      claims, to reach a parser that was not intended for it.
  T5  Reflected content: the filename is echoed back in the response and
      rendered by the frontend.

Each control below maps to one of those. What this module deliberately does NOT
claim to provide: authentication, authorisation, multi-instance rate limiting,
or protection against a distributed attack. Those need infrastructure this
project does not have, and claiming them would be worse than omitting them.
"""
import io
import re
import time
import zipfile
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------------------
# Limits. All are deliberately generous for a real SME spreadsheet while still
# bounding the worst case. Named constants rather than inline literals so the
# whole policy is visible and tunable in one place.
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = 10 * 1024 * 1024        # T1: 10MB on the wire
READ_CHUNK_BYTES = 64 * 1024               # T1: streaming granularity
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024  # T2: 100MB once decompressed
MAX_COMPRESSION_RATIO = 200                # T2: refuse absurd ratios
MAX_ROWS = 50_000                          # T2: generous for a spreadsheet
MAX_COLUMNS = 200                          # T2
RATE_LIMIT_REQUESTS = 10                   # T3: per window, per client
RATE_LIMIT_WINDOW_SECONDS = 60             # T3

# T4: format signatures. CSV has no magic number, so it is validated by
# decoding instead (see looks_like_text).
ZIP_SIGNATURE = b"PK\x03\x04"              # .xlsx is a zip container
OLE2_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # legacy .xls


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Response headers appropriate to a JSON API that returns user data.

    `Cache-Control: no-store` is the one that matters most here: every
    successful response contains the content of a file the user just uploaded,
    and it must not be retained by any intermediary cache.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        return response


class SlidingWindowRateLimiter:
    """In-process per-client sliding-window limiter (T3).

    STATED LIMITATION, because the distinction matters: this is per *process*.
    It protects a single-instance deployment (which is what this project runs
    on) from a single noisy client. It does not coordinate across replicas and
    it does not stop a distributed attack. Doing either needs shared state such
    as Redis, which this project does not deploy -- so the control is scoped
    honestly rather than described as something it is not.

    Keyed on the client IP, taking the left-most entry of X-Forwarded-For when
    present because the service runs behind a proxy. That header is
    client-controlled and therefore spoofable; it is used because on this
    deployment the proxy appends the real address, and the limiter is a
    fair-use control rather than a security boundary.
    """

    def __init__(self, max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits = defaultdict(deque)

    @staticmethod
    def client_key(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def check(self, request: Request) -> None:
        key = self.client_key(request)
        now = time.monotonic()
        window = self._hits[key]

        while window and now - window[0] > self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - window[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Too many uploads. This service allows "
                    f"{self.max_requests} uploads per minute. Please wait "
                    f"{retry_after} seconds and try again."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        # Stop unbounded growth of the key dictionary from many distinct IPs.
        if len(self._hits) > 10_000:
            for stale_key in [k for k, v in self._hits.items() if not v]:
                del self._hits[stale_key]


async def read_upload_limited(file, max_bytes=MAX_UPLOAD_BYTES) -> bytes:
    """Read an upload in chunks, refusing it as soon as the cap is passed (T1).

    The previous implementation called `await file.read()` with no argument and
    checked the length afterwards, so an oversized upload was fully
    materialised before being rejected. Starlette spools large uploads to a
    temporary file rather than holding them in RAM, so this was not a pure
    memory exhaustion bug, but it did mean accepting and materialising an
    arbitrarily large payload before the limit was applied. Reading
    incrementally and aborting at the threshold bounds both.
    """
    chunks, total = [], 0
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"File exceeds the "
                    f"{max_bytes // (1024 * 1024)}MB limit. Please reduce the "
                    f"file size and try again."
                ),
            )
        chunks.append(chunk)
    return b"".join(chunks)


def looks_like_text(contents: bytes, sample_bytes=8192) -> bool:
    """Whether the payload is plausibly a text/CSV file.

    NUL bytes are the discriminator: no text encoding this app accepts
    produces them, while every binary container the parsers could be steered
    toward does.
    """
    sample = contents[:sample_bytes]
    if b"\x00" in sample:
        return False
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            sample.decode(encoding)
            return True
        except UnicodeDecodeError:
            continue
    return False


def resolve_file_kind(contents: bytes, filename: str) -> str:
    """Decide which parser to use from CONTENT, cross-checked against the
    extension (T4). Returns "csv" or "excel".

    The previous logic trusted `filename.endswith(...)` alone, so renaming any
    file to .csv routed it to the CSV parser and renaming anything to .xlsx
    routed it to openpyxl. Checking the bytes means a file reaches a parser
    only if it really is that format, and a mismatch between the claimed
    extension and the actual content is rejected rather than guessed at.
    """
    name = (filename or "").lower()
    claims_excel = name.endswith((".xlsx", ".xls"))
    claims_csv = name.endswith(".csv")

    if not (claims_excel or claims_csv):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a CSV or Excel file (.csv, .xlsx, .xls).",
        )

    is_zip = contents.startswith(ZIP_SIGNATURE)
    is_ole2 = contents.startswith(OLE2_SIGNATURE)

    if claims_excel:
        if not (is_zip or is_ole2):
            raise HTTPException(
                status_code=400,
                detail=(
                    "This file is named like an Excel workbook but its "
                    "contents are not in Excel format. Please re-save it as "
                    ".xlsx or .csv and try again."
                ),
            )
        return "excel"

    # claims_csv
    if is_zip or is_ole2:
        raise HTTPException(
            status_code=400,
            detail=(
                "This file is named .csv but its contents are an Excel "
                "workbook. Please rename it to .xlsx, or export it as real "
                "CSV, and try again."
            ),
        )
    if not looks_like_text(contents):
        raise HTTPException(
            status_code=400,
            detail="This file is named .csv but does not contain readable text.",
        )
    return "csv"


def assert_archive_within_limits(contents: bytes) -> None:
    """Reject decompression bombs before openpyxl expands the archive (T2).

    An .xlsx is a zip container, so a few hundred kilobytes on the wire can
    expand to gigabytes of XML. The zip central directory declares each
    member's uncompressed size, so the expansion can be measured without
    performing it.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(contents)) as archive:
            total_uncompressed = sum(info.file_size for info in archive.infolist())
            total_compressed = sum(info.compress_size for info in archive.infolist())
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="This Excel file appears to be corrupt and could not be opened.",
        )

    if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                "This workbook expands to more data than this service will "
                "process. Please split it into smaller files."
            ),
        )

    if total_compressed > 0:
        ratio = total_uncompressed / total_compressed
        if ratio > MAX_COMPRESSION_RATIO and total_uncompressed > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="This file was rejected because it is compressed in an unsafe way.",
            )


def assert_frame_within_limits(df) -> None:
    """Bound the parsed shape, not just the byte size (T2).

    A 3MB CSV can hold well over a million rows, and the AutoML pipeline is
    superlinear in rows, so the byte limit alone does not bound CPU.
    """
    if len(df.columns) > MAX_COLUMNS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"This file has {len(df.columns)} columns, more than the "
                f"{MAX_COLUMNS} this service analyses. Please remove the "
                f"columns you do not need."
            ),
        )
    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"This file has {len(df):,} rows, more than the "
                f"{MAX_ROWS:,} this service analyses. Please use a smaller "
                f"sample of your data."
            ),
        )


_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ \-()\[\]]")


def safe_display_filename(filename: str, max_length=120) -> str:
    """Sanitise the filename before it is echoed back to the client (T5).

    The response includes the uploaded filename and the frontend renders it.
    React escapes interpolated text, so this is defence in depth rather than
    the only control, but a name is attacker-supplied data and should not be
    reflected raw: path separators are dropped, control characters and unusual
    symbols are replaced, and the length is bounded.
    """
    if not filename:
        return "uploaded file"
    base = filename.replace("\\", "/").split("/")[-1]
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", base).strip()
    cleaned = re.sub(r"_{2,}", "_", cleaned)
    return (cleaned[:max_length] or "uploaded file")
