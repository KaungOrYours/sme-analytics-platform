# Security

This service is a public, unauthenticated endpoint that accepts an arbitrary spreadsheet and runs a
CPU-heavy automated machine-learning pipeline over it. There is no user account, no persistence and
no stored secret, so the realistic threats are availability and resource abuse rather than data
theft. The controls below are scoped to that, and the limitations section states plainly what is
*not* covered.

Implementation: [`backend/security.py`](backend/security.py). Tests that attempt each attack:
[`backend/tests/test_security.py`](backend/tests/test_security.py).

## Data handling

Uploaded files are processed entirely in memory and are never written to persistent storage, never
logged, and never sent to a third party. Nothing is retained after the response is returned. The
service holds no API keys or credentials.

## Controls

| # | Threat | Control |
|---|---|---|
| T1 | Oversized upload exhausting memory or disk | Upload is read in 64KB chunks and refused with `413` the moment it passes 10MB, so an oversized payload is never fully materialised |
| T2 | Small file that expands enormously once parsed | `.xlsx` is a zip container, so the archive's declared uncompressed size and compression ratio are measured before openpyxl expands it; the parsed frame is also bounded to 50,000 rows and 200 columns, because a 3MB CSV can hold far more rows than the ML pipeline can process |
| T3 | Repeated requests to an expensive endpoint | Sliding-window rate limit, 10 uploads per minute per client, with `Retry-After`. Rejected requests also consume quota, so a malformed-file loop cannot buy unlimited parse attempts |
| T4 | Reaching a parser the file was not meant for | The format is established from content (zip and OLE2 signatures, text decodability) and cross-checked against the extension; a mismatch is rejected rather than guessed at. Previously the extension alone decided which parser ran |
| T5 | Reflected filename | The filename is echoed in the response and rendered by the frontend, so path separators are stripped and unusual characters replaced before it is returned. Defence in depth: React escapes interpolated text |
| — | Response caching of user data | `Cache-Control: no-store`, plus `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Cross-Origin-Resource-Policy` |
| — | Cross-origin access | Origins allow-listed; methods restricted to `GET`/`POST`/`OPTIONS`, headers to `Content-Type`, and credentialed requests disabled since the API is stateless |
| — | Vulnerable dependencies | Dependabot configured for both `pip` and `npm`; all Python dependencies are pinned to exact versions |

## Limitations — what this does not protect against

Stated deliberately, because a control described as more than it is would be worse than no control.

- **The rate limiter is per process.** It protects the single-instance deployment this project runs
  on from one noisy client. It does not coordinate across replicas and will not stop a distributed
  attack. Doing either needs shared state such as Redis, which is not deployed here.
- **The client IP is taken from `X-Forwarded-For` when present**, which is client-controlled and
  therefore spoofable. It is used because the service runs behind a proxy that appends the real
  address. The limiter is a fair-use control, not a security boundary.
- **No authentication or authorisation.** The service is intentionally open; there is nothing
  user-specific to protect.
- **No protection against a malicious file that is genuinely valid.** A well-formed 9MB CSV within
  the row and column limits will be processed, and that is the intended behaviour.
- **Row and column limits bound the worst case but are not a hard CPU ceiling.** There is no
  per-request timeout; a legitimate upload at the limit can still take a noticeable time.
- **Not independently audited.** These controls were written and tested by the author.

## Reporting

Open an issue at https://github.com/KaungOrYours/sme-analytics-platform/issues. This is a university
project rather than a production service, so there is no formal disclosure process or bounty.
