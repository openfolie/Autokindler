# Project Overview

AutoKindler is a distributed document delivery system consisting of a browser extension, an API scheduling layer, and an asynchronous worker pool. It automates the extraction, conversion, and delivery of academic research papers from arXiv to Amazon Kindle devices.

## Problem

Reading complex academic papers on standard backlit monitors causes eye strain and fatigue, making e-ink displays (like the Kindle) the preferred medium for deep reading. However, the manual workflow to achieve this is highly frictionless:

1. Downloading the PDF or source files from arXiv.
2. Converting the document into a Kindle-friendly format (EPUB) if the PDF formatting is poor.
3. Manually attaching and emailing the file to the user's `@kindle.com` address.
4. Repeating this process daily for newly published research.

## Target Users

- **Academic Researchers & Graduate Students:** Users who read multiple papers per week and require a streamlined consumption pipeline.
- **Machine Learning / AI Practitioners:** Professionals who need to stay updated with the rapid daily output of ML research without disrupting their workflow.

## Core Idea

AutoKindler eliminates the manual delivery loop. It provides a zero-friction bridge between the browser where discovery happens and the e-reader where consumption happens. It handles both ad-hoc deliveries triggered directly from the browser and automated, scheduled deliveries of top-ranked daily papers.

## Key Features

- **Browser-Native Trigger:** A Chrome Extension that activates solely on `arxiv.org/html/*` and `*.pdf` endpoints.
- **Intelligent Format Routing:**
  - **PDFs:** Passed through directly to the Kindle without conversion to preserve native formatting.
  - **HTML:** Fetched and converted to EPUB using Pandoc for reflowable text support.
- **Automated Daily Subscriptions:** A cron-driven engine that fetches the daily top Computer Science and AI papers (via the Hugging Face API) and emails them to users based on their selected category preferences and volume quotas.
- **Asynchronous Processing:** Heavy conversion tasks are offloaded to Python workers via a message queue (AWS SQS), ensuring the browser extension and API remain highly responsive.

## Non-Goals

To maintain a tight MVP scope, AutoKindler explicitly does **not** attempt the following:

- **LaTeX Parsing:** We do not compile `.tex` source files. If a paper lacks an HTML version or PDF, the system will not attempt a complex fallback compilation.
- **Full arXiv Coverage:** Automated daily subscriptions are strictly limited to Computer Science (CS) and Artificial Intelligence (AI) categories. We are not ingesting Mathematics, Physics, or Biology feeds.
- **Custom Recommendation Algorithms:** We do not build custom LLM-based curation or recommendation engines. Paper quality/popularity signals are delegated entirely to the Hugging Face Daily Papers API.
- **Real-Time Granular Progress:** The extension provides binary state updates (`Pending`, `Completed`, `Failed`) rather than granular, real-time progress bars to avoid WebSocket/SSE overhead in Chrome Manifest V3.
