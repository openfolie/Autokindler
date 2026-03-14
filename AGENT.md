# Agent Instructions

This document provides system context, constraints, and coding conventions for AI coding agents operating within the AutoKindler repository. Read this entirely before writing or modifying code.

## System Context

AutoKindler is a distributed document delivery pipeline. It extracts academic papers from arXiv (HTML or PDF) and delivers them to a user's Kindle via email.

- **Frontend:** Chrome Extension (Manifest V3).
- **Backend:** TypeScript / Hono API (handles user state, OAuth, scheduling).
- **Workers:** Python (handles document fetching, conversion, and SMTP delivery).
- **State:** PostgreSQL (stores users, preferences, delivery logs) and AWS SQS (message queue).

## Repository Structure (Monorepo)

The project uses a monorepo structure. Ensure you are operating in the correct directory for your task.

- `apps/extension/` - Chrome Extension (React/TypeScript, Vite).
- `apps/api/` - Hono API and `node-cron` scheduler (TypeScript).
- `apps/workers/` - Python worker scripts polling SQS.
- `packages/db/` - Shared database schemas and migrations (Drizzle/Prisma).
- `infra/` - `sst.config.ts` for AWS deployment and `docker-compose.yml` for local dev.

## Architectural Constraints (CRITICAL)

1.  **Chrome Manifest V3 (MV3) Lifecycle:**
    - Do NOT use WebSockets or Server-Sent Events (SSE) for state tracking. MV3 service workers sleep after 30 seconds.
    - **Implementation:** Use aggressive HTTP polling (`GET /api/deliveries/:id` every 15s) from the extension popup to check for `Pending`, `Completed`, or `Failed` status.
2.  **Document Processing Logic (MVP Scope):**
    - **PDF:** Pass-through directly. Do NOT attempt to convert PDFs to EPUB.
    - **HTML:** Use `pypandoc` to convert to EPUB.
    - **LaTeX:** Unsupported in MVP. Hard fail if only `.tex` source is available.
3.  **Email & Size Limits:**
    - AWS SES attachment limit is 10MB.
    - **Implementation:** The Python worker MUST evaluate the file size. If `size > 9MB`, immediately update the database state to `Failed: File too large` and abort the email attempt.
    - Use standard `smtplib` in Python for sending, NOT `boto3` SES clients, to maintain provider portability.
4.  **Error Handling (No Infinite Loops):**
    - If `pypandoc` fails to convert an HTML file, catch the exception, log it, update Postgres state to `Failed`, and ACK the message in SQS to remove it. Do NOT implement complex fallback loops.

## Coding Conventions

### TypeScript (API & Extension)

- Use strict typing. Avoid `any`.
- Use standard ES Modules (`import`/`export`).
- API responses must follow a consistent JSON structure: `{ success: boolean, data?: any, error?: string }`.

### Python (Workers)

- Target Python 3.11+.
- Use Type Hints for all function signatures.
- Use `boto3` strictly for interacting with AWS SQS.
- Abstract the queue interaction behind a `MessageQueue` interface to allow future migration away from AWS.

## Local Development Commands

- **Start Local Services (Postgres, LocalStack for SQS):**
  `docker-compose up -d`
- **Run API:**
  `cd apps/api && npm run dev`
- **Run Worker:**
  `cd apps/workers && python main.py`
  _TODO: inferred assumption - using standard python execution for local dev._
- **Build Extension:**
  `cd apps/extension && npm run build`

## Build & Test Commands

_TODO: inferred assumption - standard testing frameworks._

- **API Tests:** `npm run test` (Vitest/Jest)
- **Worker Tests:** `pytest`
