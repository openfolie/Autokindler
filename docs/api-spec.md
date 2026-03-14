# API Specification

## Authentication

All protected endpoints require a JSON Web Token (JWT) provided in the `Authorization` header. This token is issued by the backend after a successful GitHub OAuth exchange during onboarding.

**Format:** `Authorization: Bearer <token>`

## Endpoints

### 1. Deliveries

#### POST `/api/deliveries`

Queues a new document for delivery to the user's Kindle.

- **Purpose:** Triggered manually via the Chrome Extension.
- **Rate Limit:** 5 requests per hour per user.
- **Request Schema:**
  ```json
  {
    "url": "[https://arxiv.org/html/2401.12345v1](https://arxiv.org/html/2401.12345v1)"
  }
  ```
  _(Note: `url` must be a valid arXiv HTML endpoint or a direct `.pdf` link)._
- **Response Schema (202 Accepted):**
  ```json
  {
    "success": true,
    "data": {
      "delivery_id": "uuid-1234-5678",
      "status": "Pending"
    }
  }
  ```

#### GET `/api/deliveries/:id`

Polls the current status of a specific delivery.

- **Purpose:** Used by the Chrome Extension to track progress without WebSockets.
- **Request Params:** `id` (UUID) in the URL path.
- **Response Schema (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "delivery_id": "uuid-1234-5678",
      "status": "Completed",
      "error_message": null,
      "updated_at": "2026-03-11T12:00:00Z"
    }
  }
  ```
  _(Note: `status` enum is `['Pending', 'Completed', 'Failed']`)._

### 2. User Preferences

#### GET `/api/users/me`

Retrieves the authenticated user's profile and subscription preferences.

- **Purpose:** Populates the Chrome Extension WebUI.
- **Response Schema (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "id": "uuid-user-123",
      "email": "user@github.com",
      "kindle_email": "user@kindle.com",
      "preferences": {
        "max_papers_per_month": 10,
        "category_scores": {
          "cs.AI": 10,
          "cs.LG": 8
        }
      }
    }
  }
  ```

#### PUT `/api/users/me`

Updates the user's Kindle email or daily/monthly delivery preferences.

- **Request Schema:**
  ```json
  {
    "kindle_email": "new_address@kindle.com",
    "preferences": {
      "max_papers_per_month": 15,
      "category_scores": {
        "cs.AI": 10,
        "cs.CV": 5
      }
    }
  }
  ```
- **Response Schema (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "message": "Preferences updated successfully."
    }
  }
  ```

## Error Codes

The API returns standard HTTP status codes along with a standardized JSON error response:

```json
{
  "success": false,
  "error": "Human readable error message."
}
```

- **400 Bad Request:** Malformed payload or unsupported URL (e.g., trying to send a `.tex` file).
- **401 Unauthorized:** Missing or invalid JWT.
- **404 Not Found:** Resource (e.g., delivery ID) does not exist.
- **409 Conflict:** Idempotency constraint hit (user already received this exact paper).
- **429 Too Many Requests:** Manual delivery rate limit exceeded (5/hour limit).
- **500 Internal Server Error:** Unexpected database or queue failure.

## Rate Limits

- **Global API Rate Limit:** 100 requests per minute per IP to prevent basic DDoS.
- **Delivery Queue Limit:** Strictly 5 `POST /api/deliveries` requests per hour per authenticated user to prevent SES sandbox abuse and compute exhaustion.

## Versioning Strategy

The API is currently at `v1`. Versioning is handled via the URL path (e.g., `/api/v1/deliveries`). Breaking changes will result in a `/v2/` bump, though the MVP will strictly adhere to `v1`.
