<div align="center">
  <img src="https://github.com/user-attachments/assets/8e6571e2-6438-4606-9f2e-4bec0120444c" alt="AutoKindler Banner" width="700" />
  <br />
  <br />

  <a href="https://www.typescriptlang.org/">
    <img src="https://img.shields.io/badge/TypeScript-007ACC?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  </a>
  <a href="https://aws.amazon.com/">
    <img src="https://img.shields.io/badge/AWS-232F3E?style=flat-square&logo=cloudflare&logoColor=white" alt="AWS" />
  </a>
  <a href="https://www.postgresql.org/">
    <img src="https://img.shields.io/badge/PostgreSQL-316192?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  </a>
  <img src="https://img.shields.io/badge/Manifest-V3-4285F4?style=flat-square&logo=google-chrome&logoColor=white" alt="Chrome MV3" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: FSL-1.1-ALv2" />

  <br />
  <br />

> **A distributed document delivery pipeline and Chrome Extension designed to seamlessly send academic research papers from arXiv directly to Amazon Kindle devices.**

</div>

<br />

By bypassing complex local setups, AutoKindler allows users to trigger document conversions directly from their browser or subscribe to daily scheduled deliveries based on their category preferences.

## key features

- **One-click delivery:** A Chrome Extension that activates solely on `arxiv.org/html/*` and `*.pdf` URLs.
- **smart conversion (mvp):**
  - Directly passes through PDF files to preserve native formatting.
  - Converts arXiv HTML versions into highly readable EPUB files using Pandoc.
- **automated subscriptions:** Scheduled daily delivery of top CS/AI papers sourced from the Hugging Face Daily Papers API, matched to your custom category preferences.
- **asynchronous processing:** Heavy document conversion tasks are decoupled from the API using AWS SQS and processed by a scalable Python worker pool.
- **live status tracking:** The extension polls the API to provide real-time `Pending`, `Completed`, or `Failed` native browser notifications.

---

## high-level architecture

The project is built as a monorepo containing three core compute components backed by PostgreSQL and AWS services:

1. **frontend:** Chrome Extension (Manifest V3) with a local WebUI for onboarding.
2. **api & scheduler:** A TypeScript Hono server that handles extension requests, user state (via GitHub OAuth), and runs a daily `node-cron` job.
3. **workers:** Python workers that poll AWS SQS, download/convert papers, and dispatch emails via AWS SES (using standard SMTP).

_(for a detailed breakdown, see the [system architecture](docs/architecture.md) document)._

---

## quick start

This project requires **Docker** for running the database and local queues, and **pnpm** for workspace management.

### 1. clone the repository

```bash
git clone https://github.com/yourusername/autokindler.git
cd autokindler
```

### 2. start local infrastructure (postgres, localstack for sqs)

```bash
cd infra
docker-compose up -d
cd ..
```

### 3. install dependencies

```bash
# install node/ts dependencies
pnpm install

# setup python worker environment
cd apps/workers
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ../..
```

### 4. run the development servers

```bash
# starts the hono api, vite extension bundler, and local python worker
pnpm run dev
```

### 5. load the extension

- Open Chrome and navigate to `chrome://extensions/`
- Enable **Developer mode** in the top right corner
- Click **Load unpacked** and select the `apps/extension/dist` directory

---

## documentation index

- **[AGENT.md](AGENT.md)** — Context, constraints, and instructions for LLM coding agents.
- **[development guide](docs/development.md)** — Monorepo structure, tooling, and local workflows.

### system design & product

- **[project overview](docs/overview.md)** — Core problem, target users, and value proposition.
- **[system architecture](docs/architecture.md)** — Component diagrams and data flows.
- **[product specification](docs/product-spec.md)** — User flows, personas, and edge cases.
- **[data model](docs/data-model.md)** — Postgres schemas and JSONB structures.
- **[api specification](docs/api-spec.md)** — REST endpoints, schemas, and rate limits.

### operations & security

- **[operations](docs/operations.md)** — Deployment via SST, queue management, and logging.
- **[security model](docs/security.md)** — Auth flow, authorization, and SES abuse prevention.
- **[roadmap](docs/roadmap.md)** — Future extensions (e.g., LaTeX compilation, LLM curation).
