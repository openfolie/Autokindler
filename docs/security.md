# Security Model

This document outlines the security architecture of the AutoKindler system, focusing on API protection, data privacy, and mitigating abuse of the email delivery pipeline.

## Threat Model

The primary security threats to the AutoKindler system are:

1.  **Email Spam/Harassment:** Malicious actors using the system to flood third-party Kindle devices with unwanted documents.
2.  **Compute/Resource Exhaustion:** Automated bots submitting thousands of conversion requests to overwhelm the Python workers and rack up AWS SQS/ECS costs.
3.  **AWS SES Account Suspension:** High bounce rates or spam complaints causing AWS to suspend our Simple Email Service (SES) production access.
4.  **Unauthorized Data Access:** Attackers reading or modifying other users' delivery logs or preferences.

## Authentication

- **Provider:** GitHub OAuth is the sole authentication provider.
- **Mechanism:** Upon successful OAuth exchange, the Hono API issues a stateless JSON Web Token (JWT) signed with a secure, server-side secret.
- **Client Storage:** The Chrome Extension stores the JWT in `chrome.storage.local`.
- **Session Lifespan:** _TODO: inferred assumption - JWTs are valid for 7 days, after which the user must re-authenticate via the extension UI._

## Authorization

- Every protected API route requires a valid JWT in the `Authorization: Bearer <token>` header.
- The Hono API extracts the `user_id` from the decoded JWT payload.
- **Tenant Isolation:** Database queries strictly scope operations to the authenticated `user_id`. A user cannot read or modify the `delivery_log` or `user_preferences` of another user.

## Rate Limiting & Resource Protection

To mitigate compute exhaustion and API abuse:

- **Manual Delivery Limit:** Authenticated users are strictly limited to **5 manual deliveries per hour**.
- **Implementation:** Enforced at the Hono API level using an in-memory store or Redis cache keyed by `user_id`. Requests exceeding this limit return a `429 Too Many Requests` status code.
- **Idempotency:** The database enforces a `UNIQUE(user_id, source_url)` constraint. The system will reject redundant requests for the same paper, preventing queue flooding.

## Email Safety (AWS SES)

Because AutoKindler sends emails to user-defined addresses, it is theoretically an open mail relay. We mitigate this using a combination of limits and Amazon's native architecture:

- **The Amazon Whitelist Barrier:** Amazon Kindle devices natively reject all incoming documents unless the sender's email address (e.g., `autokindler@openfolie.org`) is explicitly added to the user's "Approved Personal Document E-mail List."
- **MVP Trust Model:** For version 1.0, we trust the `kindle_email` inputted by the user. If an attacker inputs a victim's Kindle email, the system will send the paper, but Amazon will silently drop it because the victim has not whitelisted our sender address.
- **Future Hardening:** If SES bounce rates become an issue, we will implement a "Kindle Verification Pin" flow (sending a short code to the Kindle that must be entered in the WebUI before deliveries are unlocked).

## Data Privacy

- **PII Storage:** The system stores minimal Personally Identifiable Information (PII): only the user's primary GitHub email and their target Kindle email address.
- **Data Deletion:** The database uses `ON DELETE CASCADE` constraints. If a user requests account deletion, removing their record from the `users` table automatically purges their `user_preferences` and historical `delivery_log`.
- **Content Privacy:** The system processes public arXiv papers. We do not store the compiled EPUB or PDF files permanently; they are held in ephemeral worker memory/storage only long enough to dispatch the email, then discarded.
