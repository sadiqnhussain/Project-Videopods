# Videopods API documentation

Videopods exposes a JWT-authenticated REST API for accounts, meetings, scheduling, history, and WebRTC configuration.

## Interactive API documentation

Run the project and open:

- **Swagger UI:** `/api/docs/` — interactive endpoint explorer and request tester.
- **ReDoc:** `/api/redoc/` — readable API reference.
- **OpenAPI schema:** `/api/schema/` — machine-readable OpenAPI 3 schema.

The generated documentation is powered by **drf-spectacular** and follows the same Django URL configuration used by the application, so deployment prefixes do not require JavaScript changes.

## Authentication

Most endpoints require a JWT access token.

1. Register with `POST /api/auth/register/` or sign in with `POST /api/auth/token/`.
2. Copy the returned `access` token.
3. Send it as `Authorization: Bearer <access-token>`.
4. Refresh an expired access token with `POST /api/auth/token/refresh/`.

Swagger UI can be authorized with the **Authorize** button using the bearer token.

## Authentication endpoints

| Method | Endpoint                   | Auth | Purpose                                        |
| ------ | -------------------------- | ---- | ---------------------------------------------- |
| POST   | `/api/auth/register/`      | No   | Create an account and return tokens.           |
| POST   | `/api/auth/token/`         | No   | Sign in and receive JWT access/refresh tokens. |
| POST   | `/api/auth/token/refresh/` | No   | Refresh an access token.                       |
| GET    | `/api/auth/me/`            | JWT  | Return the current user.                       |
| GET    | `/api/auth/google/config/` | No   | Return Google client configuration.            |
| POST   | `/api/auth/google/`        | No   | Sign in with a Google ID token.                |

## Meeting endpoints

| Method | Endpoint                              | Auth | Purpose                                                    |
| ------ | ------------------------------------- | ---- | ---------------------------------------------------------- |
| POST   | `/api/meetings/create/`               | JWT  | Create an instant or scheduled meeting.                    |
| GET    | `/api/meetings/<meeting_id>/`         | JWT  | Get meeting state, access window, and host information.    |
| POST   | `/api/meetings/<meeting_id>/start/`   | Host | Start a scheduled meeting within its allowed start window. |
| POST   | `/api/meetings/<meeting_id>/end/`     | Host | End an active meeting for everyone.                        |
| POST   | `/api/meetings/<meeting_id>/cancel/`  | Host | Cancel an upcoming scheduled meeting.                      |
| GET    | `/api/meetings/upcoming/`             | JWT  | List the current user's upcoming scheduled meetings.       |
| GET    | `/api/meetings/history/`              | JWT  | List the current user's meeting history.                   |
| DELETE | `/api/meetings/history/<meeting_id>/` | JWT  | Delete one history entry for the current user.             |
| DELETE | `/api/meetings/history/all/`          | JWT  | Delete all history entries for the current user.           |
| GET    | `/api/meetings/rtc-config/`           | JWT  | Return configured STUN/TURN servers.                       |

The exact request/response schemas, validation errors, status codes, and interactive “Try it out” controls are available in Swagger UI and the generated OpenAPI schema.

## WebSocket signaling

WebRTC signaling uses a Channels WebSocket endpoint configured through `WEBSOCKET_MEETING_PREFIX` in the environment. The browser obtains the prefix from Django rather than hardcoding it in JavaScript.

The signaling flow supports participant roster discovery, deterministic offer direction, SDP offer/answer exchange, ICE candidates, media state, participant join/leave notifications, and `MEETING_ENDED` broadcasts.

## Deployment note

The frontend does not hardcode the REST API prefix or meeting page paths. Django's `{% url %}` resolver injects route URLs into `window.VP_URLS`, while environment settings control deployment-specific public and WebSocket configuration.
