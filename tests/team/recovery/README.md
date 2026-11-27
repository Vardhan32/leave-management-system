# Recovery tests (pytest)

Controlled failure and recovery of the two state-changing operations of the workflows:
approving a request (`POST /api/leave-requests/{id}/review`) and creating one
(`POST /api/leave-requests`).

The test double replaces `db.session.commit` for the first call so it raises the error
SQLite reports when the database is locked or unavailable. Each test:

1. records the state before (request status, `used_days`, number of requests),
2. makes the write fail once and checks what was persisted (nothing),
3. removes the fault, retries, and checks the final state (one approval, `used_days` grew
   once, no duplicate request).

```powershell
backend\.venv\Scripts\python -m pytest tests/team/recovery -v
```

| Test | What it shows |
| --- | --- |
| `test_approval_survives_a_failed_commit` | failed approval leaves the request pending and `used_days` unchanged; the retry approves once |
| `test_failed_commit_is_reported_as_http_500` | with exception propagation off (as in production) the client gets HTTP 500 and nothing changes |
| `test_a_second_retry_cannot_double_count` | retrying after a success is refused with 409, so the balance cannot be charged twice |
| `test_create_survives_a_failed_commit_without_duplicates` | failed create stores no row; the retry stores exactly one; a repeat of the same body is refused |

`conftest.py` reuses the API client, sign-in and leave-type fixtures of `tests/team/api`, but defines
its own `app` fixture. The Area 2 fixture keeps one application context open for the whole test, so
every request shares one database session and a failed commit leaves pending changes in that session.
In production each request gets its own session, which Flask discards when the request ends; the
fixture here does the same.

With `TESTING = True` Flask re-raises unhandled exceptions into the test instead of answering 500,
which is why the first test catches `OperationalError` and the second turns propagation off.
