# Videopods

Videopods is a browser-based video-meeting application built with Django, Django REST Framework, Django Channels, and WebRTC. It supports account registration and sign-in, Google sign-in, instant and scheduled meetings, host controls, meeting history, participant signaling, and in-browser recording controls.
## Live Project Link
https://videopods.onrender.com/

> **Project status:** This repository represents a working portfolio project. It is not presented as a security-audited or production-hardened conferencing service.

## Highlights

- Email/password account registration and JWT-based API authentication.
- Google ID-token sign-in with server-side credential verification.
- Authenticated meeting creation, scheduling, starting, ending, cancellation, and history management.
- UUID meeting identifiers and host-associated meeting records.
- WebSocket signaling through Django Channels for participant presence and WebRTC offer/answer/ICE exchange.
- Browser media capture and peer-to-peer media via the WebRTC APIs.
- Adjustable video quality and meeting layouts.
- Meeting attendance records and host-disconnect/duration handling.
- OpenAPI schema, Swagger UI, and ReDoc API documentation.
- SQLite for simple local development, with PostgreSQL and Redis support for containerized deployment.

## Technology stack

| Technology                                                    | Role in Videopods                                                                                                |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Python                                                        | Backend language                                                                                                 |
| Django                                                        | Application framework, ORM, templates, middleware, settings, URL routing                                         |
| Django REST Framework                                         | JSON API views, serializers, permissions, validation and responses                                               |
| Simple JWT                                                    | Short-lived access tokens and refresh tokens for API authentication                                              |
| Django Channels                                               | ASGI WebSocket consumer and real-time signaling events                                                           |
| Daphne                                                        | ASGI server for HTTP and WebSocket traffic                                                                       |
| Redis / `channels_redis`                                      | Shared channel layer for multi-process deployments; in-memory layer is used when Redis is not configured         |
| SQLite / PostgreSQL                                           | Persistent relational data; SQLite is the default local database and PostgreSQL is configured via `DATABASE_URL` |
| Vanilla JavaScript                                            | Browser-side auth flows, API calls, WebRTC lifecycle, participant UI and recording controls                      |
| HTML templates / CSS                                          | Server-rendered pages and responsive presentation                                                                |
| WebRTC (`getUserMedia`, `RTCPeerConnection`, `MediaRecorder`) | Media capture, peer connections, and browser-side recording                                                      |
| Google Identity / `google-auth`                               | Verification of Google ID tokens                                                                                 |
| drf-spectacular                                               | OpenAPI schema and API documentation UI                                                                          |
| Docker / Docker Compose                                       | Repeatable container-based local setup with PostgreSQL and Redis                                                 |

## Features

### Accounts

- Register and sign in with email/password.
- JWT access and refresh token flow.
- Fetch the authenticated user's profile.
- Google sign-in when a Google client ID is configured.
- Client-side token handling and access-token refresh.

### Meetings

- Create instant meetings or schedule them for a future time.
- Start, end, or cancel meetings subject to host and state rules.
- View upcoming meetings and meeting history.
- Delete one history entry or clear the current user's history.
- Join a meeting using its UUID-based URL.
- View participant presence and exchange WebRTC signaling through a WebSocket.
- Host-aware meeting lifecycle handling, including duration expiry and a host-disconnect grace period.
- Choose video quality and participant layout; use browser recording controls where supported.

### API documentation

When the application is running, these routes are configured:

- `/api/docs/` — Swagger UI
- `/api/redoc/` — ReDoc
- `/api/schema/` — OpenAPI schema

See [`API.md`](API.md) for the endpoint inventory and authentication basics.

## Architecture at a glance

1. A user loads a Django-rendered page from `templates/`.
2. `static/js/auth.js` handles account-aware navigation and JSON API requests; it stores the JWT pair in browser `localStorage`.
3. Django REST Framework routes under `/api/` validate the request and apply JWT authentication and permissions.
4. Account logic lives in `accounts/`; meeting API and lifecycle logic live in `meetings/`.
5. When a participant opens a meeting, `static/js/meeting.js` obtains local media and opens a WebSocket connection.
6. `MeetingConsumer` authenticates the WebSocket, validates meeting availability, records attendance, and relays signaling/presence messages through the Channels layer.
7. Browser `RTCPeerConnection` objects negotiate peer-to-peer media. Django/Channels carries signaling messages; it is not itself the media transport.
8. The ORM persists users, meetings, and attendance. Redis provides cross-process event fan-out when configured.

## Run locally

### Requirements

- Python version compatible with `requirements.txt` (the Dockerfile currently uses Python 3.14).
- pip and a virtual environment.
- A modern browser with camera/microphone support.
- Optional: Google OAuth client ID and TURN credentials for broader connectivity.

### Setup

```bash
cd videopods
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Set environment variables for your local environment. At minimum, use a unique `SECRET_KEY`, `DEBUG=1` for local development, and an appropriate `ALLOWED_HOSTS`. Optional variables are listed below. Then run:

```bash
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Camera and microphone access generally requires HTTPS in deployed environments; browsers usually allow localhost during development.

### Docker Compose

