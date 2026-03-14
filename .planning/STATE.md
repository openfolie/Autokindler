# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-14)

**Core value:** Users can send any arXiv paper to their Kindle in one click from their browser, eliminating the manual download-convert-email loop entirely.
**Current focus:** Phase 3 — Extension + UI

## Current Position

Phase: 3 of 4 (Extension + UI)
Plan: 1 of 2 in current phase
Status: Ready
Last activity: 2026-03-14 — Completed 02-02-PLAN.md (Document processing pipeline)

Progress: [██████░░░░] 56%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 12 min
- Total execution time: 0.9 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Backend Foundation | 3/3 ✓ | 41 min | 14 min |
| 2. Delivery Engine | 2/2 ✓ | 18 min | 9 min |

**Recent Trend:**
- Last 5 plans: 9 min, 27 min, 5 min, 8 min, 10 min
- Trend: ↓

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: Build order is DB → API → Workers → Auth → Extension → Cron → Deploy (dependency-driven)
- [Roadmap]: Auth ships with API in Phase 1 (quick depth compression), not after workers as research suggested
- [Roadmap]: SST deployment deferred to Phase 4 alongside subscriptions (validate locally first)
- [01-01]: Used postgres.js driver (not pg) for Drizzle — ESM-native, faster
- [01-01]: VARCHAR status field instead of pgEnum for delivery_log — simpler MVP
- [01-01]: LocalStack init scripts at /etc/localstack/init/ready.d for auto queue creation
- [01-02]: Stub auth via X-User-Id header — Plan 03 replaces with JWT
- [01-02]: In-memory rate limiter (no Redis) — sufficient for single-instance MVP
- [01-02]: drizzle-orm added as direct API dep for query operators (eq, and)
- [01-03]: jose for JWT (ESM-native, HS256, 7d expiry) — Edge-compatible
- [01-03]: Dual token delivery: httpOnly cookie + redirect query param for extension
- [01-03]: Auth middleware at router level via .use('*', authMiddleware)
- [01-03]: X-User-Id header stub fully removed — real JWT auth in place
- [02-01]: ABC interfaces for MessageQueue, EmailSender — testability and future swapability
- [02-01]: Always-ACK pattern: message deleted regardless of outcome, DLQ handles retries
- [02-01]: Malformed SQS messages ACKed immediately to prevent poison pill loops
- [02-01]: structlog with JSON output (production) / ConsoleRenderer (local dev)
- [02-02]: Pandoc via subprocess (not pypandoc API) for reliable kill-based timeout
- [02-02]: httpx.HTTPStatusError caught in HTML fallback for graceful 404 handling
- [02-02]: process_delivery never raises — all errors caught, status always updated

### Pending Todos

None yet.

### Blockers/Concerns

- SES production access must be requested early (24h+ approval). Consider requesting during Phase 1 even though SES usage starts in Phase 2.
- arXiv HTML conversion has ~10-20% failure rate. Phase 2 will need a test corpus of 50+ papers.
- CRXJS requires Vite 5.4.x pinning in extension package only.
- LocalStack SES does not support SMTP — SESEmailSender uses smtplib which times out locally. Consider boto3 SES API for local dev or accept SMTP-only (works in production).

## Session Continuity

Last session: 2026-03-14
Stopped at: Completed 02-02-PLAN.md — Document processing pipeline (Phase 2 complete)
Resume file: None
