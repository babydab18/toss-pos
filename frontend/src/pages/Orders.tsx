import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  BellOff,
  Clock,
  Search,
  ChefHat,
  ArrowRight,
  RefreshCw,
  Pencil,
  XCircle,
  History,
} from "lucide-react";
import type { Order, Status, User } from "../types";
import type { Notify } from "../App";
import { api, money, readStored } from "../api";
import Modal from "../components/Modal";
import { draftKey } from "./POS";

const labels: Record<Status, string> = {
  new: "New",
  preparing: "Preparing",
  ready: "Ready to collect",
  completed: "Completed",
  cancelled: "Cancelled",
};
const nextStatus: Partial<Record<Status, Status>> = {
  new: "preparing",
  preparing: "ready",
  ready: "completed",
};
export default function Orders({
  kitchen = false,
  user,
  revision,
  notify,
}: {
  kitchen?: boolean;
  user: User;
  revision: number;
  notify: Notify;
}) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [status, setStatus] = useState(kitchen ? "active" : "");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState(0);
  const [cancel, setCancel] = useState<Order | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [details, setDetails] = useState<Order | null>(null);
  const [sound, setSound] = useState(false);
  const audio = useRef<AudioContext | null>(null);
  const [, tick] = useState(0);
  const navigate = useNavigate();
  useEffect(() => {
    setStatus(kitchen ? "active" : "");
    setPage(0);
  }, [kitchen]);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 15000);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const abort = new AbortController();
    const timer = setTimeout(() => {
      api<Order[]>(
        `/orders?status=${status}&q=${encodeURIComponent(query)}&offset=${page * 100}&limit=100`,
        { signal: abort.signal },
      )
        .then((data) => {
          setOrders(data);
          setError("");
        })
        .catch((e) => {
          if (!abort.signal.aborted) setError((e as Error).message);
        })
        .finally(() => {
          if (!abort.signal.aborted) setLoading(false);
        });
    }, 150);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [revision, status, query, refresh, page]);
  useEffect(() => {
    const beep = () => {
      if (!sound || !kitchen || !audio.current) return;
      const context = audio.current;
      if (context.state !== "running") return;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.frequency.value = 740;
      gain.gain.setValueAtTime(0.08, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.35);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.4);
    };
    window.addEventListener("new-kitchen-order", beep);
    return () => window.removeEventListener("new-kitchen-order", beep);
  }, [sound, kitchen]);
  async function update(order: Order, target: Status, cancellationReason = "") {
    if (busy) return;
    setBusy(order.id);
    try {
      await api(`/orders/${order.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: target,
          version: order.version,
          reason: cancellationReason,
        }),
      });
      setRefresh((n) => n + 1);
      setCancel(null);
      setReason("");
      notify(`Order #${order.number} · ${labels[target]}`);
    } catch (e) {
      notify((e as Error).message, true);
      setRefresh((n) => n + 1);
    } finally {
      setBusy(null);
    }
  }
  function edit(order: Order) {
    const saved = readStored<{ items?: unknown[]; pending?: boolean }>(
      draftKey(user.id),
      {},
    );
    if (saved.items?.length || saved.pending) {
      notify(
        "Finish or clear the current POS draft before editing another order.",
        true,
      );
      return;
    }
    navigate("/", { state: { editOrder: order } });
  }
  return (
    <main className="standard-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {kitchen
              ? "IN THE HEART OF THE TRUCK"
              : "EVERY ORDER, ACCOUNTED FOR"}
          </span>
          <h1>{kitchen ? "Kitchen board" : "Order activity"}</h1>
          <p>
            {kitchen
              ? "A clear view of what’s next. Oldest tickets first."
              : "Follow every ticket from first tap to final pickup."}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="secondary"
            aria-label="Refresh orders"
            onClick={() => setRefresh((n) => n + 1)}
          >
            <RefreshCw size={18} />
          </button>
          {kitchen && (
            <button
              className="secondary"
              onClick={async () => {
                try {
                  if (!audio.current) audio.current = new AudioContext();
                  await audio.current.resume();
                  setSound((s) => !s);
                } catch {
                  notify("Sound is not supported on this device.", true);
                }
              }}
            >
              {sound ? <Bell size={18} /> : <BellOff size={18} />}
              <span>{sound ? "Sound on" : "Enable sound"}</span>
            </button>
          )}
        </div>
      </div>
      <div className="order-toolbar">
        <div className="filter-tabs">
          {[
            ["", "All"],
            ["active", "Active"],
            ["new", "New"],
            ["preparing", "Preparing"],
            ["ready", "Ready"],
            ["completed", "Completed"],
            ["cancelled", "Cancelled"],
          ].map(([value, label]) => (
            <button
              className={status === value ? "selected" : ""}
              onClick={() => {
                setStatus(value);
                setPage(0);
              }}
              key={value}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="search-box compact">
          <Search size={18} />
          <input
            aria-label="Search orders"
            placeholder="Ticket # or customer"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </div>
      </div>
      {error && (
        <div className="error" role="alert">
          {error} Displayed tickets may be out of date.
        </div>
      )}
      {loading ? (
        <div className="empty-state">Loading tickets…</div>
      ) : !orders.length ? (
        <div className="empty-state">
          <ChefHat size={45} strokeWidth={1.3} />
          <h2>{query ? "No matching tickets" : "A clear counter"}</h2>
          <p>
            {query
              ? "Try a different ticket number or pickup name."
              : "Orders will appear here when sent to the kitchen."}
          </p>
        </div>
      ) : (
        <div className={`ticket-grid ${kitchen ? "kitchen-grid" : ""}`}>
          {orders.map((order) => {
            const age = Math.max(
              0,
              Math.floor(
                (Date.now() - new Date(order.created_at).getTime()) / 60000,
              ),
            );
            const next = nextStatus[order.status];
            const canNext =
              next && (user.role !== "kitchen" || next !== "completed");
            return (
              <article
                className={`ticket ticket-${order.status}`}
                key={order.id}
              >
                <header>
                  <div>
                    <span className="eyebrow">
                      {new Date(`${order.day}T12:00:00`).toLocaleDateString(
                        "en-IN",
                        { day: "numeric", month: "short" },
                      )}
                    </span>
                    <h2>#{String(order.number).padStart(3, "0")}</h2>
                    <p>{order.customer || "Walk-in order"}</p>
                  </div>
                  <div className="ticket-meta">
                    <span className={`status status-${order.status}`}>
                      {labels[order.status]}
                    </span>
                    <span
                      className={
                        age >= 15 && ["new", "preparing"].includes(order.status)
                          ? "wait-warning"
                          : ""
                      }
                    >
                      <Clock size={13} />
                      {["completed", "cancelled"].includes(order.status)
                        ? new Date(order.created_at).toLocaleTimeString(
                            "en-IN",
                            { hour: "2-digit", minute: "2-digit" },
                          )
                        : `${age} min`}
                    </span>
                  </div>
                </header>
                {order.history.some((h) => h.changes) && (
                  <div className="correction-banner">
                    <Pencil size={13} />
                    Updated ticket · check changes
                    <button onClick={() => setDetails(order)}>View</button>
                  </div>
                )}
                <div className="ticket-items">
                  {order.items.map((item) => (
                    <div className="ticket-item" key={item.id}>
                      <strong className="item-quantity">
                        {item.quantity}×
                      </strong>
                      <div>
                        <h3>{item.name}</h3>
                        {item.modifiers.map((m, index) => (
                          <p className="modifier-note" key={index}>
                            {m.group_name}: {m.name}
                          </p>
                        ))}
                        {item.instructions && (
                          <p className="kitchen-note">{item.instructions}</p>
                        )}
                      </div>
                    </div>
                  ))}
                  {order.instructions && (
                    <div className="kitchen-note">
                      <strong>Order note:</strong> {order.instructions}
                    </div>
                  )}
                </div>
                <footer>
                  <div className="ticket-total">
                    <span>
                      {order.items.reduce((sum, i) => sum + i.quantity, 0)}{" "}
                      items · {money(order.total)}
                    </span>
                    <button
                      className="icon-button"
                      aria-label={`History for order ${order.number}`}
                      onClick={() => setDetails(order)}
                    >
                      <History size={16} />
                    </button>
                  </div>
                  {canNext && (
                    <button
                      className={`primary ${order.status === "preparing" ? "green-button" : ""}`}
                      disabled={!!busy}
                      onClick={() => update(order, next!)}
                    >
                      {busy === order.id
                        ? "Updating…"
                        : next === "preparing"
                          ? "Start preparing"
                          : next === "ready"
                            ? "Mark ready"
                            : "Complete pickup"}
                      <ArrowRight size={17} />
                    </button>
                  )}
                  {user.role !== "kitchen" &&
                    ["new", "preparing", "ready"].includes(order.status) && (
                      <div className="ticket-actions">
                        {order.status !== "ready" && (
                          <button onClick={() => edit(order)}>
                            <Pencil size={14} />
                            Correct order
                          </button>
                        )}
                        <button
                          onClick={() => {
                            setCancel(order);
                            setReason("");
                          }}
                        >
                          <XCircle size={14} />
                          Cancel
                        </button>
                      </div>
                    )}
                </footer>
              </article>
            );
          })}
        </div>
      )}
      <div className="pagination">
        <button
          className="secondary"
          disabled={!page}
          onClick={() => setPage((p) => p - 1)}
        >
          Previous
        </button>
        <span>Page {page + 1}</span>
        <button
          className="secondary"
          disabled={orders.length < 100}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
      {cancel && (
        <Modal
          title={`Cancel order #${cancel.number}?`}
          onClose={() => !busy && setCancel(null)}
        >
          <p>The kitchen will be notified. This action cannot be undone.</p>
          <label className="field">
            Cancellation reason
            <textarea
              maxLength={500}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Tell the team why this order is cancelled"
              required
            />
          </label>
          <div className="modal-footer">
            <button
              className="secondary"
              disabled={!!busy}
              onClick={() => setCancel(null)}
            >
              Keep order
            </button>
            <button
              className="danger"
              disabled={!reason.trim() || !!busy}
              onClick={() => update(cancel, "cancelled", reason)}
            >
              Cancel order
            </button>
          </div>
        </Modal>
      )}
      {details && (
        <Modal
          title={`Order #${details.number} · History`}
          onClose={() => setDetails(null)}
        >
          <div className="history-list">
            {details.history.map((h, i) => (
              <div key={i}>
                <span className={`status status-${h.status}`}>
                  {labels[h.status]}
                </span>
                <small>{new Date(h.at).toLocaleString("en-IN")}</small>
                <p>{h.reason}</p>
                {!!h.changes && <Correction changes={h.changes} />}
              </div>
            ))}
          </div>
        </Modal>
      )}
    </main>
  );
}

function Correction({ changes }: { changes: unknown }) {
  type Snapshot = {
    customer: string;
    instructions: string;
    total: number;
    items: {
      name: string;
      quantity: number;
      instructions: string;
      modifiers: { name: string }[];
    }[];
  };
  const { before, after } = changes as { before: Snapshot; after: Snapshot };
  return (
    <details>
      <summary>What changed</summary>
      {[
        ["Before correction", before],
        ["After correction", after],
      ].map(([label, value]) => {
        const snapshot = value as Snapshot;
        return (
          <section className="correction-snapshot" key={label as string}>
            <h3>{label as string}</h3>
            <p>
              {snapshot.customer || "Walk-in order"} ·{" "}
              {money(snapshot.total || 0)}
            </p>
            {snapshot.items.map((item, i) => (
              <div key={i}>
                <strong>
                  {item.quantity} × {item.name}
                </strong>
                <p>{item.modifiers?.map((m) => m.name).join(" · ")}</p>
                {item.instructions && <p>{item.instructions}</p>}
              </div>
            ))}
            {snapshot.instructions && <p>Note: {snapshot.instructions}</p>}
          </section>
        );
      })}
    </details>
  );
}
