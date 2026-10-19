# TOSS | Food Truck Operations

A mobile-first React/TypeScript POS with a FastAPI API, PostgreSQL persistence, configurable food modifiers and a live kitchen board. Includes order corrections, cancellation history, staff roles, menu administration, image uploads and operational analytics. **There is no payment functionality.**

This is the independent TOSS POS repository, stored locally at `C:\Users\ranvi\toss-pos`. The current TOSS branding and imported menu are documented in [TOSS-MENU.md](TOSS-MENU.md). [Architecture and API map](ARCHITECTURE.md) · [Executed checks and verification limits](VERIFICATION.md).

## Use the POS on an iPad over local Wi-Fi

The owner’s chosen setup uses a local computer/server and an iPad on the same network. Follow [LOCAL-IPAD.md](LOCAL-IPAD.md); no paid hosting is needed. The revised 18 October menu contains 27 items, and existing installations can apply it with `docker compose exec api python -m app.toss_menu --update-existing` after a backup.

## Deploy the working POS

[Deploy to Render](https://render.com/deploy?repo=https://github.com/babydab18/toss-pos) provisions the full application, PostgreSQL database and persistent image storage. Enter your own admin password and review the hosting charges (approximately US$13.25/month before extra usage and taxes) before applying. See [deployment instructions](DEPLOYMENT.md).

## Public project page

[View the TOSS project page](https://babydab18.github.io/toss-pos/) for a preview, source download and setup instructions. GitHub Pages serves `docs/`; it does not run the POS backend. The complete application below runs with its own server and PostgreSQL database.

## Start with Docker

For a public HTTPS website, follow [GitHub + Render deployment](DEPLOYMENT.md).
The root `Dockerfile` and `render.yaml` package the frontend and API together;
the Compose setup below remains available for local use.

Requirements: Docker Engine/Desktop with Compose v2.

1. Copy `.env.example` to `.env`.
2. Replace `POSTGRES_PASSWORD` and `ADMIN_PASSWORD` with unique strong passwords. The admin password must be at least 12 characters.
3. Run `docker compose up --build -d` from this directory.
4. Open **http://localhost:8080** and sign in with `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

PostgreSQL health checks run before API startup. Startup applies Alembic migrations and initializes the admin account and TOSS menu only when those records do not already exist. Restarting does not reset data. To create cashier or kitchen accounts, open **Menu & team → Team**.

```sh
docker compose logs -f api
docker compose down
docker compose up -d
```

Database and uploaded images survive these restarts in named volumes. `docker compose down -v` deletes those volumes and must not be used on an installation whose records you need.

## Service workflow

- **Take an order (`/`)**: choose a category or search, tap an item, select required options and extras, add instructions, adjust quantities, then send to kitchen. Every tap can produce a separate customization of the same item.
- **Kitchen (`/kitchen`)**: tickets arrive by WebSocket, oldest active ticket first. Start preparing, then mark ready. Tap **Enable sound** once on each kitchen device; browser sound restrictions require a user gesture.
- **Orders (`/orders`)**: search by pickup name, ticket number or full order UUID, review history, correct new/preparing orders, complete pickups and cancel with a reason. Pagination supports older records.
- **Menu & team (`/admin`)**: add/edit/archive dishes, categories and modifiers; set prices, ordering, visibility and availability; upload images; create combo items and staff accounts. A combo is one menu item with its contents in its description and optional modifier groups.
- **Overview (`/analytics`)**: today’s counts, created and completed order values, popular items, average time from creation to ready, hourly volume and seven-day counts. Reporting and daily ticket numbering use **Asia/Kolkata**, regardless of the device timezone.

Admin has all permissions. Cashiers create/correct orders and manage their lifecycle. Kitchen staff view tickets and move orders to preparing/ready. All permissions are enforced by the API. The same account can use POS and Kitchen on one device, and multiple staff devices can share the server.

## Local development without Docker

Requirements: Python 3.11+ and Node.js 22+. Use PostgreSQL for deployment; SQLite is available for development only.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.lock.txt
cd backend
# Set ADMIN_PASSWORD in your shell before seeding (at least 12 characters).
# Optional DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/streetside
python -m alembic upgrade head
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Environment example in PowerShell: `$env:ADMIN_PASSWORD = 'your-local-password'`. In bash: `export ADMIN_PASSWORD='your-local-password'`. Avoid putting actual deployment passwords into shell history. Development defaults to `backend/street-side.db`; `.env` is loaded by Docker Compose, **not** implicitly by these Python commands.

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Vite proxies API, uploaded image and WebSocket requests to port 8000. API documentation: **http://localhost:8000/docs**. The production build is `npm run build`.

## Reliability and data rules

- Prices are integer paise. The server recalculates every total from current menu records and validates availability, required selections, option membership, and maximum selections. The cart shows an estimate; the server-confirmed ticket is authoritative.
- Orders store immutable item/modifier names and price snapshots. Later menu edits or archival never rewrite historical tickets.
- Creating an order requires an `Idempotency-Key` header. A key is unique in the database, tied to its creator and payload, and survives API restarts. Repeating the same request returns its original order; changing that payload conflicts. The per-day order counter increments transactionally.
- Active order updates require the last observed version. Concurrent edits are rejected with HTTP 409. Corrections record the previous ticket and reason; finalized tickets cannot be edited. Check the current ticket before resubmitting a correction after a lost response.
- The menu and each staff member’s unfinished draft are cached in local storage on that browser. After a lost submission response, the client locks the payload and preserves its key so retry cannot create another order. A confirmed server response is required before clearing the draft or showing success. If browser storage is disabled, sending is blocked to avoid losing the retry key.
- WebSockets reconnect with exponential backoff and jitter. The client refreshes menu and orders on reconnect, on restored network connectivity, and every 15 seconds as a fallback. Tickets explicitly show stale-data errors if refresh fails.
- Offline operation is **draft-only in an already loaded app**. There is no offline submission queue or service-worker app-shell cache; reopening an uncached app requires the server. Cached menus can be stale. Clearing browser storage removes unfinished drafts and retry keys, so resolve pending submissions first.
- Sessions use Argon2 password hashes, random HttpOnly/SameSite cookies, hashed session tokens stored in the database, 12-hour expiration and server-side logout revocation. Mutations and WebSockets check allowed origins; login attempts are rate-limited per connecting IP. Behind the default proxy this is a shared truck-wide limit of 15 attempts/minute.
- Uploads are decoded, bounded and re-encoded as WebP under generated filenames. SVG and arbitrary files are not served as uploaded content.

## Verification

```sh
cd backend
python -m pytest -q
# PostgreSQL: set TEST_DATABASE_URL to a DISPOSABLE test database, then rerun.
# The suite recreates that test database's application tables on every test.

cd ../frontend
npm test
npm run build
npx playwright install chromium
# Start API + Vite against a disposable seeded database first.
# Set E2E_USERNAME and E2E_PASSWORD to its admin credentials.
npm run test:e2e
```

Backend tests exercise modifier rules, pricing, separate customizations, sold-out items, request replay, status transitions, cancellation, correction/version conflicts, snapshots, database reconnect, authentication, permissions, image validation and WebSocket delivery to two clients. Component tests cover required/optional selection, calculated totals, notes, storage and network failures. Playwright covers the real ordering lifecycle on desktop and phone layouts, a second kitchen tab, draft reload and a response lost *after* the server committed an order.

`.github/workflows/ci.yml` runs API checks against PostgreSQL and frontend checks plus Playwright. It assumes this directory is the repository root; move or adjust the workflow paths if retaining it inside another repository.

## Deployment

1. Set exact externally used origins in `ALLOWED_ORIGINS`, including the scheme and port. For a tablet on your LAN, add e.g. `http://192.168.1.10:8080` and open that address on the tablet. Loopback addresses only reach the current device.
2. Terminate HTTPS at your reverse proxy, forward WebSocket upgrades, and set `COOKIE_SECURE=true` for HTTPS deployments. Keep the API and database on the internal network.
3. Run **one API worker / replica**. The event hub is in-process; multiple workers require a shared pub/sub broker before scaling. PostgreSQL constraints and version checks still protect writes independently.
4. Back up both the PostgreSQL database and `upload_data`. For example, use `pg_dump -Fc` through `docker compose exec -T db`, and use `pg_restore` against a separate restore target to verify backups. Shell binary redirection differs on older Windows PowerShell; use a database backup tool or run export inside the container.
5. Run migrations as part of each release; review generated migration scripts. Avoid simultaneous migration startup across replicas. `ADMIN_PASSWORD` only initializes a missing account; changing the environment does not rotate an existing password.
6. For password rotation run `python -m app.manage reset-password USERNAME` inside the API container using an interactive terminal. This revokes that user’s existing sessions.

No taxes, inventory decrementing, printers, payments or multi-truck tenancy are included. A future payment module should reference order IDs with its own records and lifecycle; operational order totals must remain independent of collected amounts. Preparation metrics use creation-to-ready time, not active cooking time.

## Layout

```text
backend/
  app/             # models, validation, auth, services and API routers
  migrations/      # versioned Alembic schema
  tests/           # API, database and WebSocket tests
frontend/
  src/components/  # reusable modifier dialog and modal
  src/pages/       # POS, Kitchen/Orders, Admin, Analytics
  e2e/             # browser workflows
compose.yaml       # PostgreSQL, API, Nginx
.env.example       # deployment configuration
ARCHITECTURE.md     # design decisions and API map
```

Implementation references: [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) and [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html).

## Windows setup without Docker

Download and extract the ZIP, keep the folder in a permanent location, then double-click **Setup TOSS POS.cmd**. It installs prerequisites, builds the app, asks for an admin password, and creates a **Run TOSS POS** desktop shortcut. See [the Windows setup guide](LOCAL-IPAD.md) for details.
