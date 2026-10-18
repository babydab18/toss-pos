import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import {
  Flame,
  LayoutGrid,
  ChefHat,
  ClipboardList,
  SlidersHorizontal,
  ChartNoAxesCombined,
  Sun,
  Moon,
  LogOut,
  Radio,
  WifiOff,
} from "lucide-react";
import { api, readStored, saveStored } from "./api";
import type { Menu, User } from "./types";
import POS from "./pages/POS";
import Orders from "./pages/Orders";
import Admin from "./pages/Admin";
import Analytics from "./pages/Analytics";
import TossLogo from "./components/TossLogo";

const emptyMenu: Menu = { items: [], categories: [], groups: [] };
export type Notify = (message: string, error?: boolean) => void;
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [menu, setMenu] = useState<Menu>(() =>
    readStored("streetside-menu", emptyMenu),
  );
  const [menuLoaded, setMenuLoaded] = useState(false);
  const [connected, setConnected] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [revision, setRevision] = useState(0);
  const [dark, setDark] = useState(() => readStored("toss-dark", true));
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(
    null,
  );
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );
  const notify = useCallback<Notify>((text, error = false) => {
    setToast({ text, error });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 6000);
  }, []);
  const refreshMenu = useCallback(async () => {
    try {
      const data = await api<Menu>("/menu");
      setMenu(data);
      saveStored("streetside-menu", data);
      setMenuLoaded(true);
    } catch {
      setMenuLoaded(false);
    }
  }, []);
  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
    const expire = () => setUser(null);
    window.addEventListener("session-expired", expire);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    saveStored("toss-dark", dark);
  }, [dark]);
  useEffect(() => {
    if (!user) return;
    let disposed = false,
      socket: WebSocket,
      retry: ReturnType<typeof setTimeout>,
      attempts = 0;
    const refresh = () => {
      void refreshMenu();
      setRevision((v) => v + 1);
    };
    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/ws`,
      );
      socket.onopen = () => {
        attempts = 0;
        setConnected(true);
        refresh();
      };
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "menu.updated") void refreshMenu();
          if (data.type.startsWith("order.")) {
            setRevision((v) => v + 1);
            if (data.type === "order.created")
              window.dispatchEvent(new Event("new-kitchen-order"));
          }
        } catch {
          /* Ignore malformed events; periodic refresh remains available. */
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!disposed)
          retry = setTimeout(
            connect,
            Math.min(30000, 1000 * 2 ** attempts++) + Math.random() * 500,
          );
      };
      socket.onerror = () => socket.close();
    };
    const network = () => {
      setOnline(navigator.onLine);
      if (navigator.onLine) refresh();
    };
    connect();
    refresh();
    const poll = setInterval(refresh, 15000);
    window.addEventListener("online", network);
    window.addEventListener("offline", network);
    return () => {
      disposed = true;
      clearTimeout(retry);
      clearInterval(poll);
      socket?.close();
      setConnected(false);
      window.removeEventListener("online", network);
      window.removeEventListener("offline", network);
    };
  }, [user, refreshMenu]);
  if (loading)
    return (
      <main className="loading-screen">
        <Flame size={42} />
        <p>Opening TOSS…</p>
      </main>
    );
  if (!user) return <Login onLogin={setUser} />;
  const canOrder = user.role !== "kitchen";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to={canOrder ? "/" : "/kitchen"} className="brand">
          <TossLogo />
        </NavLink>
        <span className="nav-caption">YOUR WORKSPACE</span>
        <nav>
          {canOrder && (
            <NavLink to="/" end title="Take an order">
              <LayoutGrid size={21} />
              Take an order
            </NavLink>
          )}
          <NavLink to="/kitchen" title="Kitchen">
            <ChefHat size={21} />
            Kitchen <span className="nav-dot" />
          </NavLink>
          <NavLink to="/orders" title="Orders">
            <ClipboardList size={21} />
            Orders
          </NavLink>
          {user.role === "admin" && (
            <>
              <NavLink to="/admin" title="Menu & team">
                <SlidersHorizontal size={21} />
                Menu & team
              </NavLink>
              <NavLink to="/analytics" title="Overview">
                <ChartNoAxesCombined size={21} />
                Overview
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="service-note">
            <span className="green-dot" />
            Fresh made daily.<p>Premium ingredients. Big flavour.</p>
          </div>
          <button className="theme-button" onClick={() => setDark((d) => !d)}>
            {dark ? <Sun size={19} /> : <Moon size={19} />}
            {dark ? "Light mode" : "Dark mode"}
          </button>
          <div className="user-row">
            <span className="avatar">
              {user.username.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>{user.username}</strong>
              <small>
                {user.role === "cashier" ? "Order taker" : user.role}
              </small>
            </div>
            <button
              aria-label="Sign out"
              className="icon-button"
              onClick={async () => {
                try {
                  await api("/auth/logout", { method: "POST" });
                  setUser(null);
                } catch (e) {
                  notify((e as Error).message, true);
                }
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <span className="truck-tag">TOSS KITCHEN</span>
            <span className="topbar-divider">/</span>
            <span>Service workspace</span>
          </div>
          <span
            className={`connection ${connected && online ? "live" : "disconnected"}`}
          >
            {connected && online ? <Radio size={15} /> : <WifiOff size={15} />}
            {!online
              ? "Offline · draft only"
              : connected
                ? "Live & connected"
                : "Reconnecting · refreshing"}
          </span>
          <div className="mobile-account">
            <button
              className="icon-button"
              aria-label="Toggle theme"
              onClick={() => setDark((d) => !d)}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              className="icon-button"
              aria-label="Sign out"
              onClick={async () => {
                try {
                  await api("/auth/logout", { method: "POST" });
                  setUser(null);
                } catch (e) {
                  notify((e as Error).message, true);
                }
              }}
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>
        {!menuLoaded && (
          <div className="connection-banner">
            {menu.items.length
              ? "Showing your cached menu. Availability and prices will be checked by the server."
              : "Menu unavailable. Check your connection."}
            <button onClick={refreshMenu}>Retry</button>
          </div>
        )}
        <Routes>
          <Route
            path="/"
            element={
              canOrder ? (
                <POS
                  menu={menu}
                  user={user}
                  notify={notify}
                  online={online}
                  onSubmitted={() => setRevision((v) => v + 1)}
                />
              ) : (
                <Navigate to="/kitchen" replace />
              )
            }
          />
          <Route
            path="/kitchen"
            element={
              <Orders kitchen user={user} revision={revision} notify={notify} />
            }
          />
          <Route
            path="/orders"
            element={<Orders user={user} revision={revision} notify={notify} />}
          />
          <Route
            path="/admin"
            element={
              user.role === "admin" ? (
                <Admin
                  revision={revision}
                  notify={notify}
                  onChanged={refreshMenu}
                />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route
            path="/analytics"
            element={
              user.role === "admin" ? (
                <Analytics revision={revision} />
              ) : (
                <Navigate to="/" replace />
              )
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
      {toast && (
        <div
          role={toast.error ? "alert" : "status"}
          className={`toast ${toast.error ? "toast-error" : ""}`}
        >
          {toast.text}
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast(null)}
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <main className="login-page">
      <div className="login-art">
        <TossLogo large />
        <span className="eyebrow">DRENCH. MESSY. ADDICTIVE.</span>
        <h1>
          Crispy. Juicy.
          <br />
          Drippy.
        </h1>
        <p>
          From the first order to the last pickup.
          <br />
          Your whole service, in one place.
        </p>
        <div className="login-stamp">WARNING: EXTREME TOSSY FOOD!</div>
      </div>
      <form
        className="login-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            onLogin(
              await api<User>("/auth/login", {
                method: "POST",
                body: JSON.stringify({ username, password }),
              }),
            );
          } catch (err) {
            setError((err as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <span className="eyebrow">LET’S GET SERVICE STARTED</span>
        <h1>Welcome to TOSS</h1>
        <p className="muted">Sign in with your staff account.</p>
        <label className="field">
          Username
          <input
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            maxLength={80}
          />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            maxLength={200}
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          {busy ? "Signing in…" : "Open workspace →"}
        </button>
        <p className="login-help">Need access? Ask your truck administrator.</p>
      </form>
    </main>
  );
}
