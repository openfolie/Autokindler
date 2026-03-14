# Project Roadmap

This document outlines the current state of AutoKindler and the planned technical trajectory. The focus shifts from basic pipeline stability in the MVP to advanced document parsing and personalized curation in future iterations.

## Current MVP (v1.0)

The MVP establishes the core infrastructure and a zero-friction user experience for the most common paper formats.

- **Format Support:** Pass-through delivery for `.pdf` files; `pypandoc` conversion for arXiv HTML endpoints.
- **Delivery Engine:** Asynchronous processing via AWS SQS and Python worker pools.
- **Scheduled Subscriptions:** Basic category matching (e.g., `cs.AI`) using the Hugging Face Daily Papers API.
- **Client Interface:** Chrome Extension (Manifest V3) triggering ad-hoc deliveries and managing local state via API polling.

## Short Term Improvements (v1.x)

Focus on expanding format coverage and hardening system security against abuse.

- **LaTeX Parsing Engine:** \* _Goal:_ Support papers that lack both HTML and PDF versions.
  - _Implementation:_ Introduce a secondary, specialized Python worker pool running `latexml` or a minimal TeX Live environment. Route these CPU-intensive tasks to a dedicated "heavy" SQS queue.
- **Kindle Email Verification (Security):**
  - _Goal:_ Prevent AWS SES bounce-rate penalties and unauthorized spam.
  - _Implementation:_ Require users to verify their Kindle address during onboarding by sending a 6-digit PIN to their Kindle, which they must enter into the extension WebUI to unlock deliveries.
- **Delivery History UI:**
  - _Goal:_ Allow users to track and retry failed papers.
  - _Implementation:_ Add a "History" tab to the extension WebUI that fetches the user's `delivery_log` from the Hono API.

## Long Term Vision (v2.0+)

Focus on hyper-personalization and infrastructure independence.

- **LLM-Based Curation Engine:**
  - _Goal:_ Move beyond broad arXiv categories (like `cs.LG`) to specific research interests (e.g., "Transformer optimization techniques").
  - _Implementation:_ Replace the simple Hugging Face rank-matching cron job with an LLM evaluator pipeline. The cron job will fetch daily abstracts, batch process them through a lightweight LLM (e.g., Gemini Flash or Claude Haiku), and score them against the user's natural language research queries.
- **Infrastructure Portability:**
  - _Goal:_ Eliminate AWS vendor lock-in to allow self-hosting or cheaper deployments (e.g., DigitalOcean).
  - _Implementation:_ \* Swap AWS SQS for Redis (using Python `rq` or Celery).
    - Swap AWS SES for a provider-agnostic SMTP service (like Postmark or SendGrid).
    - Update the `sst.config.ts` deployment model to a standard `docker-compose` swarm or Kubernetes manifest.
- **Expanded Source Ingestion:**
  - _Goal:_ Support repositories beyond arXiv.
  - _Implementation:_ Build specialized scrapers for BioRxiv, MedRxiv, and OpenReview (for NeurIPS/ICML proceedings), unifying them under a generic `DocumentFetcher` interface in the worker pool.
