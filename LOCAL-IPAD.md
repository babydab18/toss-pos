# Run TOSS locally: computer server + iPad

The computer runs the full application and database. The iPad opens it in Safari
over the same local Wi-Fi network. No paid web host is needed. The computer must
stay powered on and awake during service. After downloading/building the software,
normal ordering can run without an internet connection as long as local Wi-Fi
and the server remain available.

## New Windows computer: one-time setup without Docker

1. Download the repository ZIP and **Extract All**. Move the extracted folder to
   a permanent location you own, such as `Documents/TOSS POS` (not Program Files).
2. Double-click **Setup TOSS POS.cmd**. Stay connected to the internet.
3. Setup finds or installs Python and Node.js through Windows Package Manager,
   installs dependencies, builds the website, and initializes the local database.
   Windows may ask you to approve a prerequisite installer. If App Installer is
   missing, install/update it from Microsoft Store and rerun setup.
4. Enter and confirm your own admin password when asked (12+ characters).
   Characters are hidden as you type. Existing installations keep their passwords.
5. When setup says complete, double-click **Run TOSS POS** on the desktop.
6. Open the laptop website with the launcher button. On an iPad/phone, join the
   same Wi-Fi and open the address displayed. Sign in as `admin`.

No GitHub account, Git, Docker, `.env` editing, or command typing is required.
This installer is Windows-only. Do not move/delete the folder after setup; the
shortcut and database depend on it. If setup fails, read its error and rerun it.
Close the running POS before rerunning setup. Existing databases are backed up to
`backups/` before migration; existing menu edits and passwords are preserved.
Python/Node installation may require administrator approval or a restart. Allow
Python on **private networks** if Windows Firewall asks; do not disable the firewall.

## Daily start on Windows (no Docker)

Double-click **Run TOSS POS** on the desktop, or `Run TOSS POS.cmd` in the project
folder. Keep the launcher open. Click **Open POS on this laptop**; on your phone
or iPad, join the same Wi-Fi and type the address displayed in the launcher.
Use your existing login. If multiple addresses appear, use the Wi-Fi IPv4 address
shown by `ipconfig`. After changing Wi-Fi, click **Restart / refresh Wi-Fi address**.

This launcher uses the existing `.venv`, compiled `frontend/dist`, and
`backend/street-side.db`; it does not install dependencies, pull GitHub updates,
or read `.env`. It preserves the local database and uploaded images. Close it
using **Stop POS and close** after service. Restarting Windows requires opening
the shortcut again. Back up the SQLite database while the server is stopped.

If a phone cannot connect, permit the Python server on your trusted private
network in Windows Firewall. Guest/campus Wi-Fi can block device-to-device access;
use a trusted home router or hotspot instead. No router port forwarding is needed.
The shortcut is for this already installed laptop; use the setup below for a new
computer. GitHub Actions is not involved in local startup.

## 1. Prepare the server computer

Install Docker Desktop (or Docker Engine with Compose on Linux), download this
repository and open a terminal in its root directory.

Copy `.env.example` to `.env`. Choose unique `POSTGRES_PASSWORD` and
`ADMIN_PASSWORD` values; the admin password must be at least 12 characters.
Keep `PORT=8080` and `COOKIE_SECURE=false` for this local HTTP setup.

Find the computer's Wi-Fi/LAN IPv4 address: use `ipconfig` on Windows or the
network settings on macOS/Linux. For example, if the address is `192.168.1.50`, set:

```dotenv
ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080,http://192.168.1.50:8080
COOKIE_SECURE=false
PORT=8080
```

Replace the example IP with the real address. Use your router's DHCP reservation
feature to keep that address stable. Use a trusted staff network; HTTP is local
but unencrypted. An HTTPS reverse proxy can be added if needed.

Start the services:

```sh
docker compose up --build -d
```

Open `http://localhost:8080` on the server and sign in with `admin` (or your
configured username) and the password from `.env`. Create cashier/kitchen users
under **Menu & team > Team**.

## 2. Connect the iPad

1. Connect the iPad and server to the same staff network. A guest network may
   block connections between devices.
2. In Safari, open `http://192.168.1.50:8080`, using the server's actual IP.
   **Do not use localhost on the iPad**: that refers to the iPad itself.
3. Sign in. Add the website to the Home Screen using Safari's Share menu for
   quick access. Available app-display options depend on the iPadOS version.
4. Place a test order and confirm it appears in Kitchen on another tab/device.
   Test ready/completed states before the first service.

If the page cannot be reached, confirm the computer is awake, the containers are
running (`docker compose ps`), and the firewall allows TCP port 8080 on the private
staff network. No internet-facing router port forwarding is needed. If the IP
changes, update `ALLOWED_ORIGINS` and rerun `docker compose up -d`.

The database lives on the computer, so staff can use multiple iPads or a separate
kitchen display. If the computer or Wi-Fi goes down, an already-loaded app can
retain a draft, but orders cannot be submitted until the connection returns.
Adding to the Home Screen does not turn this into a self-contained iPad server.

## 3. Apply the revised menu on an existing installation

Back up first. Then, from the repository directory:

```sh
git pull
docker compose up --build -d
docker compose exec api python -m app.toss_menu --update-existing
```

The menu update preserves order history and images. It explicitly applies poster
prices, so run it once for this revision, not at every startup. Open clients
refresh within 15 seconds. See [TOSS-MENU.md](TOSS-MENU.md) for exact prices.

## 4. Backups and daily operation

Docker's named volumes retain orders and uploads across restarts. Do not use
`docker compose down -v`: it deletes those volumes. Restart Docker after a reboot
and verify the POS opens before service. Prevent the server computer from sleeping.

Back up the database and uploaded images to a separate drive regularly. These
commands create binary backups inside the containers before copying them out,
which also avoids older PowerShell binary-redirection issues. Create a local
`backups` directory first and use a new dated filename each time.

```sh
docker compose exec db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/toss-backup.dump'
docker compose cp db:/tmp/toss-backup.dump ./backups/toss-backup.dump
docker compose exec api tar -czf /tmp/toss-uploads.tar.gz -C /data uploads
docker compose cp api:/tmp/toss-uploads.tar.gz ./backups/toss-uploads.tar.gz
```

Test restoring a backup to a separate installation before relying on it. Local
backup files and `.env` are excluded from Git. No hosted server has been
configured by these instructions; they must be run on the owner's computer.

Apple reference: [Add a website to the iPad Home Screen](https://support.apple.com/guide/ipad/bookmark-a-website-ipadc602b75b/ipados).
