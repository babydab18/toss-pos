import { useEffect, useState } from "react";
import {
  ClipboardList,
  ChefHat,
  CheckCheck,
  XCircle,
  TrendingUp,
  Clock,
} from "lucide-react";
import { api, money } from "../api";
type Data = {
  day: string;
  total_orders: number;
  active_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  created_order_value: number;
  completed_order_value: number;
  average_preparation_minutes: number | null;
  popular_items: { name: string; quantity: number }[];
  hourly: { hour: number; orders: number }[];
  weekly: { day: string; orders: number }[];
};
export default function Analytics({ revision }: { revision: number }) {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    api<Data>("/analytics")
      .then((d) => {
        if (active) {
          setData(d);
          setError("");
        }
      })
      .catch((e) => {
        if (active) setError((e as Error).message);
      });
    return () => {
      active = false;
    };
  }, [revision]);
  return (
    <main className="standard-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">A PULSE ON YOUR SERVICE</span>
          <h1>The daily overview</h1>
          <p>Know your rush. Find your favourites.</p>
        </div>
        <span className="pill">{data?.day} · India time</span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {!data ? (
        <div className="empty-state">Loading your overview…</div>
      ) : (
        <>
          <div className="stats-grid">
            {[
              {
                label: "Orders today",
                value: data.total_orders,
                Icon: ClipboardList,
              },
              {
                label: "In the kitchen",
                value: data.active_orders,
                Icon: ChefHat,
              },
              {
                label: "Completed",
                value: data.completed_orders,
                Icon: CheckCheck,
              },
              {
                label: "Cancelled",
                value: data.cancelled_orders,
                Icon: XCircle,
              },
            ].map(({ label, value, Icon }) => (
              <article className="stat-card" key={label}>
                <span>
                  <Icon size={20} />
                  {label}
                </span>
                <strong>{value}</strong>
                <small>Today’s tickets</small>
              </article>
            ))}
          </div>
          <div className="value-grid">
            <article className="value-card">
              <TrendingUp size={23} />
              <div>
                <span>Value of orders created</span>
                <strong>{money(data.created_order_value)}</strong>
                <small>
                  All tickets created today, including cancelled orders
                </small>
              </div>
            </article>
            <article className="value-card">
              <CheckCheck size={23} />
              <div>
                <span>Value of completed orders</span>
                <strong>{money(data.completed_order_value)}</strong>
                <small>Today’s tickets that have completed pickup</small>
              </div>
            </article>
            <article className="value-card">
              <Clock size={23} />
              <div>
                <span>Average time to ready</span>
                <strong>
                  {data.average_preparation_minutes === null
                    ? "—"
                    : `${data.average_preparation_minutes} min`}
                </strong>
                <small>
                  From creation to ready, excluding cancelled tickets
                </small>
              </div>
            </article>
          </div>
          <p className="metric-note">
            Order values describe food ordered. They do not represent collected
            money.
          </p>
          <div className="analytics-grid">
            <section className="panel">
              <h2>Today, hour by hour</h2>
              <p className="muted">Orders created · Asia/Kolkata</p>
              <div
                className="bar-chart"
                role="img"
                aria-label={data.hourly
                  .map((h) => `${h.hour}:00 ${h.orders} orders`)
                  .join(", ")}
              >
                {data.hourly.map((h) => (
                  <div
                    className="bar-column"
                    key={h.hour}
                    title={`${h.hour}:00 · ${h.orders} orders`}
                  >
                    <span className="bar-value">{h.orders || ""}</span>
                    <div
                      className="chart-bar"
                      style={{
                        height: `${Math.max(2, (h.orders / Math.max(1, ...data.hourly.map((x) => x.orders))) * 150)}px`,
                      }}
                    />
                    <small>{h.hour % 3 === 0 ? `${h.hour}h` : ""}</small>
                  </div>
                ))}
              </div>
            </section>
            <section className="panel">
              <h2>The crowd favourites</h2>
              <p className="muted">
                Items ordered today · excludes cancellations
              </p>
              {!data.popular_items.length ? (
                <p className="empty-state">
                  Your favourites will take shape after the first orders.
                </p>
              ) : (
                data.popular_items.map((item, i) => (
                  <div className="popular-row" key={item.name}>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    <strong>{item.name}</strong>
                    <span>{item.quantity} ordered</span>
                  </div>
                ))
              )}
            </section>
            <section className="panel">
              <h2>Seven days on the street</h2>
              <p className="muted">Daily order count</p>
              <div
                className="bar-chart weekly-chart"
                role="img"
                aria-label={data.weekly
                  .map((d) => `${d.day}: ${d.orders} orders`)
                  .join(", ")}
              >
                {data.weekly.map((d) => (
                  <div className="bar-column" key={d.day}>
                    <span className="bar-value">{d.orders}</span>
                    <div
                      className="chart-bar"
                      style={{
                        height: `${Math.max(2, (d.orders / Math.max(1, ...data.weekly.map((x) => x.orders))) * 150)}px`,
                      }}
                    />
                    <small>
                      {new Date(`${d.day}T12:00:00`).toLocaleDateString(
                        "en-IN",
                        { weekday: "short" },
                      )}
                    </small>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </main>
  );
}
