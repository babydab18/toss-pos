# Run TOSS locally: computer server + iPad

The computer runs the full application and database. The iPad opens it in Safari
over the same local Wi-Fi network. No paid web host is needed. The computer must
stay powered on and awake during service. After downloading/building the software,
normal ordering can run without an internet connection as long as local Wi-Fi
and the server remain available.

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
