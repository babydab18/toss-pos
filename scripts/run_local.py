"""Desktop launcher for an already installed local TOSS POS (no Docker)."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
PORT = 8080
URL = f"http://localhost:{PORT}"


def addresses():
    found = set()
    try:
        found.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(ip for ip in found if not ip.startswith(("127.", "169.254.")) and ip != "0.0.0.0")


def environment(ips):
    env = os.environ.copy()
    env.update(DATABASE_URL="sqlite:///" + (ROOT / "backend/street-side.db").as_posix(),
               FRONTEND_DIST=str(ROOT / "frontend/dist"),
               UPLOAD_DIR=str(ROOT / "backend/uploads"), COOKIE_SECURE="false",
               ALLOWED_ORIGINS=",".join([URL, f"http://127.0.0.1:{PORT}"] +
                                        [f"http://{ip}:{PORT}" for ip in ips]))
    return env


class Launcher:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("TOSS POS - Local server")
        self.window.geometry("620x440")
        self.process = None
        self.log = None
        self.tries = 0
        tk.Label(self.window, text="TOSS POS", font=("Segoe UI", 25, "bold")).pack(pady=(18, 5))
        self.status = tk.StringVar(value="Starting...")
        tk.Label(self.window, textvariable=self.status, wraplength=570).pack(pady=8)
        tk.Label(self.window, text="Phone / iPad: connect to the same Wi-Fi, then open:").pack()
        self.links = tk.Text(self.window, height=4, width=65)
        self.links.pack(padx=20, pady=10)
        tk.Button(self.window, text="Open POS on this laptop", command=lambda: webbrowser.open(URL)).pack(pady=5)
        tk.Button(self.window, text="Restart / refresh Wi-Fi address", command=self.restart).pack(pady=5)
        tk.Button(self.window, text="Stop POS and close", command=self.close).pack(pady=5)
        tk.Label(self.window, text="Keep this window open and the laptop awake.\nYour existing login and saved sales are retained.").pack(pady=10)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.start()

    def start(self):
        for path in [ROOT/"backend/street-side.db", ROOT/"frontend/dist/index.html", ROOT/".venv/Scripts/python.exe"]:
            if not path.exists():
                self.status.set(f"Missing {path.name}. This launcher requires the installed local app.")
                return
        probe = socket.socket()
        try:
            probe.bind(("0.0.0.0", PORT))
        except OSError:
            self.status.set("Port 8080 is already in use. Close the other POS launcher/server first, then click Restart.")
            return
        finally:
            probe.close()
        ips = addresses()
        self.links.delete("1.0", "end")
        self.links.insert("1.0", "\n".join(f"http://{ip}:{PORT}" for ip in ips) or "No network address found. Connect to Wi-Fi and click Restart.")
        (ROOT/".tools").mkdir(exist_ok=True)
        self.log = (ROOT/".tools/local-launcher.log").open("a", encoding="utf-8")
        self.process = subprocess.Popen(
            [str(ROOT/".venv/Scripts/python.exe"), "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=ROOT/"backend", env=environment(ips), stdout=self.log, stderr=self.log,
            creationflags=subprocess.CREATE_NO_WINDOW)
        self.status.set("Starting local server...")
        self.tries = 0
        self.window.after(700, self.check)

    def check(self):
        if self.process is None:
            return
        if self.process.poll() is not None:
            self.status.set("Server stopped. See .tools/local-launcher.log for details, then click Restart.")
            return
        try:
            with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
                healthy = json.load(response).get("status") == "ok"
            if healthy:
                self.status.set("Running - ready for orders")
                self.window.after(4000, self.check)
                return
        except Exception:
            pass
        self.tries += 1
        self.status.set("Waiting for server..." if self.tries < 20 else "Server is not responding. Check .tools/local-launcher.log.")
        self.window.after(1000, self.check)

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            self.process.wait(timeout=10)
        self.process = None
        if self.log:
            self.log.close()
            self.log = None

    def restart(self):
        self.stop()
        self.start()

    def close(self):
        if self.process is not None and self.process.poll() is None:
            if not messagebox.askyesno("Stop POS?", "Stop the server? Connected phones cannot submit orders until you start it again."):
                return
        self.stop()
        self.window.destroy()


if __name__ == "__main__":
    Launcher().window.mainloop()
