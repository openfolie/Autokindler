# AutoKindler

AutoKindler is a distributed document delivery pipeline and Chrome Extension designed to seamlessly send academic research papers from arXiv directly to Amazon Kindle devices. 

By bypassing complex local setups, it allows users to trigger document conversions directly from their browser or subscribe to daily scheduled deliveries based on their category preferences.

## Key Features

* **One-Click Delivery:** A Chrome Extension active on `arxiv.org/html/*` and `*.pdf` URLs.
* **Smart Conversion (MVP):** * Directly passes through PDF files to avoid formatting loss.
    * Converts arXiv HTML versions into highly readable EPUB files using Pandoc.
* **Automated Subscriptions:** Scheduled daily delivery of top CS/AI papers sourced from the Hugging Face Daily Papers API, matched to user category preferences.
* **Asynchronous Processing:** Heavy document conversion tasks are decoupled from the API using AWS SQS and processed by scalable Python workers.
* **Live Status Tracking:** The extension polls the API to provide real-time `Pending`, `Completed`, or `Failed` status notifications.

## High-Level Architecture Summary

The project is built as a monorepo containing three core compute components backed by PostgreSQL and AWS services:

1.  **Frontend:** Chrome Extension (Manifest V3) with a local WebUI for onboarding.
2.  **API & Scheduler:** A TypeScript Hono server that handles extension requests, user state (via GitHub OAuth), and runs a daily `node-cron` job.
3.  **Workers:** Python workers that poll AWS SQS, download/convert papers, and dispatch emails via AWS SES (using standard SMTP).



For a detailed breakdown, see the [System Architecture](docs/architecture.md).

## Quick Start (Local Development)

This project requires Docker for running the database and local queues.

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/autokindler.git](https://github.com/yourusername/autokindler.git)
    cd autokindler
    ```

2.  **Start local infrastructure (Postgres, LocalStack for SQS):**
    ```bash
    docker-compose up -d
    ```

3.  **Install dependencies:**
    ```bash
    npm install
    # TODO: inferred assumption - python env setup
    cd workers && pip install -r requirements.txt && cd ..
    ```

4.  **Run the development servers:**
    ```bash
    # Starts the Hono API and local Python worker
    npm run dev 
    ```

5.  **Load the Extension:**
    * Open Chrome and navigate to `chrome://extensions/`
    * Enable "Developer mode"
    * Click "Load unpacked" and select the `apps/extension/dist` directory.

## Documentation Index

**For AI Agents & Contributors:**
* [AGENT.md](AGENT.md) - Context, constraints, and instructions for LLM coding agents.
* [Development Guide](docs/development.md) - Monorepo structure and local workflows.

**System Design & Product:**
* [Project Overview](docs/overview.md) - Core problem, users, and value proposition.
* [System Architecture](docs/architecture.md) - Component diagrams and data flow.
* [Product Specification](docs/product-spec.md) - User flows, personas, and edge cases.
* [Data Model](docs/data-model.md) - Postgres schemas and JSONB structures.
* [API Specification](docs/api-spec.md) - REST endpoints and schemas.

**Operations & Security:**
* [Operations](docs/operations.md) - Deployment (SST/Docker) and monitoring.
* [Security Model](docs/security.md) - Authentication, authorization, and abuse prevention.
* [Roadmap](docs/roadmap.md) - Future extensions (e.g., LaTeX support).
