# Service architecture

StreetSide is a single food-truck, staff-only ordering application. The React/Vite client talks to a FastAPI REST API; PostgreSQL is the source of truth. One Uvicorn worker broadcasts committed changes over authenticated WebSockets. Clients also refresh periodically and after reconnecting. Horizontal scaling requires a shared event broker before adding workers.

## Data

Users have admin, cashier, or kitchen roles. Revocable, hashed session tokens live in a separate sessions table. Categories contain menu items. Items have ordered many-to-many modifier-group assignments; groups own options and selection bounds. Combos are menu items with a configurable description and modifier assignments, with no inventory decomposition.

Orders own item snapshots, modifier snapshots, and an append-only status/correction history. All monetary values are integer paise. A per-India-calendar-day counter allocates ticket numbers atomically. Each creation has a unique idempotency key and request fingerprint; retries return the original order, while changed payloads conflict. Orders carry optimistic versions to reject concurrent corrections/status changes. Database transactions commit before events are broadcast.

Menu deletion is archival to preserve references. Order names/prices never depend on current menu values. Corrections replace an active ticket's items and record before/after details. Completed and cancelled orders are immutable. No payment records, methods, or statuses exist.

## Routes

| API | Access |
| --- | --- |
| POST /api/auth/login, POST /api/auth/logout, GET /api/auth/me | Session |
| GET /api/menu, GET /api/orders, GET /api/orders/{id} | All staff |
| POST /api/orders, PUT /api/orders/{id} | Admin / cashier |
| PATCH /api/orders/{id}/status | Role and transition checked |
| GET/POST/PUT/DELETE /api/admin/{categories,groups,items} | Admin |
| POST /api/admin/images, GET/POST /api/admin/users | Admin |
| GET /api/analytics | Admin |
| /api/ws | Authenticated session and same-origin check |

## Client

App owns session, menu cache, theme, navigation, and connectivity. POS owns a persisted draft with a stable submission key, modifier dialog and responsive cart. Orders and Kitchen consume live invalidations. Admin provides category, item, modifier and staff editors. Analytics displays order-value metrics, hourly volume and a seven-day trend. The API client always waits for a successful response before acknowledging submission.

## Delivery

backend/app contains models, schemas, authentication, order services and API routers; backend/migrations contains Alembic migrations. frontend/src contains typed components, pages, API and styles. Docker Compose starts PostgreSQL, runs migrations and optional seed initialization, then serves the application through Nginx. SQLite is supported only for fast local tests/development; PostgreSQL integration tests are selectable using TEST_DATABASE_URL.
