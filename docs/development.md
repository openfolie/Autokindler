# Development Guide

This document outlines how to set up, run, and contribute to the AutoKindler monorepo.

## Prerequisites

Ensure you have the latest stable versions of the following tools installed:

- **Node.js:** v22 LTS (or higher)
- **Package Manager:** `pnpm` v9+ (Required for monorepo workspace management)
- **Python:** v3.13+
- **Docker Engine & Docker Compose:** For running local infrastructure (Postgres, LocalStack).
- **Pandoc:** Required locally for the Python worker (`brew install pandoc` on macOS or `apt-get install pandoc` on Linux).

## Repository Structure

We use a `pnpm` workspace monorepo.

```text
autokindler/
├── apps/
│   ├── api/          # Hono API & node-cron (TypeScript)
│   ├── extension/    # Chrome Extension MV3 (React, Vite)
│   └── workers/      # Python SQS Consumers (pypandoc, smtplib)
├── packages/
│   └── db/           # Shared database schema and migrations (Drizzle ORM)
├── infra/
│   └── docker-compose.yml # Local services (Postgres + LocalStack)
├── sst.config.ts     # SST v3 (Ion) Infrastructure as Code
├── package.json
└── pnpm-workspace.yaml

```

## Local Setup

1. **Clone and Install:**

```bash
git clone [https://github.com/yourusername/autokindler.git](https://github.com/yourusername/autokindler.git)
cd autokindler
pnpm install

```

2. **Start Local Infrastructure:**
   This spins up a local PostgreSQL 16+ instance and LocalStack (to simulate AWS SQS locally).

```bash
cd infra
docker-compose up -d

```

3. **Environment Variables:**
   Copy the example environment files in each app:

```bash
cp apps/api/.env.example apps/api/.env
cp apps/workers/.env.example apps/workers/.env

```

_Note: Ensure your local `DATABASE_URL` matches the credentials in `docker-compose.yml`._ 4. **Run Database Migrations:**
We use Drizzle ORM. Push the schema to your local Postgres container:

```bash
pnpm --filter @autokindler/db db:push

```

## Development Workflow

You can run the entire stack concurrently from the root directory using standard `pnpm` scripts:

```bash
# Starts the Hono API, the Vite bundler for the extension, and the Python worker
pnpm run dev

```

### Running Components Individually

- **API:** `pnpm --filter @autokindler/api dev`
- **Extension:** `pnpm --filter @autokindler/extension build --watch`
- **Worker:** See the "Worker Architecture" section below.

### Loading the Extension in Chrome

1. Go to `chrome://extensions/`.
2. Toggle **Developer mode** on (top right).
3. Click **Load unpacked**.
4. Select the `apps/extension/dist` folder. (Vite will automatically rebuild into this folder on save).

## Worker Architecture (Python)

The Python workers handle the CPU-bound task of converting HTML to EPUB via Pandoc.

**Setting up the Python Environment:**

```bash
cd apps/workers
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

**Running the Worker Locally:**
The worker listens to the LocalStack SQS queue by default in development mode.

```bash
python main.py

```

## Testing Strategy

- **API & Database:** Use Vitest. Tests are co-located with their features (`user.test.ts`). Focus tests on the `node-cron` matching logic and API rate limits.

```bash
pnpm test:api

```

- **Python Workers:** Use `pytest`. The `MessageQueue` adapter pattern allows you to mock the SQS queue entirely for unit testing the conversion logic.

```bash
cd apps/workers && pytest

```

## Git Workflow

1. **Branch Naming:** Use prefixes: `feat/`, `fix/`, `chore/`, or `docs/` (e.g., `feat/add-github-oauth`).
2. **Commits:** Write descriptive commit messages.
3. **PRs:** All PRs must pass the GitHub Actions CI pipeline (Type checking, Vitest, Pytest) before merging into `main`.
