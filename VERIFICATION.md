# Verification record

Executed locally on Windows with Python 3.11 and a project-local Node.js 22 runtime.

| Check | Result |
| --- | --- |
| Backend API/database/WebSocket/hosting tests | 26 passed |
| Frontend component/API/storage tests | 6 passed |
| Playwright desktop + phone + tablet-sized Chromium | 13 passed |
| TypeScript + Vite production build | Passed; main JavaScript bundle approximately 102 KB gzip |
| Alembic upgrade to head | Passed on SQLite |
| Alembic model/schema consistency check | Passed; no new upgrade operations |
| Python source compilation | Passed |
| Compose, Render Blueprint and CI YAML parsing | Passed |

Browser coverage includes separately customized versions of the same dish, required selections, draft persistence after reload, sending to kitchen, live updates in a second tab, preparation and pickup completion, active-order corrections with readable history, cancellation reason validation, admin item creation/deletion, sold-out propagation, theme changes, phone viewport overflow, connectivity loss/reconnection, and a network failure after the server commits an order followed by a safe retry. Backend concurrency testing submits the same key from four simultaneous clients and asserts exactly one ticket.

The administration checks found and verified a fix for an Add item button that could be clicked before category loading completed. Image tests found and verified explicit WebP MIME registration for Windows. Desktop and phone screenshots were inspected; quantity controls and cart height were adjusted.

Local database tests and browser runs used isolated SQLite databases. Docker and PostgreSQL executables were unavailable on this host, so the Compose image build and PostgreSQL runtime behavior were **not executed here**. The included CI workflow runs the API suite against a disposable PostgreSQL 17 service; that workflow has not yet run on GitHub. Native Safari/iOS and Android devices were not tested; phone coverage used Chromium emulation.

The backend test run emits a dependency deprecation warning for Starlette's current httpx test adapter; there were no failing tests. Production startup does not use that adapter.

Temporary servers were used only for verification. Follow README setup instructions to launch your own instance with your chosen administrator credentials.

## TOSS redesign

The TOSS reference menu was imported as 30 items across 11 categories. Four additional backend tests cover safe/idempotent menu import, preservation of past order snapshots and custom dishes, the confirmed portion prices, sauce and extra prices, and combo drink choices. The user confirmed the tender and bucket price ladders.

Browser workflows now use the TOSS menu. The final run passed all 13 checks with the neon redesign, including an 820px tablet viewport, a phone viewport, and desktop. Local font and image files loaded successfully; screenshots were checked and no horizontal overflow or browser runtime errors were observed. The reload test waits for the POS to finish loading before opening the mobile cart.

The production frontend build and 6 component tests passed. The current local app remains at http://localhost:5173; temporary verification used separate ports and a disposable database. See [preview](docs/toss-preview.png), [menu details](TOSS-MENU.md), and [asset provenance/prompts](frontend/public/images/ASSETS.md).

## Public hosting preparation

The combined frontend/API mode passed all 13 browser tests using the compiled
Vite output served directly by FastAPI on a temporary local port. Its startup
applied both migrations and seeded a disposable SQLite database. Four new backend
checks cover managed database URL conversion, allowed public/custom origins,
frontend routes and private-file rejection, and secure cookies/origin protection.
All 26 backend tests passed. The frontend production build passed again.

The Render and CI files parse as YAML; they have not yet been validated by a
Render deployment. The cloud Docker image, Linux privilege-drop bootstrap and
PostgreSQL startup cannot be executed on this Windows host without Docker. A new
GitHub Actions container job checks those paths after pushing the repository.
No public URL or hosted resources have been created, and nothing has been pushed
to GitHub. The source archive excludes local runtime data and dependencies.
