# Publish TOSS with GitHub and Render

TOSS needs its FastAPI server and PostgreSQL database. GitHub stores the source;
Render runs the website. A private GitHub repository can serve a public website.
Visitors see the TOSS staff login. Orders, menu editing and staff administration
require an account; this deployment does not add customer self-service ordering.

## Existing public repository

Source: https://github.com/babydab18/toss-pos

Use [Deploy to Render](https://render.com/deploy?repo=https://github.com/babydab18/toss-pos) to create the full POS from the included Blueprint. Sign in to Render, set a new admin password, review the paid resources, and apply. The GitHub Pages project showcase is separate from the operational POS.

## 1. Put only this project in a new GitHub repository

Use the supplied `toss-pos-source.zip`, extracted into a new folder outside the
drone repository. The archive contains the application source, branding assets,
tests and deployment configuration. It excludes local databases, uploaded files,
environment secrets, dependencies and the drone project.

To regenerate the archive after edits, run `python scripts/export_source.py` from
this project directory. It writes `.tools/toss-pos-source.zip` using Git's ignore
rules and refuses known runtime or private files accidentally tracked in Git.

Create an empty repository named `toss-pos` at https://github.com/new. Private is
appropriate unless you also want to publish the source. Do not initialize it with
a README, license or gitignore because these source files already exist.

Open a terminal **inside the extracted folder containing `render.yaml`**, then:

```powershell
git init -b main
git add .
git diff --cached --stat
git commit -m "Initial TOSS POS application"
git remote add origin https://github.com/YOUR-ACCOUNT/toss-pos.git
git push -u origin main
```

Replace `YOUR-ACCOUNT` with your GitHub account. Git may open browser sign-in.
Never paste passwords or access tokens into source files or this chat. Do not run
these commands from the parent `ai-powered-inspection-drone` repository.

## 2. Create the Render deployment

1. Sign in at https://dashboard.render.com and connect your GitHub account.
2. Choose **New > Blueprint**, select the new TOSS repository and its `main` branch.
   The Blueprint file is `render.yaml` at the repository root.
3. Review the resources and cost before applying. The file requests a paid
   `0.5c-512mb` web service, a paid `0.1c-256mb` PostgreSQL database with 1 GB
   storage, and a 1 GB persistent upload disk. The selected region is Singapore,
   suitable for the India menu; change both region entries before deployment if
   a different region is closer to your staff.
4. Enter a **new, strong `ADMIN_PASSWORD` of at least 12 characters** in Render's
   secret field. The username is `admin`. Do not reuse the local demo password.
5. Apply the Blueprint. This is the step that creates billable resources.
6. Wait until the web service is healthy, then open the **actual URL Render
   assigns**. It will look like `https://toss-pos-....onrender.com`.
7. Sign in and create staff accounts under **Menu & team > Team**.

The initial baseline is approximately **US$13.25/month**, before additional
usage and tax: $7 web compute, $6 PostgreSQL compute (1 GB storage included),
and $0.25 for the upload disk. Confirm the live quote in Render before applying;
prices and plans can change. See [Render pricing](https://render.com/pricing).
Free Postgres expires after 30 days and free web services have limitations, so
this Blueprint uses paid persistence for ongoing operation. See
[Render free services](https://render.com/docs/free).

Deployment builds the React app and serves it with the API at one HTTPS origin.
Startup applies migrations and seeds the TOSS menu. Render's database URL is
automatically converted to the installed psycopg driver; its assigned port and
public URL are used automatically. HTTPS session cookies are enabled. No staff
password is included in the repository. Production starts with a fresh database;
local orders, uploaded photos and browser drafts are not transferred.

## 3. Check the first deployment

- Open `/api/health`; it should return `{"status":"ok"}`.
- Open `/kitchen` directly and refresh it; the application should load.
- Confirm logged-out visitors cannot read `/api/orders` (HTTP 401).
- Sign in on a cashier device and open Kitchen in a second browser/device. Create
  a clearly labeled test order and check that Kitchen updates, then cancel it
  with a test reason.
- Upload a menu photo and confirm it remains after a service restart.
- Check the GitHub Actions results. They cover PostgreSQL, the compiled frontend
  in browser tests, and booting the Docker image with a fresh persistent volume.

Keep **one web instance and one Uvicorn worker** because live events are currently
in-process. Disk-backed deployments briefly interrupt service on redeploy, so
schedule updates outside busy service hours. Auto-deploy waits for GitHub checks
to pass. See [Render Blueprints](https://render.com/docs/blueprint-spec) and
[persistent disks](https://render.com/docs/disks).

## Custom domain and ongoing operation

Add your domain in Render's **Settings > Custom Domains**, then follow its DNS
instructions. Add `ALLOWED_ORIGINS=https://orders.yourdomain.com` in the service's
environment and redeploy. Use comma-separated full origins for multiple domains.
The assigned Render URL remains allowed automatically. There are no frontend
API URL changes to make.

Keep database backups and an upload-disk backup. A new deployment does not reset
orders or overwrite menu edits. Changing `ADMIN_PASSWORD` later does not rotate
an existing account: use Render's service shell to run
`python -m app.manage reset-password admin`, which also revokes its sessions.

The Docker/Render deployment must still be exercised on the host. Local checks
are documented in [VERIFICATION.md](VERIFICATION.md); preparation is not proof
that a public deployment has succeeded.
