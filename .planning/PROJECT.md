# AutoKindler

## What This Is

AutoKindler is a distributed document delivery pipeline and Chrome Extension that sends academic research papers from arXiv directly to Amazon Kindle devices. It provides one-click browser-triggered delivery of PDFs and HTML-to-EPUB conversions, plus automated daily subscriptions of top CS/AI papers sourced from the Hugging Face Daily Papers API. It targets academic researchers, graduate students, and ML/AI practitioners who want zero-friction paper consumption on e-ink.

## Core Value

Users can send any arXiv paper to their Kindle in one click from their browser, eliminating the manual download-convert-email loop entirely.

## Requirements

### Validated

(None yet -- ship to validate)

### Active

- [ ] Chrome Extension (MV3) activates on arxiv.org/html/* and *.pdf URLs with one-click "Send to Kindle"
- [ ] PDF pass-through delivery (no conversion, email directly)
- [ ] HTML-to-EPUB conversion via Pandoc for reflowable e-ink reading
- [ ] GitHub OAuth authentication with JWT session management
- [ ] User onboarding flow: Kindle email input, sender whitelisting tutorial, category preferences
- [ ] Asynchronous document processing via AWS SQS + Python worker pool
- [ ] Email delivery via AWS SES (standard SMTP)
- [ ] Live status tracking via HTTP polling (Pending/Completed/Failed) with browser notifications
- [ ] Automated daily subscriptions: cron fetches top HF Daily Papers, matches user category preferences, enforces quotas
- [ ] Rate limiting (5 manual sends/hour, monthly quota for subscriptions)
- [ ] Idempotency: unique constraint prevents duplicate deliveries per user/paper
- [ ] File size guard: hard-fail deliveries > 9MB before SMTP attempt
- [ ] Graceful error handling: Pandoc failures hard-fail with user notification, no retry loops

### Out of Scope

- LaTeX compilation -- high complexity, no `.tex` support in MVP
- Full arXiv category coverage -- MVP limited to CS/AI categories only
- Custom LLM recommendation engine -- defer to v2, use HF rank signals for now
- Real-time progress tracking (WebSocket/SSE) -- MV3 service workers sleep after 30s, use polling
- Mobile app -- web/extension-first
- Multi-source ingestion (BioRxiv, OpenReview) -- arXiv only for MVP

## Context

- **Monorepo structure** managed by pnpm:
  - `apps/extension/` -- Chrome Extension (React/TypeScript, Vite, Manifest V3)
  - `apps/api/` -- Hono API server + node-cron scheduler (TypeScript)
  - `apps/workers/` -- Python workers polling SQS
  - `packages/db/` -- Shared database schemas/migrations (Drizzle)
  - `infra/` -- SST config for AWS deployment + docker-compose for local dev
- **Database:** PostgreSQL with 4 core tables: users, user_preferences (JSONB category_scores), daily_papers (cache), delivery_log (state machine)
- **Local dev:** Docker (Postgres + LocalStack for SQS), pnpm workspaces
- **Deployment target:** AWS via SST (Lambda-compatible Hono, SQS, SES, RDS)
- **Existing docs:** Comprehensive design documents exist covering architecture, product spec, data model, API spec, security, operations, and roadmap

## Constraints

- **Chrome MV3**: No WebSockets/SSE -- service workers sleep after 30s. Must use HTTP polling for status updates.
- **AWS SES**: 10MB attachment limit. Workers must pre-check file size (9MB threshold).
- **Tech Stack**: TypeScript (Hono API + Extension), Python (Workers), PostgreSQL, AWS (SQS/SES/SST).
- **Error Philosophy**: No complex fallback chains. Failed conversions hard-fail, ACK the SQS message, notify user.
- **Python Workers**: Must abstract queue behind `MessageQueue` interface for future portability away from AWS.
- **SMTP**: Use standard `smtplib`, not boto3 SES client, for provider portability.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hono over Express/Fastify | Lightweight, runs on Lambda via SST, fast cold starts | -- Pending |
| HTTP polling over WebSocket | Chrome MV3 kills service workers after 30s | -- Pending |
| PDF pass-through (no conversion) | Preserves native formatting, avoids unnecessary processing | -- Pending |
| pypandoc for HTML-to-EPUB | Mature, handles arXiv HTML well, avoids custom parsing | -- Pending |
| GitHub OAuth (not email/password) | Simpler auth, no password management, target users have GitHub | -- Pending |
| SQS over Redis queues | AWS-native, pairs with SST deployment, easy scaling | -- Pending |
| smtplib over boto3 SES | Provider portability -- can swap to SendGrid/Postmark later | -- Pending |
| Monorepo with pnpm | Shared types/schemas between API and extension, single repo | -- Pending |

---
*Last updated: 2026-03-14 after initialization*