The repository includes a `Dockerfile` and `docker-compose.yml` for a web service, PostgreSQL, and Redis:

```bash
docker compose up --build
```

The compose file is a development-oriented example, not a secure production deployment template. Replace placeholder credentials, avoid exposing database/Redis ports publicly, use HTTPS/WSS, and supply secrets through a proper environment or secret manager before deployment.

## Configuration

The settings module reads these environment variables (some have development defaults):

| Variable                         | Purpose                                                                       |
| -------------------------------- | ----------------------------------------------------------------------------- |
| `SECRET_KEY`                     | Django cryptographic signing key; set a strong secret outside development     |
| `DEBUG`                          | Enables/disables Django debug mode; must be `0` in production                 |
| `ALLOWED_HOSTS`                  | Comma-separated permitted host names                                          |
| `CSRF_TRUSTED_ORIGINS`           | Comma-separated trusted origins for CSRF checks                               |
| `DATABASE_URL`                   | SQLite URL by default; PostgreSQL URL for containerized/production-style use  |
| `REDIS_URL`                      | Enables Redis-backed Channels; without it, an in-memory channel layer is used |
| `PUBLIC_BASE_URL`                | Public base URL used to build meeting links                                   |
| `WEBSOCKET_MEETING_PREFIX`       | WebSocket route prefix used by server-rendered config and browser code        |
| `GOOGLE_CLIENT_ID`               | Google sign-in client ID; sign-in is unavailable if not configured            |
| `STUN_URL`                       | STUN server URL used for ICE discovery                                        |
| `TURN_URL`                       | Optional TURN relay URL                                                       |
| `TURN_USERNAME`, `TURN_PASSWORD` | TURN credentials returned to authenticated clients                            |
| `LOGIN_URL`                      | Login route setting                                                           |

Never commit real `.env` values, OAuth secrets, TURN credentials, production database URLs, or private keys.

## Testing and quality checks

Run the existing Django test suite:

```bash
python manage.py test
```

Useful checks before a pull request or deployment:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

Also test key user journeys manually in at least two browsers/devices: registration/login, token refresh, instant and scheduled meetings, unauthorized meeting actions, reconnects, host departure, meeting expiry, recording permissions, and camera/microphone denial. WebRTC connectivity should be tested across different networks, not only on one machine.

## Security notes

The project includes several useful controls—Django middleware, DRF's authenticated-by-default permission setting, explicit `AllowAny` on public authentication/config endpoints, JWT authentication, server-side Google ID-token verification, ownership/host-oriented meeting flows, and WebSocket JWT authentication. These are good foundations, not a guarantee of security.

Before production use:

- Set `DEBUG=0`, a strong secret, correct hosts/origins, HTTPS/WSS, secure deployment headers and cookies, and a production-grade ASGI/reverse-proxy setup.
- Do not use the sample Compose passwords or placeholder secrets.
- Keep `.env`, SQLite databases with user data, recordings, logs, and credentials out of Git.
- Evaluate JWT storage: `localStorage` is accessible to JavaScript and therefore exposed if an XSS vulnerability occurs. Consider a carefully designed HttpOnly/Secure/SameSite cookie approach and CSRF model.
- Add rate limits and abuse protection for login, registration, Google sign-in, meeting creation and WebSocket connection attempts.
- Review WebSocket origin validation, per-message schema/size/rate validation, participant authorization, and meeting-join policy.
- Configure a real TURN service for reliability and protect its credentials with time-limited credentials where possible.
- Add dependency scanning, security tests, logging/monitoring, backup/restore procedures, and an external security review.

## Known scope boundaries

- WebRTC media is peer-to-peer; multi-party mesh performance and bandwidth usage can degrade as participant count grows. A Selective Forwarding Unit (SFU) would be a future scaling path.
- Browser recording is client-side and depends on browser support and user permissions; it is not a managed server-side recording service.
- Redis is required for robust cross-process Channels communication in a multi-worker deployment; the in-memory channel layer is development-only.
- This repository does not claim end-to-end encryption beyond the protections provided by browser WebRTC and transport configuration, nor does it claim a formal security audit.
- Email verification, password reset UX, organization/team administration, meeting waiting rooms, moderation, analytics, and comprehensive operational monitoring can be future improvements.

## Repository map

```text
accounts/          Custom user model, account serializers, auth endpoints
config/            Django settings, root URLs, ASGI/WSGI and template context
meetings/          Meeting and attendance models, API views, services, Channels consumer
templates/         Landing, auth, dashboard, meeting and ended/error pages
static/css/        Application styles
static/js/auth.js  Browser authentication/API helper and top navigation
static/js/meeting.js WebRTC, signaling client, controls, layout and recording logic
API.md             REST API endpoint reference
Dockerfile         Container image definition
docker-compose.yml Local PostgreSQL + Redis + web composition
```

## Contributing

Issues and pull requests are welcome. For meaningful changes, include tests, document behavior changes, avoid committing secrets or local database files, and describe manual WebRTC testing performed.


# Thankyou for Visiting. Feedbacks and contributions are welcomed and highly appreciated
